from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import os
import cohere
import asyncio
from typing import List

load_dotenv()

async def get_embedding_model():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        request_timeout=60,
        max_retries=3,
        chunk_size=1000,
        show_progress_bar=True,
    )


def rerank_documents(query : str , docs : List[dict]):
    co = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))
    result = co.rerank(
        model="rerank-v4.0-pro",
        query=query,
        documents=docs,
        top_n=len(docs),
    )
    return result
