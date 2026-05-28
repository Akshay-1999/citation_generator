import asyncio
import os
import json
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv(override=True)

class resume_extractor_agent:
    def __init__(self, client, user_id=None):
        self.client = client
        self.user_id = user_id
    
        from agents.agent_utils import contain_extraction_system_prompt
        
        from langchain_core.messages import SystemMessage
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=contain_extraction_system_prompt()),
            ("human", "Extract the data from this Resume: {resume_text}\n\nCRITICAL INSTRUCTION: Extract the complete details. For the 'responsibilities' field in each project, you MUST extract at least 3 to 5 distinct, highly detailed bullet points summarizing their exact tasks, technical contributions, and achievements. Do not group them into just one point; break their work down into multiple specific points.")
        ])

        # Using a simple chain instead of AgentExecutor since there are no tools
        self.chain = self.prompt | ChatOpenAI(model="gpt-5o-mini", api_key=os.getenv("OPENAI_API_KEY"), temperature=0.0)

    async def run_agent(self, resume_text):
        # Await the chain invocation
        response = await self.chain.ainvoke({
            "resume_text": resume_text
        })
        # Get the text content
        content = response.content.strip()
        
        # Clean up markdown code blocks if the LLM added them
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback to returning raw string if JSON parsing fails
            return response.content

async def main():
    from document_processing.data_extraction import extract_with_pymupdf
    
    print("Extracting text from PDF...")
    resume_txt, metadata = await extract_with_pymupdf(file_path=r"D:\Akshay\Work and Document\Training\LLM AND AI\citation\citation_generator\uploaded_files\Naukri_KaranamRao[18y_0m].doc")
    print("Extraction complete. Metadata:", metadata)
    
    print("\nRunning extractor agent...")
    extractor = resume_extractor_agent(client="akshay", user_id="user_1")
    resume_content = await extractor.run_agent(resume_txt)
    
    print("\n--- Extracted Content ---")
    print(resume_content)

    import json
    from docxtpl import DocxTemplate
    from docx.shared import Pt
    from docx import Document
    import os

    # =========================================================
    # LOAD EXTRACTED JSON
    # =========================================================

    # with open(r"D:\Akshay\Work and Document\Training\LLM AND AI\citation\citation_generator\resume_content.json", "r", encoding="utf-8") as f:
    #     data = json.load(f)
    data = resume_content

    from docxtpl import RichText

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

    # =========================================================
    # LOAD TEMPLATE
    # =========================================================

    template_path = r"D:\Akshay\Work and Document\Training\LLM AND AI\citation\citation_generator\templates\Estuate_Template_main.docx"

    doc = DocxTemplate(template_path)

    # =========================================================
    # RENDER TEMPLATE
    # =========================================================

    doc.render(context)

    # =========================================================
    # SAVE OUTPUT
    # =========================================================

    output_path = "Generated_Resume.docx"

    doc.save(output_path)

    print(f"Resume generated successfully: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())