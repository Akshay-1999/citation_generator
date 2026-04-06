from langchain.text_splitter import TextSplitter
from langchain.schema import Document
import tiktoken
from utils.logging_utils import set_system_logger
from typing import List , Optional
import os
from pathlib import Path
from document_processing.document_loader import MemoryEfficientFileloader
logger = set_system_logger("system_logger")

# Character sets for intelligent text splitting
CJK_WORD_BREAKS = [
    "、", "，", "；", "：", "（", "）", "【", "】", "「", "」", "『", "』", "〔", "〕",
    "〈", "〉", "《", "》", "〖", "〗", "〘", "〙", "〚", "〛", "〝", "〞", "〟", "〰",
    "–", "—", "'", "'", "‚", "‛", "\"", "\"", "„", "‟", "‹", "›"
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

    def count_tokens(self, text: str) -> int:
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"=== Tokenization failed: {e} ===")
            return 0


    def split_text_by_tokens(self, text: str, depth: int = 0) -> List[str]:
        """
        Fixed version with recursion depth limit and better error handling.
        """
        # Prevent infinite recursion
        if depth > 10:
            logger.warning(f"=== Max recursion depth reached, force splitting text of length {len(text)} ===")
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
                logger.warning("=== No forward progress in markdown splitter; forcing advancement ===")
                break_idx = start_char + 50  # or a minimum step size

            start_char = break_idx

        return chunks

async def split_documents(files_to_process : List[str] , user_id : str = None , file_name: Optional[str] = None):
    logger.info(f"=== Starting document processing for user {user_id} with documents: {files_to_process} ===")
    loader = MemoryEfficientFileloader()
    
    if not files_to_process:
        logger.info("--- No files to process or splitting ---")
        return []
    
    supported_files = [f for f in files_to_process if Path(f).suffix.lower() in loader.loader_mapping]

    if not supported_files:
        logger.info("--- No supported files to process or splitting in the given files ---")
        return []

    logger.info(f"=== Started data extraction for user {user_id} with documents: {supported_files} ===")
    intermediate_chunks = [] 
    async for doc in loader.load(specific_files=supported_files , user_id=user_id ):
        intermediate_chunks.append(doc)
    logger.info(f"=== Completed data extraction for user {user_id} with documents: {supported_files} ===")
    
    intermediate_chunks.sort(key=lambda x: x.metadata.get("chunk_index", 0))

    all_final_chunks = []
    for file_data in intermediate_chunks:
        full_text = file_data.page_content
        file_metadata = file_data.metadata

        if not full_text.strip():
            logger.warning(f"=== Empty text content for file {file_metadata.get('file_name') or file_metadata.get('chunk_index' , -1)} ===")
            continue
        
        is_markdown = file_metadata.get("content_format") == "markdown"
        splitter_cls = EnhancedMarkdownSplitter if is_markdown else EnhancedTextSplitter
        splitter = splitter_cls()

        final_chunks_from_block = splitter.split_text(full_text)
        for chunk_text in final_chunks_from_block:
            document = Document(page_content=chunk_text, metadata={**file_metadata})
            all_final_chunks.append(document)
    
    total_chunks = len(all_final_chunks)
    logger.info(f"=== Completed document processing for user {user_id} - Total chunks: {total_chunks} ===")
    for i , chunk_doc in enumerate(all_final_chunks):
        chunk_doc.metadata.update({"chunk_index": i,
        "total_chunks": total_chunks})
    
    logger.info(f"=== Completed document splitting for user {user_id} - Total chunks: {total_chunks} ===")
    
    return all_final_chunks