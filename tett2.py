import asyncio
import os
import pandas as pd
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from agents.agents_main import ResumeMappingAgent

load_dotenv()

async def main():
    # Initialize the LLM client
    client = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    
    # Initialize the Agent
    agent = ResumeMappingAgent(client=client)
    
    # Define Job Description and Files
    job_description = """
    We are looking for a candidate with:
    - 5+ years of experience in manual testing and QA methodologies.
    - Strong SQL knowledge (SQL Server, Oracle).
    - Experience in Gen AI / RAG is a plus.
    - Excellent communication skills.
    """
    
    # Note: Using the file name from your previous request
    file_names = ["Naukri_SrikanthN[8y_0m].pdf","Naukri_UjjwalGupta[10y_0m] (1).pdf","AsifKalam_Fullstack.pdf"]
    user_id = "ac68c8ac-0c3d-458c-bd2e-b707c278f7f1"
    
    print(f"--- Running Resume Mapping for: {file_names} ---")
    
    try:
        response, matches, source = await agent.process_resume_mapping(
            job_description=job_description,
            file_names=file_names,
            user_id=user_id
        )
        
        print("\n--- Agent Response (Structured) ---")
        print(response)
        
        # Convert to DataFrame if response is a dict
        if isinstance(response, dict):
            # If it's a single dict, wrap it in a list for DataFrame
            df = pd.DataFrame([response])
        elif isinstance(response, list):
            df = pd.DataFrame(response)
        else:
            print("Warning: Response is not a dictionary or list. Cannot create DataFrame easily.")
            df = pd.DataFrame([{"raw_output": response}])
            
        print("\n--- DataFrame Structure ---")
        print(df)
        
        # Save to Excel
        output_file = "candidate_screening_results.xlsx"
        df.to_excel(output_file, index=False)
        print(f"\n--- Results saved to {output_file} ---")
        
    except Exception as e:
        print(f"An error occurred during testing: {e}")

if __name__ == "__main__":
    asyncio.run(main())
