# from document_processing.document_loader import MemoryEfficientFileloader
# import asyncio
# from pathlib import Path
# async def main():
#     async def progress_callback(completed_chunks, total_chunks):
#         print(f"Processed {completed_chunks}/{total_chunks} chunks")
#     file_path = Path(r"D:\Akshay\Work and Document\Training\LLM AND AI\citation\citation_generator\uploaded_files\Fundamentals_of_Database_Systems_6th_Edition-1.pdf")
#     file_loader = MemoryEfficientFileloader(file_path , progress_callback=progress_callback)
#     async for chunk in file_loader._process_file(file_path , user_id="1"):
#         print(chunk)

# if __name__ == "__main__":
#     asyncio.run(main())



# from langchain.schema import Document
# import tiktoken
# # from utils.log_config import get_system_logger
# from typing import List
# import os
# from pathlib import Path
# # from document_processing.documentloader import MemoryEfficientLoader
# from langchain.text_splitter import TextSplitter

# # Character sets for intelligent text splitting
# CJK_WORD_BREAKS = [
#     "、", "，", "；", "：", "（", "）", "【", "】", "「", "」", "『", "』", "〔", "〕",
#     "〈", "〉", "《", "》", "〖", "〗", "〘", "〙", "〚", "〛", "〝", "〞", "〟", "〰",
#     "–", "—", "'", "'", "‚", "‛", """, """, "„", "‟", "‹", "›"
# ]
# CJK_SENTENCE_ENDINGS = ["。", "！", "？", "‼", "⁇", "⁈", "⁉"]
# STANDARD_SENTENCE_ENDINGS = [".", "!", "?"]
# STANDARD_WORD_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]


# class EnhancedTextSplitter(TextSplitter):
#     def __init__(self, chunk_size=1000, chunk_overlap=None, model_name="text-embedding-3-large",
#                  max_tokens_per_section=1000, overlap_percent=15, sentence_search_limit=150):
#         if chunk_overlap is None:
#             chunk_overlap = int(chunk_size * overlap_percent / 100)
#         super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
#         self.max_tokens = max_tokens_per_section
#         self.encoding = tiktoken.get_encoding("cl100k_base")
#         self.overlap_percent = overlap_percent
#         self.sentence_endings = STANDARD_SENTENCE_ENDINGS + CJK_SENTENCE_ENDINGS
#         self.word_breaks = STANDARD_WORD_BREAKS + CJK_WORD_BREAKS
#         self.sentence_search_limit = sentence_search_limit
#         # Add minimum token count to prevent tiny chunks
#         self.min_tokens = max(50, int(self.max_tokens * 0.1))

#     def count_tokens(self, text: str) -> int:
#         try:
#             return len(self.encoding.encode(text))
#         except Exception as e:
#             logger.error(f"Tokenization failed: {e}")
#             return 0

#     def split_text(self, text: str) -> List[str]:
#         return self.split_text_by_tokens(text)

#     def split_text_by_tokens(self, text: str, depth: int = 0) -> List[str]:
#         """
#         Fixed version with recursion depth limit and better error handling.
#         """
#         # Prevent infinite recursion
#         if depth > 10:
#             logger.warning(f"Max recursion depth reached, force splitting text of length {len(text)}")
#             # Force split in the middle as last resort
#             mid = len(text) // 2
#             return [text[:mid], text[mid:]]
        
#         tokens = self.encoding.encode(text)
#         if len(tokens) <= self.max_tokens:
#             return [text]

#         # Find optimal split point
#         start = len(text) // 2
#         pos = 0
#         split_position = -1
#         max_range = min(self.sentence_search_limit, len(text) // 2)

#         # Search for sentence endings
#         while pos < max_range:
#             left = start - pos
#             right = start + pos

#             if left >= 0 and left < len(text) and text[left] in self.sentence_endings:
#                 split_position = left + 1  # Include the sentence ending
#                 break
#             if right < len(text) and text[right] in self.sentence_endings:
#                 split_position = right + 1  # Include the sentence ending
#                 break
#             pos += 1

#         if split_position > 0 and split_position < len(text):
#             first_half = text[:split_position].strip()
#             second_half = text[split_position:].strip()
            
#             # Ensure both halves are meaningful
#             if len(first_half) < 10 or len(second_half) < 10:
#                 # Fall back to middle split with overlap
#                 middle = len(text) // 2
#                 overlap = int(len(text) * (self.overlap_percent / 100))
#                 first_half = text[:middle + overlap]
#                 second_half = text[middle - overlap:]
#         else:
#             # No good sentence boundary found, use middle split with overlap
#             middle = len(text) // 2
#             overlap = int(len(text) * (self.overlap_percent / 100))
#             first_half = text[:middle + overlap]
#             second_half = text[middle - overlap:]

#         # Recursively split both halves
#         left_chunks = self.split_text_by_tokens(first_half, depth + 1) if first_half.strip() else []
#         right_chunks = self.split_text_by_tokens(second_half, depth + 1) if second_half.strip() else []
        
#         return left_chunks + right_chunks

# class 


# def main():
#     
#     # text = """machinelearningartificialintelligencelargelanguagemodelneuralnetworkdeepreinforcementlearningdatapreprocessingfeatureengineeringvectorizationembeddingretrievalaugmentedgenerationtransformerarchitectureattentionmechanismsemanticsearchknowledgerepresentationinformationextractionnaturallanguageprocessingtextgenerationdocumentanalysiscontextunderstandingmodeloptimizationhyperparametertuningcomputervisiondatasciencealgorithmdevelopmentsoftwareengineeringcloudcomputingdistributedtrainingmodeldeploymentautomationpipelineintegrationcontinuouslearningexperimentationframeworkscalabilityperformanceevaluationstatisticalmodelingpredictiveanalyticsdatavalidationerrorhandlingdebuggingversioncontrolcollaborativedevelopment"""
#     #text = """The history of the Internet has its roots in the Cold War and the desire of the United States government to have a decentralized communication network that could survive a nuclear attack. The Advanced Research Projects Agency Network (ARPANET), established in 1969, was the first wide-area packet-switching network and the precursor to the modern Internet. It connected four university computers and allowed researchers to share resources and information. Over the next two decades, ARPANET expanded to include more universities and research institutions, and new networking technologies were developed. The development of the Transmission Control Protocol/Internet Protocol (TCP/IP) in the 1970s provided a standardized way for different networks to communicate with each other, creating a true "network of networks." The Domain Name System (DNS), introduced in 1983, made the Internet more user-friendly by allowing people to use memorable domain names instead of numerical IP addresses. The World Wide Web, invented by Tim Berners-Lee at CERN in 1989, revolutionized the Internet by introducing hyperlinks and graphical interfaces, making it accessible to a much wider audience. The release of the Mosaic web browser in 1993 sparked the commercialization of the Internet, leading to the dot-com boom of the late 1990s. While the dot-com bubble burst in 2000, the Internet continued to evolve, with the rise of social media, mobile computing, and cloud services transforming how we communicate, work, and access information. Today, the Internet is an integral part of modern society, connecting billions of people worldwide and enabling countless applications and services."""
#     splitter = EnhancedTextSplitter()
#     token_count = splitter.count_tokens(text)
#     # left_chunks , right_chunks = splitter.split_text_by_tokens(text)
#     # print(token_count)
#     # print(left_chunks)
#     # print("\n ______________________________________________________________")
#     # print(right_chunks)
#     # print("countof left chunk is ",len(left_chunks))
#     # print("countof right chunk is ",len(right_chunks))
#     chunk = splitter.split_text_by_tokens(text)
#     for i in chunk:
#         print(i)
#         print("\n ______________________________________________________________")
#     # print(chunk)

# if __name__ == "__main__":
#     main()


# from langchain.text_splitter import TextSplitter
# from langchain.schema import Document
# import tiktoken
  
# from typing import List
# import os
# from pathlib import Path
 
 


# text = """ In this chapter we discussed DBMS concepts for transaction processing. We introduced the concept of a database transaction and the operations relevant to transaction processing. We compared single-user systems to multiuser systems and then
#         presented examples of how uncontrolled execution of concurrent transactions in a
#         multiuser system can lead to incorrect results and database values.We also discussed
#         the various types of failures that may occur during transaction execution.
#         Next we introduced the typical states that a transaction passes through during execution, and discussed several concepts that are used in recovery and concurrency control methods. The system log keeps track of database accesses, and the system uses
#         this information to recover from failures. A transaction either succeeds and reaches
#         its commit point or it fails and has to be rolled back. A committed transaction has its
#         changes permanently recorded in the database. We presented an overview of the
#         desirable properties of transactions—atomicity, consistency preservation, isolation,
#         and durability—which are often referred to as the ACID properties.
#         Then we defined a schedule (or history) as an execution sequence of the operations
#         of several transactions with possible interleaving. We characterized schedules in
#         terms of their recoverability. Recoverable schedules ensure that, once a transaction
#         commits, it never needs to be undone. Cascadeless schedules add an additional condition to ensure that no aborted transaction requires the cascading abort of other
#         transactions. Strict schedules provide an even stronger condition that allows a simple recovery scheme consisting of restoring the old values of items that have been
#         changed by an aborted transaction.
        
#         We defined equivalence of schedules and saw that a serializable schedule is equivalent to some serial schedule. We defined the concepts of conflict equivalence and
#         view equivalence, which led to definitions for conflict serializability and view serializability. A serializable schedule is considered correct. We presented an algorithm
#         for testing the (conflict) serializability of a schedule. We discussed why testing for
#         serializability is impractical in a real system, although it can be used to define and
#         verify concurrency control protocols, and we briefly mentioned less restrictive definitions of schedule equivalence. Finally, we gave a brief overview of how transaction
#         concepts are used in practice within SQL.

#         Wikipedia. Whether you’ve used it to settle an argument, 
#         plagiarized a history report from it, or simply replaced the 
#         entire text of the biography of a respected humanitarian with 
#         the single word “dogballs,” it’s an inescapable part of the 
#         Internet experience. Since its launch in 2001, it has rapidly 
#         risen to become the seventh most popular website, with 
#         over 365 million readers (Source: Wikipedia). If you’re like 
#         us, when you want to know the name of the kangaroo on 
#         Shirt Tales or just want to confirm that Mother Teresa was 
#         a dogballs who helped the farts (Source: Wikipedia), The 
#         Encyclopedia That Anyone Can Edit will probably be the first 
#         place you check.

#         But here’s the thing about letting anybody edit your 
#         encyclopedia: it means that anybody can edit your 
#         encyclopedia. And while in theory this means that one day 
#         Stephen Hawking might decide to weigh in on the entry for 
#         string theory, in reality it means that somebody who deeply 
#         cares about pro wrestling is going to call someone else a 
#         Nazi when they revert his edits about Wrestlemania XI on 
#         Razor Ramon’s page.

#         And so we arrive at a cosmic intersection, where an obscure 
#         topic of dubious relevance is written about by the type of 
#         weirdo who logs on to Wikipedia to write about obscure 
#         topics of dubious relevance. Were these authors re-watching 
#         their video of Wrestlemania XI instead of completing basic 
#         8th grade English assignments? It’s very likely. Does this
#         6

#         stop them from attempting to emulate the academic tone 
#         of the great encyclopedias of the past as they describe a 
#         large mammalian species from the Star Wars universe that 
#         shares a common ancestor with the Wookies? It does not. 
#         The result? Some really terrible Wikipedia writing.
#         For the past two years, we have collected this writing on 
#         our blog, [Citation Needed].  Fascinated and delighted by 
#         the brilliantly bad writing we encountered in our Wikipedia 
#         browsing, we set out to curate The Best of Wikipedia’s Worst 
#         Writing. Starting the blog was a no-brainer; our only concern 
#         was whether, after a few months of our daily mining, the well 
#         of awful Wikipedia writing would eventually run dry. 
#         By the time you read this, we will have published our 
#         thousandth entry. We started a podcast. Instead of drying 
#         up, the ocean of ineptitude has proven far more vast than 
#         we ever could have imagined. Through our own browsing, 
#         and with the help of a dedicated group of readers who are 
#         exploring the topics they submit for God knows what reason, 
#         we’ve continually lowered and re-lowered the bar for bad 
#         Wikipedia writing.
#         Now, let’s get one thing straight: we love each and every 
#         entry written in this book. If you are one of the authors who 
#         have chosen to use your valuable time on this planet to write 
#         straight-faced exegeses on the subject of forgotten action
#         7

#         f
#         igures from the seventies, we hope you don’t take offense. 
#         And if you do, we have an acceptable retort prepared for 
#         you: “You guys ran a blog about Wikipedia for two years, 
#         who the hell are you to talk?” Feel free to use it!
#         Others may criticize us for not doing our part to help 
#         Wikipedia become “better” by revising these passages. 
#         Nothing that does not involve electrodes near our genitals 
#         would make us more miserable. In our opinion, many of the 
#         passages in this book stand alone as works of art. Think of 
#         us as photographers preserving the memory of the great 
#         street art of the world before the joyless police come and 
#         whitewash over it. (Is that an official police responsibility? It 
#         seems beneath them. If it’s not, but they’re still forced to do 
#         it, that might explain the joylessness.) The point is, if you’re 
#         moved to correct these entries, we’re powerless to stop you. 
#         They’ve already given us joy, and we’re just happy to have 
#         encountered them.

#         Enough introduction. Here are over two hundred of our 
#         favorite bad Wikipedia articles of all time. Comments in 
#         italics are ours. Everything else is a faithful reproduction of 
#         the way the entry stood at the moment we or our informants 
#         encountered it. We hope you will laugh, cry, maybe even 
#         learn something, and always remember to dogballs.
#         —Conor Lastowka & Josh Fruhlinger
#             citationneeded.tumblr.com"""

# def split_text(text):
#     sections  =  text.split("\n\n")
#     print(len(sections))
#     if len(sections) > 1:
#         chunks = []
#         current_chunk = ""
#         current_token = 0
#         for section in sections:
#             section = section.strip()
#             if not section:
#                 continue
#             encoding = tiktoken.get_encoding("cl100k_base")
#             section_tokens = len(encoding.encode(section))
            
#             if section_tokens > 150:
#                 print(section_tokens)
#                 if current_chunk and current_tokens >= 100:
#                     print("Current chunk: ", current_chunk)
#                     chunks.append(current_chunk)
#                     current_chunk = ""
#                     current_tokens = 0
#         return chunks

# if __name__ == "__main__":
#     val = split_text(text)
#     print(val)


# import asyncio
# import os
# from pathlib import Path
# from typing import Any, List, Dict, Tuple
# import uuid
# import httpx
# import numpy as np
# from sklearn.metrics.pairwise import cosine_similarity
# from langsmith import traceable
# import os
# from dotenv import load_dotenv
# load_dotenv()
# from langchain_openai import OpenAIEmbeddings

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# from langchain_openai import OpenAIEmbeddings

# # Initialize embedding model

# from utils.model_loader import get_embedding_model

# # Example chunks
# chunks = [
#     "LangChain helps build applications with LLMs.",
#     "Embeddings convert text into numerical vectors."
# ]

# # Generate embeddings
# model = asyncio.run(get_embedding_model())
# for i in chunks:
#     embeddings = model.embed_query(i)
#     print("Chunk:", i)
#     print("Embedding length:", len(embeddings))
#     print("embeddin ", embeddings)

# # Print results
# # for chunk, vector in zip(chunks, embeddings):
# #     print("Chunk:", chunk)
# #     print("Embedding length:", len(vector))
# #     print("embeddin ", vector)


import os 
import asyncio
from pinecone import Pinecone, ServerlessSpec
from utils.logging_utils import set_system_logger
from dotenv import load_dotenv
from embedding.pinecone_index import get_pinecone_index, create_pinecone_index

# load_dotenv()

# logger = set_system_logger("system_logger")

# pc = None
# _pinecone_index = None

# PINECONE_DIMENSION = 1536
# PINECONE_METRIC = "cosine"





# async def main():
#     index = await get_pinecone_index()
#     if index:
#         print("Pinecone index found")
#     else:
#         await create_pinecone_index()
#         index = await get_pinecone_index()
#         print("Pinecone index not found")
#     print(index)

# if __name__ == "__main__":
#     asyncio.run(main())




async def get_reranker_clinet(docs):
    import cohere
    co = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))
    return co.rerank(
        model="rerank-v4.0-pro",
        query="What is the capital of the United States?",
        documents=docs, 
        top_n=3,
        return_documents=True,  
    )

if __name__ == "__main__":
    docs = ["hi", "hello" , "capital of india is new delhi" , "capital of usa is new york"]
    result = asyncio.run(get_reranker_clinet(docs))
    print(result)
