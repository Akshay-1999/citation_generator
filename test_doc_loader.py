import re
import json
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
import asyncio
from langsmith import traceable, trace
import os
from typing import List
from agents.agent_utils import get_resume_extractor_system_prompt
from dotenv import load_dotenv
load_dotenv(override=True)  # loads .env from the current working directory

class resume_extractor_agent:
    def __init__(self , client , user_id = None ):
        self.client = client
        self.user_id = user_id
    
        from agents.agent_utils import contain_extraction_system_prompt
        self.prompt = ChatPromptTemplate.from_messages([
        ("system" , contain_extraction_system_prompt(self.user_prompt)),
        ("human" , "extract the data from this Resume : {resume_text}\n\n extract the complete details from this"),
        ("placeholder" , "{agent_scratchpad}")  
        ])
        

        