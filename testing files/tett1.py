from agents.agents_main import RAGAgent , ResumeMappingAgent
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

load_dotenv()

async def main():
    client = ChatOpenAI(model="gpt-5-mini", api_key=os.getenv("OPENAI_API_KEY"))
    agent = ResumeMappingAgent(client=client)
    response, matches, source = await agent.process_resume_mapping(job_description="can you give me a condidate who is good in manual testing and having expreance more than 5+ years and he should also have a good sql knowledge and if he has some exreance in gen ai will e good", 
    file_names=["Akshay Patil Resume.pdf"], user_id="ac68c8ac-0c3d-458c-bd2e-b707c278f7f1")
    print(response)
    print(matches)
    print(source)

if __name__ == "__main__":
    asyncio.run(main())