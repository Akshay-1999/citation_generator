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

from dotenv import load_dotenv
load_dotenv(override=True)  # loads .env from the current working directory

from agents.agents_tool import get_tool_definitions , get_resume_mapping_tools 
from agents.agent_utils import get_combined_system_prompt , extract_llm_suggested_chunks , verify_llm_chunks
from utils.logger_instances import system_logger as logger

class RAGAgent:

    def __init__(self , client ,user_id = None, user_prompt = ""):
        self.client = client
        self.user_id = user_id
        self.user_prompt = user_prompt
        

        # confidence boundaries for text-embedding-3-large
        self.confidence_boundaries = {
            "high": 0.55,
            "medium": 0.45,
            "low": 0.35
        }
        self.tools = get_tool_definitions(self)
        self.agent = self._setup_agent()  # initialized via await initialize()
        
    def _setup_agent(self):
        llm_with_tools = self.client.bind_tools(self.tools)
        system_prompt = get_combined_system_prompt(self.user_prompt)
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        agent  = create_tool_calling_agent(llm = llm_with_tools, prompt = prompt, tools = self.tools)
        logger.info(f"=== Agent created with tools: {self.tools} ===")
        return AgentExecutor(agent=agent,
            tools=self.tools,
            verbose=False,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            max_iterations=4,
            early_stopping_method="generate")   
    
    async def run_agent(self, query: str, messages: List[dict] = None, user_id= None , pinecone_filter : List[str] | None = None):
        try:
            if user_id is None  :
                logger.warning("--- No user_id provided to process_query, using default from agent initialization ---")
                logger.info(f"--- User ID: {self.user_id} ---")
                user_id = self.user_id

            if messages is None:
                logger.info("--- No messages provided to process_query, using default from agent initialization ---")
                messages = []
            
            #convert messages to the format required by the agent
            chat_history = [
                HumanMessage(content=message["content"]) if message["role"] == "user" else AIMessage(content=message["content"]) for message in messages[-10:]
            ]
            
            # Store for tool access
            self.pinecone_filter = pinecone_filter 
            
            # If files are selected, inform the LLM internally so it knows the context
            effective_input = query
            if pinecone_filter and len(pinecone_filter) > 0:
                files_list = ", ".join(pinecone_filter)
                effective_input = f"[Selected Files: {files_list}]\n\n{query}"

            result = await self.agent.ainvoke({    
                "input": effective_input,
                "chat_history": chat_history,
                "pinecone_filter": pinecone_filter
            })
            logger.info(f"=== Agent result: output={result.get('output', '')[:200]}, steps={len(result.get('intermediate_steps', []))} ===")
            
            matches = []
            used_search_uploaded_documents = False

            for action, output in result.get("intermediate_steps", []):
                if action.tool == "search_uploaded_documents":
                    raw_matches = output.get("matches", [])
                    # ScoredVector is not JSON serializable, convert to dict
                    for m in raw_matches:
                        if hasattr(m, 'to_dict'):
                            matches.append(m.to_dict())
                        else:
                            matches.append({
                                "id": getattr(m, "id", None),
                                "score": getattr(m, "score", 0.0),
                                "metadata": getattr(m, "metadata", {})
                            })
                    used_search_uploaded_documents = True
                    logger.info(f"--- Document search returned {len(matches)} matches ---")
                    break
            
            result["matches"] = matches
            result["used_search_uploaded_documents"] = used_search_uploaded_documents
            answer = result.get("output", "").strip()
            if used_search_uploaded_documents:
                logger.info(f"Document search returned {len(matches)} matches")
                suggested_chunks = extract_llm_suggested_chunks(result)
                verified_chunks = verify_llm_chunks(suggested_chunks, matches, limit=3)
                logger.info(f"Verified chunks: {verified_chunks}")
                answer = re.sub(r"CITED_CHUNKS:\s*\[.*?\](\s*)?$", "", answer, flags=re.DOTALL).strip()
                return answer , verified_chunks , 'Document derived'
            else:
                logger.info("not used the search_uploaded_documents tool")
                return answer , [] , 'LLM derived'
        except Exception as e:
            logger.error(f"=== Error in processing query: {e} ===")
            error_message = f"Encountered an error: {str(e)}"
            return error_message , [] , 'Error'

class ResumeMappingAgent:
    def __init__(self , client , user_id = None , user_prompt = "" ):
        self.client = client
        self.user_id = user_id
        self.user_prompt = user_prompt
        #get custom mapping tools
        self.tools = get_resume_mapping_tools(self)

        from agents.agent_utils import get_resume_mapping_system_prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system" , get_resume_mapping_system_prompt(self.user_prompt)),
            ("human" , "Job Description : {job_description}\n\n search this Job Description in the Resume : {file_names}"),
            ("placeholder" , "{agent_scratchpad}")  
        ])
        logger.info(f"=== Agent created with tools: {self.tools} ===")
        llm_with_tools = self.client.bind_tools(self.tools)
        agent = create_tool_calling_agent(
            llm = llm_with_tools , 
            prompt = self.prompt ,
            tools = self.tools)

        self.executor = AgentExecutor(
            agent = agent ,
            tools = self.tools ,
            verbose = False ,
            return_intermediate_steps=True,
            handle_parsing_errors=True,
            max_iterations=5, 
            early_stopping_method="generate"
        )
    async def process_resume_mapping(self , job_description : str , file_names : list , user_id : str):
        try:
            logger.info(f"--- User ID: {user_id} ---")
            self.user_id = user_id  # update so the tool closure can read it
            result = await self.executor.ainvoke({
                "job_description" : job_description,
                "file_names" : file_names
            })
            answer = result.get("output" , "").strip()
            matches = []
            used_resume_mapping_search = False
            for action , output in result.get("intermediate_steps" , []):
                if action.tool == "resume_mapping_search" and isinstance(output , dict):
                    matches = output.get("matches" , [])
                    logger.info(f"--- Resume mapping search returned {len(matches)} matches ---")
                    used_resume_mapping_search = True
                    break
            result["matches"] = matches
            result["used_resume_mapping_search"] = used_resume_mapping_search
            answer = result.get("output", "").strip()
            
            # Attempt to parse answer as JSON if it looks like JSON
            try:
                # Remove potential markdown code blocks if the LLM included them
                json_match = re.search(r'(\{.*\}|\[.*\])', answer, re.DOTALL)
                if json_match:
                    parsed_answer = json.loads(json_match.group(1))
                    answer = parsed_answer
            except Exception as json_err:
                logger.warning(f"Could not parse agent output as JSON: {json_err}")
                # Fallback to raw string if parsing fails
            
            if used_resume_mapping_search:
                logger.info(f"Document search returned {len(matches)} matches")
                return answer , matches , 'Document derived'
            else:
                logger.info("not used the search_uploaded_documents tool")
                return answer , [] , 'LLM derived'
        except Exception as e:
            logger.error(f"=== Error in processing resume mapping: {e} ===")
            error_message = f"Encountered an error: {str(e)}"
            return error_message , [] , 'Error'
