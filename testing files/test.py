from langchain.text_splitter import TextSplitter
from langchain.schema import Document
import tiktoken
from typing import List
from document_processing.document_loader import MemoryEfficientFileloader
import asyncio
from pathlib import Path
from utils.logging_utils import set_system_logger
logger = set_system_logger("system_logger")

CJK_WORD_BREAKS = [
    "、", "，", "；", "：", "（", "）", "【", "】", "「", "」", "『", "』", "〔", "〕",
    "〈", "〉", "《", "》", "〖", "〗", " আটকে", "〙", "〚", "〛", "〝", "〞", "〟", "〰",
    "–", "—", "'", "'", "‚", "‛", """, """, "„", "‟", "‹", "›"
]
CJK_SENTENCE_ENDINGS = ["。", "！", "？", "‼", "⁇", "⁈", "⁉"]
STANDARD_SENTENCE_ENDINGS = [".", "!", "?"]
STANDARD_WORD_BREAKS = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]


class EnhancedTextSplitter(TextSplitter):
    def __init__(self, chunk_size=1000, chunk_overlap=None, model_name="text-embedding-3-large",
                 max_tokens_per_section=1000, overlap_percent=15, sentence_search_limit=150):
        if chunk_overlap is None:
            chunk_overlap = int(chunk_size * overlap_percent / 100)
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.max_tokens = max_tokens_per_section
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.overlap_percent = overlap_percent
        self.sentence_endings = STANDARD_SENTENCE_ENDINGS + CJK_SENTENCE_ENDINGS
        self.word_breaks = STANDARD_WORD_BREAKS + CJK_WORD_BREAKS
        self.sentence_search_limit = sentence_search_limit
        # Add minimum token count to prevent tiny chunks
        self.min_tokens = max(50, int(self.max_tokens * 0.1))

    def count_tokens(self , text):
        return len(self.encoding.encode(text))

    def split_text_by_tokens(self, text: str, depth: int = 0) -> List[str]:
        """
        Fixed version with recursion depth limit and better error handling.
        """
        # Prevent infinite recursion
        if depth > 10:
            logger.warning(f"Max recursion depth reached, force splitting text of length {len(text)}")
            # Force split in the middle as last resort
            mid = len(text) // 2
            return [text[:mid], text[mid:]]
        
        tokens = self.encoding.encode(text)
        if len(tokens) <= self.max_tokens:
            return [text]

        # Find optimal split point
        start = len(text) // 2
        pos = 0
        split_position = -1
        max_range = min(self.sentence_search_limit, len(text) // 2)

        # Search for sentence endings
        while pos < max_range:
            left = start - pos
            right = start + pos

            if left >= 0 and left < len(text) and text[left] in self.sentence_endings:
                split_position = left + 1  # Include the sentence ending
                break
            if right < len(text) and text[right] in self.sentence_endings:
                split_position = right + 1  # Include the sentence ending
                break
            pos += 1

        if split_position > 0 and split_position < len(text):
            first_half = text[:split_position].strip()
            second_half = text[split_position:].strip()
            
            # Ensure both halves are meaningful
            if len(first_half) < 10 or len(second_half) < 10:
                # Fall back to middle split with overlap
                middle = len(text) // 2
                overlap = int(len(text) * (self.overlap_percent / 100))
                first_half = text[:middle + overlap]
                second_half = text[middle - overlap:]
        else:
            # No good sentence boundary found, use middle split with overlap
            middle = len(text) // 2
            overlap = int(len(text) * (self.overlap_percent / 100))
            first_half = text[:middle + overlap]
            second_half = text[middle - overlap:]

        # Recursively split both halves
        left_chunks = self.split_text_by_tokens(first_half, depth + 1) if first_half.strip() else []
        right_chunks = self.split_text_by_tokens(second_half, depth + 1) if second_half.strip() else []
        
        return left_chunks + right_chunks

    def split_text(self, text : str )->List[str]:
        if not text:
            return []
        
        if self.count_tokens(text) <= self.max_tokens:
            return [text]

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []

        if self.count_tokens(text) <= self.max_tokens:
            return [text]

        # Try paragraph-based splitting first
        sections = text.split("\n\n")
        if len(sections) > 1:
            chunks = []
            current_chunk = ""
            current_tokens = 0

            for section in sections:
                section = section.strip()
                if not section:
                    continue
                    
                section_tokens = self.count_tokens(section)

                # If single section is too large, split it
                if section_tokens > self.max_tokens:
                    # Save current chunk first
                    if current_chunk and current_tokens >= self.min_tokens:
                        chunks.append(current_chunk)
                        current_chunk = ""
                        current_tokens = 0

                    # Split the large section
                    subsections = self.split_text_by_tokens(section)
                    for subsection in subsections:
                        if subsection.strip() and self.count_tokens(subsection) >= self.min_tokens:
                            chunks.append(subsection)
                    continue

                # Check if adding this section would exceed limits
                new_total = current_tokens + section_tokens + (2 if current_chunk else 0)  # +2 for \n\n
                
                if new_total > self.max_tokens and current_chunk:
                    # Save current chunk and start new one
                    chunks.append(current_chunk)
                    current_chunk = section
                    current_tokens = section_tokens
                else:
                    # Add to current chunk
                    if current_chunk:
                        current_chunk += "\n\n" + section
                        current_tokens = new_total
                    else:
                        current_chunk = section
                        current_tokens = section_tokens

            # Add final chunk
            if current_chunk and current_tokens >= self.min_tokens:
                chunks.append(current_chunk)

            # Filter out chunks that are too small
            valid_chunks = [chunk for chunk in chunks if self.count_tokens(chunk) >= self.min_tokens]
            if valid_chunks:
                return valid_chunks

        # Fall back to token-based splitting
        chunks = self.split_text_by_tokens(text)
        return [chunk for chunk in chunks if chunk.strip() and self.count_tokens(chunk) >= self.min_tokens]

class EnhancedMarkdownSplitter(EnhancedTextSplitter):
    def __init__(self, chunk_size=1000, chunk_overlap=None, model_name="text-embedding-3-large",
                 max_tokens_per_section=1000, overlap_percent=15):
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap,
                         model_name=model_name, max_tokens_per_section=max_tokens_per_section,
                         overlap_percent=overlap_percent)
        self.md_breakpoints = [  
            "\n# ",      # H1 - highest priority
            "\n## ",     # H2
            "\n### ",    # H3
            "\n#### ",   # H4
            "\n##### ", # H5
            "\n\n",     # Paragraph break
            "\n- ",     # Unordered list
            "\n* ",     # Unordered list alt
            "\n1. ",    # Ordered list
        ]

    def find_md_breakpoint(self, text: str, start: int, end: int) -> int:
        # Search for markdown breakpoints in priority order
        for bp in self.md_breakpoints:
            idx = text.rfind(bp, start, end)
            if idx != -1 and idx > start + 20:  # Ensure minimum chunk size
                return idx + len(bp)

        # Fall back to sentence endings
        for i in range(end - 1, start + 20, -1):  # Ensure minimum chunk size
            if i < len(text) and text[i] in self.sentence_endings:
                return i + 1

        # Fall back to word breaks 
        for i in range(end - 1, start + 20, -1):  # Ensure minimum chunk size
            if i < len(text) and text[i] in self.word_breaks:
                return i + 1

        return end

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []

        tokens = self.encoding.encode(text)
        if len(tokens) <= self.max_tokens:
            return [text]

        chunks = []
        start_char = 0

        while start_char < len(text):
            remaining_text = text[start_char:]
            tokens_remaining = self.encoding.encode(remaining_text)
            num_tokens = len(tokens_remaining)

            if num_tokens <= self.max_tokens:
                if remaining_text.strip():  # Only add non-empty chunks
                    chunks.append(remaining_text)
                break

            # Estimate character position for max tokens (with safety margin)
            approx_char_per_token = len(remaining_text) / num_tokens
            approx_char_limit = int(self.max_tokens * approx_char_per_token * 0.9)  # 10% safety margin
            end_char = min(start_char + approx_char_limit, len(text))

            # Find optimal breakpoint
            break_idx = self.find_md_breakpoint(text, start_char, end_char)
            chunk_text = text[start_char:break_idx]
            
            # Verify token count and adjust if necessary
            chunk_tokens = self.count_tokens(chunk_text)    
            if chunk_tokens > self.max_tokens:
                # Binary search for acceptable position
                left, right = start_char + 50, break_idx  # Minimum 50 chars
                while left < right:
                    mid = (left + right + 1) // 2
                    test_chunk = text[start_char:mid]
                    if self.count_tokens(test_chunk) <= self.max_tokens:
                        left = mid
                    else:
                        right = mid - 1
                break_idx = left
                chunk_text = text[start_char:break_idx]

            # Only add chunks that meet minimum requirements
            if chunk_text.strip() and self.count_tokens(chunk_text) >= self.min_tokens:
                chunks.append(chunk_text)

            # Calculate next start position with overlap - FIXED BUG
            overlap_chars = int(len(chunk_text) * self.overlap_percent / 100)
            start_char = max(break_idx - overlap_chars, start_char + 1)  # Ensure progress
            
            # Safety check to prevent infinite loop
            if break_idx <= start_char:
                logger.warning("No forward progress in markdown splitter; forcing advancement")
                break_idx = start_char + 50  # or a minimum step size

            start_char = break_idx

        return chunks



from document_processing.textsplitter import split_documents
from embedding.embedder import process_embedding_batch
from embedding.embedder import store_embeddings
 
async def main(files_to_process , user_id):
    # file_path = r"D:\Akshay\Work and Document\Training\LLM AND AI\citation\citation_generator\uploaded_files\DOC-20251220-WA0001.pdf"
    # file_loader = MemoryEfficientFileloader(file_path)
    # supported_files = [f for f in files_to_process]
    # intermediate_chunk = []
    # async for docs in file_loader.load(specific_files  = supported_files , user_id="ac68c8ac-0c3d-458c-bd2e-b707c278f7f1"):
    #     intermediate_chunk.append(docs)

    # intermediate_chunk.sort(key=lambda x: x.metadata.get("chunk_index",0))

    # text_splitter = EnhancedTextSplitter()
    
    # final_chunks = []
    # for file_data in intermediate_chunk:
    #     chunk_metadata = file_data.metadata
    #     chunk_content = file_data.page_content
        
    #     split_content = text_splitter.split_text(chunk_content)
    #     for i, content in enumerate(split_content):
    #         final_chunks.append(Document(
    #             page_content=content,
    #             metadata={
    #                 **chunk_metadata,
    #                 "chunk_index": chunk_metadata.get("chunk_index", 0) * len(split_content) + i
    #             }
    #         ))
    
    # for chunk in final_chunks:
    #     print(chunk)
    #     print("\n")
    # Val = await split_documents(files_to_process, user_id=user_id)
    # batch_size = 150
    # total_chunk = len(Val)
    # batches = [(Val[i:i + batch_size], i // batch_size)
    #                 for i in range(0, total_chunk, batch_size)]
        
    # embedding_task = [asyncio.create_task(process_embedding_batch(batch_chunk , file_path , batch_index)) for batch_chunk, batch_index in batches]
    
    # batch_result = {}

    # for i in range(0, len(embedding_task) , 4):
    #     batch_group  = embedding_task[i:i+4]
    #     group_result = await asyncio.gather(*batch_group)
    #     for idx,embedding,batch_chunk in group_result:
    #         batch_result[idx] = (embedding,batch_chunk)        

    # return batch_result
    val = await store_embeddings(files_to_process , user_id=user_id)
    return val



if __name__ == "__main__":
    file_path = [r'D:\Akshay\Work and Document\Training\LLM AND AI\citation\citation_generator\uploaded_files\c2d-vendor-guidance.pdf']

    chunks_metadata = asyncio.run(main(files_to_process = file_path ,  user_id="ac68c8ac-0c3d-458c-bd2e-b707c278f7f1" ))
    for file_name, success in chunks_metadata.items():
        status = "successful" if success else "failed"
        print(f"File {file_name}: Processing {status}")
        

    

    # for i in range(0, total_chunk, batch_size):
    #     print(chunks[i:i + batch_size])