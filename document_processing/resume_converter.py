"""
Resume Format Converter — core conversion logic.
Extracted from the standalone resume_converter.py script for integration
into the main FastAPI application.

Public API:  run_conversion(resume_path, template_path, output_path, api_key)
"""

import base64
import json
import os
from pathlib import Path
from typing import Optional

import pdfplumber
import fitz  # PyMuPDF
from openai import OpenAI

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, HRFlowable, KeepTogether, FrameBreak,
    NextPageTemplate,
)

from utils.logger_instances import file_convert_logger as logger


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def hex_to_color(hex_str: str, fallback: str = "#000000") -> colors.Color:
    try:
        h = str(hex_str).strip().lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return colors.Color(
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
        )
    except Exception:
        return hex_to_color(fallback)


def parse_size(val, default: int = 10) -> int:
    try:
        return max(6, min(40, int(str(val).replace("px", "").replace("pt", "").strip())))
    except Exception:
        return default


FONT_MAP = {
    "helvetica":   ("Helvetica",   "Helvetica-Bold",   "Helvetica-Oblique"),
    "arial":       ("Helvetica",   "Helvetica-Bold",   "Helvetica-Oblique"),
    "times":       ("Times-Roman", "Times-Bold",       "Times-Italic"),
    "times-roman": ("Times-Roman", "Times-Bold",       "Times-Italic"),
    "georgia":     ("Times-Roman", "Times-Bold",       "Times-Italic"),
    "courier":     ("Courier",     "Courier-Bold",     "Courier-Oblique"),
}


def get_fonts(family: str):
    return FONT_MAP.get(family.lower().strip(),
                        ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique"))


# Supported resume input formats
SUPPORTED_RESUME_EXTENSIONS = {".pdf", ".docx", ".doc"}


async def extract_text(file_path: str) -> str:
    """
    Extract plain text from a resume file, reusing the existing
    battle-tested extractors in document_processing/data_extraction.py.

    - PDF  → extract_with_pymupdf  (pymupdf4llm → fitz fallback)
    - DOCX → extract_with_unstructured  (UnstructuredWordDocumentLoader
              → python-docx fallback)
    - DOC  → extract_with_unstructured  (HTML-disguised sniff → OLE binary
              stream → python-docx fallback — no LibreOffice required)
    """
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_RESUME_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{ext}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_RESUME_EXTENSIONS))}"
        )

    if ext == ".pdf":
        from document_processing.data_extraction import extract_with_pymupdf
        text, _ = await extract_with_pymupdf(file_path)
    else:  # .docx or .doc
        from document_processing.data_extraction import extract_with_unstructured
        text, _ = await extract_with_unstructured(file_path)

    if not text or not text.strip():
        raise ValueError(
            f"Could not extract any text from '{Path(file_path).name}'. "
            "The file may be corrupt, image-only, or password-protected."
        )

    return text


# ──────────────────────────────────────────────────────────────────────────────
# Template text helper (PDF-only, sync — used inside asyncio.to_thread)
# ──────────────────────────────────────────────────────────────────────────────

def _extract_template_text(pdf_path: str) -> str:
    """Extract raw text from the template PDF using pdfplumber (template is always PDF)."""
    content = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                content.append(f"--- Page {i} ---\n{text}")
    return "\n\n".join(content)


# ──────────────────────────────────────────────────────────────────────────────
# Step 2 — Extract header/footer text by coordinates
# ──────────────────────────────────────────────────────────────────────────────

def extract_header_footer(pdf_path: str) -> dict:
    result = {"logo_text": "", "footer_text": ""}
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        page_h = page.height
        page_w = page.width
        header_threshold = page_h * 0.15
        footer_threshold = page_h * 0.88
        logo_x_threshold = page_w * 0.55
        logo_words: list[str] = []
        footer_words: list[str] = []
        for w in page.extract_words():
            y = w.get("top", 0)
            x = w.get("x0", 0)
            t = w.get("text", "").strip()
            if not t:
                continue
            if y < header_threshold and x > logo_x_threshold:
                logo_words.append(t)
            elif y > footer_threshold:
                footer_words.append(t)
        result["logo_text"] = " ".join(logo_words).strip()
        result["footer_text"] = " ".join(footer_words).strip()
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Step 3 — Convert PDF pages to base64-encoded PNG images
# ──────────────────────────────────────────────────────────────────────────────

def pdf_to_images(pdf_path: str) -> list[str]:
    encoded: list[str] = []
    doc = fitz.open(pdf_path)
    for page in doc:
        mat = fitz.Matrix(200 / 72, 200 / 72)
        pix = page.get_pixmap(matrix=mat)
        encoded.append(base64.b64encode(pix.tobytes("png")).decode("utf-8"))
    doc.close()
    return encoded


# ──────────────────────────────────────────────────────────────────────────────
# Step 4 — Analyze template with GPT-4o (visual style + section schema)
# ──────────────────────────────────────────────────────────────────────────────

def analyze_template(client: OpenAI, template_images: list[str],
                     template_text: str, hf: dict) -> dict:
    logger.info("--- Analyzing template with GPT-4o ---")

    content: list[dict] = []
    logo_is_image = not hf.get("logo_text", "")
    if logo_is_image:
        content.append({"type": "text", "text":
            "IMPORTANT: Look at the top-right corner of the template image. "
            "There is a company logo or name there as an image/graphic. "
            "Read that company name exactly and put it in header.logo_text in your JSON."
        })
    for i, img in enumerate(template_images):
        content.append({"type": "text", "text": f"Template Page {i + 1}:"})
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img}"}})

    content.append({"type": "text", "text": f"""
Already extracted from PDF coordinates:
- Footer text: "{hf['footer_text']}"
- Logo text (if empty, read from image top-right corner): "{hf['logo_text']}"

Full template text:
{template_text}

Analyze the template image and text carefully. Return ONLY this JSON:

{{
  "layout": {{
    "type": "single_column or two_column",
    "sidebar_position": "left or right",
    "sidebar_width_percent": 30
  }},
  "colors": {{
    "header_background": "#hex or none",
    "sidebar_background": "#hex or none",
    "page_background": "#ffffff",
    "name_color": "#hex",
    "role_color": "#hex",
    "section_heading_color": "#hex",
    "body_text_color": "#hex",
    "divider_color": "#hex",
    "footer_text_color": "#hex",
    "footer_bar_color": "#hex or none"
  }},
  "typography": {{
    "font_family": "Helvetica or Times-Roman or Courier",
    "name_font_size": 16,
    "role_font_size": 12,
    "section_heading_font_size": 11,
    "body_font_size": 9
  }},
  "margins": {{
    "left_mm": 18,
    "right_mm": 18,
    "top_mm": 10,
    "col_padding_mm": 5
  }},
  "header": {{
    "logo_text": "company name from top-right corner of image",
    "logo_position": "left or right or none",
    "name_alignment": "left or center or right",
    "show_role_under_name": true,
    "has_divider_after_header": true,
    "has_contact_in_header": false
  }},
  "sections": {{
    "order": ["exact section names as written in template body"],
    "sidebar_sections": [],
    "main_sections": [],
    "section_fields": {{
      "Section Name": ["Field1", "Field2", "Field3"]
    }}
  }},
  "footer": {{
    "has_colored_bar": true
  }},
  "styling": {{
    "section_divider": true,
    "bullet_char": "•",
    "section_heading_uppercase": false
  }}
}}

Rules:
- font_size = plain integers only
- font_family = Helvetica, Times-Roman, or Courier only
- Section names = EXACTLY as written in template body
- If single_column, sidebar_sections = []
- section_fields is CRITICAL: for EVERY section in order[], list ALL sub-field labels
  that appear inside that section in the template.
"""})

    resp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": content}],
        max_tokens=2000,
    )
    fmt = json.loads(resp.choices[0].message.content)
    fmt.setdefault("header", {})
    fmt.setdefault("footer", {})
    fmt["footer"]["footer_text"] = hf["footer_text"]
    if hf.get("logo_text"):
        fmt["header"]["logo_text"] = hf["logo_text"]

    logger.info(f"--- Template layout: {fmt.get('layout', {}).get('type', '?')} ---")
    logger.info(f"--- Sections detected: {fmt.get('sections', {}).get('order', [])} ---")
    return fmt


# ──────────────────────────────────────────────────────────────────────────────
# Step 5 — Extract & remap resume content using section fields
# ──────────────────────────────────────────────────────────────────────────────

def extract_resume_data(client: OpenAI, resume_text: str, fmt: dict) -> dict:
    logger.info("--- Extracting and remapping resume content ---")
    sections = fmt.get("sections", {}).get("order", [])
    section_fields = fmt.get("sections", {}).get("section_fields", {})

    field_map_lines: list[str] = []
    for sec in sections:
        fields = section_fields.get(sec, [])
        if fields:
            field_map_lines.append(f'  - "{sec}": has fields: {fields}')
        else:
            field_map_lines.append(f'  - "{sec}": free text or list')
    field_map_str = "\n".join(field_map_lines)

    prompt = f"""You are a professional resume parser.

RESUME TEXT:
{resume_text}

TARGET TEMPLATE SECTIONS AND THEIR FIELDS:
{field_map_str}

Rules:
1. Extract ALL content EXACTLY as written — do not add, change or remove anything
2. Map content to the closest matching template section name
3. For "role": check top of resume first, then experience/projects/industrial exposure. NEVER leave empty.
4. For each section, use the field list above to know exactly what sub-fields to extract.
5. Return ONLY this JSON:

{{
  "personal_info": {{
    "name": "",
    "role": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "github": "",
    "website": ""
  }},
  "sections": [
    {{
      "title": "exact section name from template",
      "type": "summary or skills or experience or education or projects or certifications or other",
      "content": {{
        "text": "use for free-text sections like Profile Summary",
        "items": ["use for simple list sections like Technical Skills"],
        "entries": [
          {{
            "heading": "primary heading",
            "subheading": "secondary",
            "duration": "date range if present",
            "location": "location if present",
            "description": "description text if present",
            "bullets": ["bullet points / responsibilities"],
            "metadata": {{
              "FieldName": "value — use EXACT field names from the template section_fields"
            }}
          }}
        ]
      }}
    }}
  ]
}}
"""

    resp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
    )
    data = json.loads(resp.choices[0].message.content)
    logger.info(f"--- Resume parsed: {data.get('personal_info', {}).get('name', 'N/A')} ---")
    return data


# ──────────────────────────────────────────────────────────────────────────────
# Step 6 — Build PDF with ReportLab
# ──────────────────────────────────────────────────────────────────────────────

def build_pdf(data: dict, fmt: dict, output_path: str) -> None:
    logger.info(f"--- Building PDF: {output_path} ---")

    clr = fmt.get("colors", {})
    typo = fmt.get("typography", {})
    layout = fmt.get("layout", {})
    header_cfg = fmt.get("header", {})
    footer_cfg = fmt.get("footer", {})
    styling = fmt.get("styling", {})
    margins_cfg = fmt.get("margins", {})
    sections_cfg = fmt.get("sections", {})

    font_normal, font_bold, font_italic = get_fonts(typo.get("font_family", "Helvetica"))

    def get_color(key):
        val = clr.get(key, "none")
        return hex_to_color(val) if val and str(val).lower() not in ("none", "") else None

    c_page_bg = hex_to_color(clr.get("page_background", "#ffffff"))
    c_header_bg = get_color("header_background")
    c_sidebar_bg = get_color("sidebar_background")
    c_name = hex_to_color(clr.get("name_color", "#000000"))
    c_role_clr = hex_to_color(clr.get("role_color", "#555555"))
    c_heading = hex_to_color(clr.get("section_heading_color", "#000000"))
    c_body = hex_to_color(clr.get("body_text_color", "#333333"))
    c_divider = hex_to_color(clr.get("divider_color", "#cccccc"))
    c_footer_txt = hex_to_color(clr.get("footer_text_color", "#888888"))
    c_footer_bar = get_color("footer_bar_color")
    c_sidebar_txt = colors.white if c_sidebar_bg else c_body

    sz_name = parse_size(typo.get("name_font_size", 16), 16)
    sz_role = parse_size(typo.get("role_font_size", 12), 12)
    sz_heading = parse_size(typo.get("section_heading_font_size", 11), 11)
    sz_body = parse_size(typo.get("body_font_size", 9), 9)
    sz_contact = max(6, sz_body - 1)

    ml = margins_cfg.get("left_mm", 18) * mm
    mr = margins_cfg.get("right_mm", 18) * mm
    mt = margins_cfg.get("top_mm", 10) * mm
    cp = margins_cfg.get("col_padding_mm", 5) * mm

    page_w, page_h = A4

    info = data.get("personal_info", {})
    logo_text = str(header_cfg.get("logo_text", "")).strip()
    logo_pos = header_cfg.get("logo_position", "right")
    show_role = header_cfg.get("show_role_under_name", True) and bool(info.get("role", "").strip())
    show_contact = header_cfg.get("has_contact_in_header", True)
    show_divider = header_cfg.get("has_divider_after_header", True)
    name_align = header_cfg.get("name_alignment", "center")
    footer_text = str(footer_cfg.get("footer_text", "")).strip()
    has_bar = footer_cfg.get("has_colored_bar", False)

    contact_parts: list[str] = []
    for key in ("email", "phone", "location", "linkedin", "github"):
        val = info.get(key, "")
        if val:
            contact_parts.append(val)
    contact_line = "  |  ".join(contact_parts)

    LINE_GAP = 4
    header_h = mt
    if logo_text:
        header_h += sz_name + LINE_GAP
    header_h += sz_name + LINE_GAP
    if show_role:
        header_h += sz_role + LINE_GAP
    if show_contact and contact_parts:
        header_h += sz_contact + LINE_GAP
    if show_divider:
        header_h += 8
    header_h += 10

    footer_h = 14 * mm
    body_h = page_h - header_h - footer_h

    layout_type = layout.get("type", "single_column")
    sidebar_pos = layout.get("sidebar_position", "left")
    sidebar_pct = layout.get("sidebar_width_percent", 30) / 100.0
    two_col = layout_type in ("two_column", "sidebar") and c_sidebar_bg is not None
    sidebar_w = page_w * sidebar_pct if two_col else 0
    main_w = page_w - sidebar_w

    logo_only_h = mt + (sz_name + LINE_GAP if logo_text else 0) + 8

    def draw_page(canvas, doc):
        canvas.saveState()
        is_p1 = (doc.page == 1)
        cur_h = header_h if is_p1 else logo_only_h

        canvas.setFillColor(c_page_bg)
        canvas.rect(0, 0, page_w, page_h, fill=1, stroke=0)

        if c_header_bg:
            canvas.setFillColor(c_header_bg)
            canvas.rect(0, page_h - cur_h, page_w, cur_h, fill=1, stroke=0)

        if two_col and c_sidebar_bg:
            canvas.setFillColor(c_sidebar_bg)
            x = 0 if sidebar_pos == "left" else main_w
            canvas.rect(x, footer_h, sidebar_w, body_h, fill=1, stroke=0)

        y = page_h - mt

        if logo_text:
            canvas.setFont(font_bold, sz_name - 2)
            canvas.setFillColor(c_heading)
            if logo_pos == "right":
                canvas.drawRightString(page_w - mr, y, logo_text)
            elif logo_pos == "left":
                canvas.drawString(ml, y, logo_text)
            else:
                canvas.drawCentredString(page_w / 2.0, y, logo_text)
            y -= (sz_name + LINE_GAP)

        if is_p1:
            canvas.setFont(font_bold, sz_name)
            canvas.setFillColor(c_name)
            if name_align == "center":
                canvas.drawCentredString(page_w / 2.0, y, info.get("name", ""))
            elif name_align == "right":
                canvas.drawRightString(page_w - mr, y, info.get("name", ""))
            else:
                canvas.drawString(ml, y, info.get("name", ""))
            y -= (sz_name + LINE_GAP)

            if show_role:
                canvas.setFont(font_normal, sz_role)
                canvas.setFillColor(c_role_clr)
                if name_align == "center":
                    canvas.drawCentredString(page_w / 2.0, y, info.get("role", ""))
                elif name_align == "right":
                    canvas.drawRightString(page_w - mr, y, info.get("role", ""))
                else:
                    canvas.drawString(ml, y, info.get("role", ""))
                y -= (sz_role + LINE_GAP)

            if show_contact and contact_line:
                canvas.setFont(font_normal, sz_contact)
                canvas.setFillColor(c_role_clr)
                if name_align == "center":
                    canvas.drawCentredString(page_w / 2.0, y, contact_line)
                else:
                    canvas.drawString(ml, y, contact_line)
                y -= (sz_contact + LINE_GAP)

            if show_divider:
                canvas.setStrokeColor(c_divider)
                canvas.setLineWidth(0.8)
                canvas.line(ml, y, page_w - mr, y)

        if has_bar and c_footer_bar:
            canvas.setFillColor(c_footer_bar)
            canvas.rect(0, 0, page_w, 5, fill=1, stroke=0)

        if footer_text:
            canvas.setFont(font_normal, 7)
            canvas.setFillColor(c_footer_txt)
            canvas.drawCentredString(page_w / 2.0, footer_h / 2.0, footer_text)

        canvas.restoreState()

    body_h_later = page_h - logo_only_h - footer_h

    def make_frames(bh, _start_y=0):
        if two_col:
            if sidebar_pos == "left":
                fs = Frame(0, footer_h, sidebar_w, bh, leftPadding=cp, rightPadding=cp,
                           topPadding=10, bottomPadding=10, id="sidebar")
                fm = Frame(sidebar_w, footer_h, main_w, bh, leftPadding=cp, rightPadding=cp,
                           topPadding=10, bottomPadding=10, id="main")
            else:
                fm = Frame(0, footer_h, main_w, bh, leftPadding=cp, rightPadding=cp,
                           topPadding=10, bottomPadding=10, id="main")
                fs = Frame(main_w, footer_h, sidebar_w, bh, leftPadding=cp, rightPadding=cp,
                           topPadding=10, bottomPadding=10, id="sidebar")
            return [fs, fm]
        else:
            return [Frame(ml, footer_h, page_w - ml - mr, bh,
                          leftPadding=0, rightPadding=0,
                          topPadding=10, bottomPadding=10, id="main")]

    doc = BaseDocTemplate(output_path, pagesize=A4,
                          leftMargin=0, rightMargin=0,
                          topMargin=0, bottomMargin=0)
    doc.addPageTemplates([
        PageTemplate(id="first", frames=make_frames(body_h), onPage=draw_page),
        PageTemplate(id="later", frames=make_frames(body_h_later), onPage=draw_page),
    ])

    def S(name, font=font_normal, size=sz_body, color=None, align=TA_LEFT,
          before=0, after=2, leading=None):
        return ParagraphStyle(name,
                              fontName=font, fontSize=size,
                              textColor=color or c_body,
                              alignment=align,
                              spaceBefore=before, spaceAfter=after,
                              leading=leading or (size + 4))

    st = {
        "sh":       S("sh",      font=font_bold,   size=sz_heading, color=c_heading,     before=6, after=3),
        "sh_side":  S("sh_side", font=font_bold,   size=sz_heading, color=c_sidebar_txt, before=6, after=3),
        "body":     S("body",    font=font_normal, size=sz_body,    color=c_body,        after=2),
        "body_s":   S("body_s",  font=font_normal, size=sz_body,    color=c_sidebar_txt, after=2),
        "bold":     S("bold",    font=font_bold,   size=sz_body,    color=c_body,        after=1),
        "bold_s":   S("bold_s",  font=font_bold,   size=sz_body,    color=c_sidebar_txt, after=1),
        "italic":   S("italic",  font=font_italic, size=sz_body - 1, color=c_body,       after=1),
        "bullet":   S("bullet",  font=font_normal, size=sz_body,    color=c_body,        after=1),
        "bullet_s": S("bullet_s", font=font_normal, size=sz_body,   color=c_sidebar_txt, after=1),
    }
    st["bullet"].leftIndent = 12
    st["bullet_s"].leftIndent = 12

    story = [NextPageTemplate("later")]
    all_sections = data.get("sections", [])

    template_section_order = [s.strip() for s in sections_cfg.get("order", [])]
    filtered_sections: list[dict] = []
    for tmpl_sec in template_section_order:
        for ds in all_sections:
            if ds.get("title", "").lower() == tmpl_sec.lower():
                filtered_sections.append(ds)
                break
    all_sections = filtered_sections

    sidebar_titles = [s.lower() for s in sections_cfg.get("sidebar_sections", [])]
    sidebar_items: list = []
    main_items: list = []
    bullet_char = styling.get("bullet_char", "•")

    for sec in all_sections:
        title = sec.get("title", "")
        content = sec.get("content", {})
        is_side = title.lower() in sidebar_titles and two_col

        target = sidebar_items if is_side else main_items
        h_style = st["sh_side"]  if is_side else st["sh"]
        b_style = st["body_s"]   if is_side else st["body"]
        bl_style = st["bullet_s"] if is_side else st["bullet"]
        bo_style = st["bold_s"]  if is_side else st["bold"]
        div_col = c_sidebar_txt  if is_side else c_divider

        heading_text = title.upper() if styling.get("section_heading_uppercase") else title
        target.append(Paragraph(heading_text, h_style))

        if styling.get("section_divider", True):
            target.append(HRFlowable(width="100%", thickness=0.5,
                                     color=div_col, spaceAfter=4))

        if content.get("text"):
            target.append(Paragraph(content["text"], b_style))
            target.append(Spacer(1, 6))

        elif content.get("items"):
            for item in content["items"]:
                target.append(Paragraph(f"{bullet_char}  {item}", bl_style))
            target.append(Spacer(1, 6))

        elif content.get("entries"):
            template_fields = sections_cfg.get("section_fields", {}).get(title, [])

            for entry in content["entries"]:
                block: list = []
                metadata = entry.get("metadata", {})

                heading = entry.get("heading", "")
                if heading:
                    block.append(Paragraph(f"<b>{heading}</b>", bo_style))

                subheading = entry.get("subheading", "")
                location = entry.get("location", "")
                if subheading:
                    sub_line = subheading + (f"  |  {location}" if location else "")
                    block.append(Paragraph(sub_line, st["italic"]))

                if template_fields:
                    for field in template_fields:
                        if field.lower() in ("project", "name", "title", "position",
                                             "degree", "company", "institution"):
                            continue
                        val = metadata.get(field, "") or metadata.get(field.lower(), "")
                        if field.lower() in ("responsibilities", "duties",
                                             "achievements", "key responsibilities"):
                            if val:
                                block.append(Paragraph(f"<b>{field}:</b>", bo_style))
                                items = val if isinstance(val, list) else [val]
                                for item in items:
                                    block.append(Paragraph(f"{bullet_char}  {item}", bl_style))
                            for bp in entry.get("bullets", []):
                                block.append(Paragraph(f"{bullet_char}  {bp}", bl_style))
                        elif val:
                            block.append(Paragraph(f"<b>{field}:</b> {val}", b_style))
                else:
                    duration = entry.get("duration", "")
                    if duration:
                        block.append(Paragraph(f"<b>Duration:</b> {duration}", b_style))
                    for key, val in metadata.items():
                        if val:
                            val_str = ", ".join(val) if isinstance(val, list) else str(val)
                            if key.lower() in ("responsibilities", "duties"):
                                block.append(Paragraph(f"<b>{key}:</b>", bo_style))
                                for item in (val if isinstance(val, list) else [val]):
                                    block.append(Paragraph(f"{bullet_char}  {item}", bl_style))
                            else:
                                block.append(Paragraph(f"<b>{key}:</b> {val_str}", b_style))
                    if entry.get("description"):
                        block.append(Paragraph(entry["description"], b_style))
                    for bp in entry.get("bullets", []):
                        block.append(Paragraph(f"{bullet_char}  {bp}", bl_style))

                block.append(Spacer(1, 8))
                target.append(KeepTogether(block))
        else:
            target.append(Spacer(1, 4))

    if two_col:
        story += sidebar_items
        story.append(FrameBreak())
    story += main_items

    doc.build(story)
    logger.info(f"=== PDF saved: {output_path} ===")


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

async def run_conversion(
    resume_path: str,
    template_path: str,
    output_path: str,
    api_key: Optional[str] = None,
) -> dict:
    """
    Convert a resume (PDF, DOCX, or DOC) to match a template PDF format
    using GPT-4o + ReportLab.

    Args:
        resume_path:   Absolute path to the source resume (PDF/DOCX/DOC).
        template_path: Absolute path to the target template PDF.
        output_path:   Absolute path where the converted PDF will be written.
        api_key:       OpenAI API key. Falls back to OPENAI_API_KEY env var.

    Returns:
        dict with keys: output_path, format, content
    """
    if not Path(resume_path).exists():
        raise FileNotFoundError(f"Resume not found: {resume_path}")
    if not Path(template_path).exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    resolved_key = (api_key or "").strip() or os.environ.get("OPENAI_API_KEY", "").strip()
    if not resolved_key:
        raise ValueError("OpenAI API key is missing. Set OPENAI_API_KEY in .env")

    # Validate resume format early so we get a clear error before any API call
    resume_ext = Path(resume_path).suffix.lower()
    if resume_ext not in SUPPORTED_RESUME_EXTENSIONS:
        raise ValueError(
            f"Unsupported resume format '{resume_ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_RESUME_EXTENSIONS))}"
        )

    client = OpenAI(api_key=resolved_key)

    logger.info(f"=== Starting resume conversion: {resume_path} → {output_path} ===")

    # Resume text — routed through data_extraction.py (PDF/DOCX/DOC all handled)
    resume_text = await extract_text(resume_path)
    logger.info(f"--- Resume text extracted: {len(resume_text)} characters ---")

    # Template is always a PDF — use pdfplumber for coordinates + GPT-4o images
    import asyncio
    template_text = await asyncio.to_thread(_extract_template_text, template_path)
    hf_data = extract_header_footer(template_path)
    template_images = await asyncio.to_thread(pdf_to_images, template_path)
    logger.info(f"--- Template text extracted. Logo: '{hf_data['logo_text']}' ---")

    fmt = analyze_template(client, template_images, template_text, hf_data)
    data = extract_resume_data(client, resume_text, fmt)

    await asyncio.to_thread(build_pdf, data, fmt, output_path)

    logger.info(f"=== Conversion complete: {output_path} ===")
    return {
        "output_path": str(output_path),
        "format": fmt,
        "content": data,
    }
