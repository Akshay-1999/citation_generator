import os
import json
import uuid
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from docxtpl import DocxTemplate, RichText
from docx2pdf import convert as docx2pdf_convert

from agents.agent_utils import contain_extraction_system_prompt
from utils.logger_instances import file_convert_logger as logger

load_dotenv(override=True)

class ResumeExtractorAgent:
    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=contain_extraction_system_prompt()),
            ("human", "Extract the data from this Resume: {resume_text}\n\nCRITICAL INSTRUCTION: Extract the complete details. For the 'responsibilities' field in each project, you MUST extract at least 3 to 5 distinct, highly detailed bullet points summarizing their exact tasks, technical contributions, and achievements. Do not group them into just one point; break their work down into multiple specific points.")
        ])
        
        # Using a simple chain
        self.chain = self.prompt | ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.0,
            max_tokens=4096
        )

    async def run_agent(self, resume_text: str , feedback : str = None) -> dict:
        logger.info("--- Extracting and remapping resume content with LLM ---")
        if feedback:
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=contain_extraction_system_prompt()),
                ("human", "Extract the data from this Resume: {resume_text}\n\nCRITICAL INSTRUCTION: Extract the complete details. For the 'responsibilities' field in each project, you MUST extract at least 3 to 5 distinct, highly detailed bullet points summarizing their exact tasks, technical contributions, and achievements.\n\nUSER FEEDBACK PROVIDED: {feedback}\n\nCRITICAL OVERRIDE: You MUST enrich and modify the extracted resume data strictly according to the USER FEEDBACK. If the feedback asks you to add more data, invent or expand upon the project details, you ARE ALLOWED to invent highly professional, plausible data to fulfill the feedback. Override any previous 'do not hallucinate' instructions to fully satisfy this user request.")
            ])
            chain = prompt | ChatAnthropic(
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                temperature=0.3,
                max_tokens=4096
            )
            response = await chain.ainvoke({
                "resume_text": resume_text,
                "feedback": feedback
            })
        else:
            response = await self.chain.ainvoke({
                "resume_text": resume_text,
            })
        
        content = response.content
        if isinstance(content, list):
            content = "".join(item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in content)
        content = str(content).strip()
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        try:
            data = json.loads(content)
            logger.info(f"--- Resume parsed successfully for candidate: {data.get('candidate_name', 'Unknown')} ---")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {e}\nContent: {content}")
            raise ValueError("Failed to extract structured data from resume.")

def convert_to_richtext(obj):
    if isinstance(obj, str):
        if '\n' in obj:
            return RichText(obj)
        return obj
    elif isinstance(obj, dict):
        return {k: convert_to_richtext(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_richtext(v) for v in obj]
    return obj

def safe_join(values):
    if not values:
        return ""
    return ", ".join(values)

def generate_docx_and_pdf_json_file(data: dict, template_path: str, pdf_dir: str, docx_dir: str, filename_base: str) -> dict:
    """
    Generates DOCX from JSON data using docxtpl, then converts it to PDF.
    Returns the file paths.
    """
    Path(pdf_dir).mkdir(parents=True, exist_ok=True)
    Path(docx_dir).mkdir(parents=True, exist_ok=True)
    
    technical_skills = data.get("technical_skills", {})

    context = {
        "candidate_name": data.get("candidate_name", ""),
        "candidate_designation_based_on_jd": data.get("candidate_designation_based_on_jd", ""),
        "profile_summary": data.get("profile_summary", ""),

        # Skills
        "languages": safe_join(technical_skills.get("languages", [])),
        "operating_systems": safe_join(technical_skills.get("operating_systems", [])),
        "ui_technologies": safe_join(technical_skills.get("ui_technologies", [])),
        "databases": safe_join(technical_skills.get("databases", [])),
        "frameworks": safe_join(technical_skills.get("frameworks", [])),
        "tools": safe_join(technical_skills.get("tools", [])),
        "ides": safe_join(technical_skills.get("ides", [])),
        "delivery_methodologies": safe_join(technical_skills.get("delivery_methodologies", [])),

        # Projects
        "project_details": data.get("project_details", []),

        # Certifications
        "certifications": data.get("certifications", [])
    }
    
    context = convert_to_richtext(context)

    # 1. Generate DOCX
    logger.info(f"--- Rendering DOCX template from {template_path} ---")
    doc = DocxTemplate(template_path)
    doc.render(context)

    docx_filename = f"{filename_base}.docx"
    docx_path = os.path.join(docx_dir, docx_filename)
    doc.save(docx_path)
    logger.info(f"=== DOCX saved: {docx_path} ===")

    # 2. Convert to PDF using docx2pdf
    pdf_filename = f"{filename_base}.pdf"
    pdf_path = os.path.join(pdf_dir, pdf_filename)
    
    logger.info(f"--- Converting DOCX to PDF: {pdf_path} ---")
    try:
        import platform
        if platform.system() == "Windows":
            # Initialize COM for the current background thread
            import pythoncom
            pythoncom.CoInitialize()
            
            # docx2pdf is synchronous and uses MS Word COM, which can be blocking.
            docx2pdf_convert(docx_path, pdf_path)
        else:
            # Use LibreOffice in headless mode for Linux/macOS
            import subprocess
            import shutil
            
            logger.info("Using LibreOffice for Linux/macOS PDF conversion")
            
            # Find the LibreOffice executable (could be 'libreoffice' or 'soffice')
            lo_exec = shutil.which("libreoffice") or shutil.which("soffice") or "/usr/bin/libreoffice"
            
            # Ensure standard system paths are in the environment so the libreoffice wrapper script can find basic tools like 'dirname'
            env = os.environ.copy()
            system_paths = "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin"
            env["PATH"] = f"{env.get('PATH', '')}:{system_paths}" if env.get('PATH') else system_paths
            
            process = subprocess.run([
                lo_exec, "--headless", "--convert-to", "pdf",
                "--outdir", pdf_dir, docx_path
            ], capture_output=True, text=True, env=env)
            
            if process.returncode != 0:
                raise Exception(f"LibreOffice conversion failed: {process.stderr}")
                
        logger.info(f"=== PDF saved: {pdf_path} ===")
    except Exception as e:
        logger.error(f"Failed to convert DOCX to PDF: {e}")
        # If PDF conversion fails, we still have the DOCX
        pdf_filename = None

    return {
        "docx_filename": docx_filename,
        "pdf_filename": pdf_filename,
        "docx_path": docx_path,
        "pdf_path": pdf_path
    }

async def run_docxtpl_conversion(resume_path: str, template_path: str, pdf_dir: str, docx_dir: str, filename_base: str , feedback : str = None) -> dict:
    """
    Main entry point for new conversion process.
    """
    if not Path(resume_path).exists():
        raise FileNotFoundError(f"Resume not found: {resume_path}")
    if not Path(template_path).exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    logger.info(f"=== Starting docxtpl resume conversion: {resume_path} ===")

    # Extract text from uploaded resume
    from document_processing.resume_converter import extract_text
    resume_text = await extract_text(resume_path)
    logger.info(f"--- Resume text extracted: {len(resume_text)} characters ---")

    # Run Agent to get structured JSON
    extractor = ResumeExtractorAgent()
    data = await extractor.run_agent(resume_text)

    # Generate documents
    # Run synchronous IO/COM tasks in a thread
    result = await asyncio.to_thread(generate_docx_and_pdf_json_file, data, template_path, pdf_dir, docx_dir, filename_base)

    logger.info(f"=== Conversion complete for {filename_base} ===")
    return {
        "filename_base": filename_base,
        "content": data,
        "files": result
    }
