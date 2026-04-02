import asyncio
import logging
from typing import Any, Dict, List
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langsmith import traceable
from utils.logging_utils import set_system_logger
from embedding.embedder import query_similar_documents

logger = set_system_logger("system_logger")
#query_similar_documents(query : str , user_id : str = None , top_k : int = 5 , pinecone_filter : dict = None)

def get_tool_definitions(agent_instance) -> list[Any]:
    @tool
    @traceable(name="search_uploaded_documents", run_type="tool")
    async def search_uploaded_documents(query: str) -> Dict[str, Any]:
        """
        Query the uploaded documents for similar information to the query.
        """
        logger.info(f"--- agent using search_uploaded_documents for the: {query} ---")
        user_id = agent_instance.user_id
        logger.info(f"--- agent using search_uploaded_documents for the: {query} and user_id: {user_id} ---")
        try:
            top_k = 50
            result = await query_similar_documents(query , user_id , top_k)
        except asyncio.TimeoutError:
            logger.error(f"=== search_uploaded_documents timed out for the query: {query} ===")
            return {"matches": [], "no_results": True}
        except Exception as e:
            logger.error(f"=== search_uploaded_documents failed: {e} ===")
            return {"matches": [], "no_results": True}

        matches = result.get("matches" , [])
        if not matches:
            return {"matches": [], "no_results": True}
        
        matches.sort(key = lambda m:m.metadata.get("reranked_score" , 0), reverse=True)

        top1_score = matches[0].metadata.get("reranked_score" , 0)
        weighted_avg = sum(m.metadata.get("reranked_score" , 0) / (i + 1) for i, m in enumerate(matches)) / sum(1/(i+1) for i in range(len(matches)))
        logger.info(f"--- top1_score: {top1_score}, weighted_avg: {weighted_avg} ---")
        return {"matches": matches, "no_results": False}
    @tool
    @traceable(name="tavily_search_invoke", run_type="tool")
    async def tavily_search_invoke(query: str) -> Dict[str, Any]:
        """
        Search the web using Tavily to retrieve current or general knowledge
        that is not available in the uploaded document corpus.
        """
        logger.info(f"--- agent using tavily web search for the: {query} ---")
        try:    
            tavily_tool = TavilySearch(max_results=1, tracing_disabled=True)
            return tavily_tool.invoke({"query": query})
        except Exception as e:
            logger.error(f"=== Web search failed: {e} ===")
            return {"error": str(e)}
    
    return [search_uploaded_documents, tavily_search_invoke]

def get_resume_mapping_tools(agent_instance):
    """
    return a list of tools for custom resume mapping
    """
    @tool
    @traceable(name="resume_mapping_search", run_type="tool")
    async def resume_mapping_search(query : str , file_names : List[str])-> dict:
        """ 
        Retrieve relevant answer chunks for resume mapping given a JD and selected document names.
        
        Args:
            query: The user's query to search for or the JD
            file_names: List of ALL file names to search in (must be provided as a complete list in one call)
        
        Returns:
            dict: Contains matched text chunks as plain text from all specified documents
        """

        user_id = agent_instance.user_id
        logger.info(f"--- agent using resume_mapping_search for the: {query} and user_id: {user_id} ---")
        filter = {"file_name": {"$in": file_names}}
        try:
            result = await query_similar_documents(query , user_id , top_k = 50 , pinecone_filter = filter)
        except asyncio.TimeoutError:
            logger.error(f"=== resume_mapping_search timed out for the query: {query} ===")
            return {"matches": [], "no_results": True}
        except Exception as e:
            logger.error(f"=== resume_mapping_search failed: {e} ===")
            return {"matches": [], "no_results": True}

        matches = result.get("matches" , [])
        if not matches:
            return {"matches": [], "no_results": True}
        
        matches.sort(key = lambda m:m.metadata.get("reranked_score" , 0), reverse=True)

        top1_score = matches[0].metadata.get("reranked_score" , 0)
        weighted_avg = sum(m.metadata.get("reranked_score" , 0) / (i + 1) for i, m in enumerate(matches)) / sum(1/(i+1) for i in range(len(matches)))
        logger.info(f"--- top1_score: {top1_score}, weighted_avg: {weighted_avg} ---")
        return {"matches": matches, "no_results": False}

    return [resume_mapping_search]