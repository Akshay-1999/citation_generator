"""
Security Layer for MCP Connector:
1. Rate limiting (sliding window per user/client).
2. Input sanitization and prompt injection guard.
"""
import time
import re
from typing import Dict, List, Tuple
from fastapi import HTTPException, Request
from utils.logging_utils import set_system_logger

logger = set_system_logger("mcp_security_logger")


class RateLimiter:
    """In-memory sliding window rate limiter."""
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[str, List[float]] = {}

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Clean older entries
        timestamps = self._history.get(client_id, [])
        valid_timestamps = [t for t in timestamps if t > cutoff]
        
        if len(valid_timestamps) >= self.max_requests:
            retry_after = int(valid_timestamps[0] - cutoff) + 1
            self._history[client_id] = valid_timestamps
            return False, retry_after
        
        valid_timestamps.append(now)
        self._history[client_id] = valid_timestamps
        return True, 0

    def check_request(self, client_id: str):
        allowed, retry_after = self.is_allowed(client_id)
        if not allowed:
            logger.warning(f"Rate limit exceeded for client {client_id}. Retry after {retry_after}s")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Please wait {retry_after} seconds before retrying.",
                headers={"Retry-After": str(retry_after)}
            )


# Global rate limiter instance
mcp_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)


class PromptInjectionGuard:
    """Sanitizes text and guards against prompt injection / jailbreak attempts."""
    
    # Common prompt injection patterns
    SUSPICIOUS_PATTERNS = [
        r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|directions)\b",
        r"(?i)\bdisregard\s+(all\s+)?(previous|prior|system)\b",
        r"(?i)\byou\s+are\s+now\s+(in\s+)?(developer\s+mode|unrestricted|DAN|jailbroken)\b",
        r"(?i)\breveal\s+(the\s+)?(system\s+prompt|hidden\s+prompt|developer\s+prompt|secret\s+key|api\s+key)\b",
        r"(?i)\boutput\s+the\s+(entire\s+)?system\s+prompt\b",
        r"(?i)\[system\s*:\s*.*\]",
        r"(?i)<\s*system\s*>.*<\s*/system\s*>",
        r"(?i)\badmin\s+override\s+code\b",
    ]

    MAX_QUERY_LENGTH = 2000
    MAX_JD_LENGTH = 50000

    @classmethod
    def sanitize_text(cls, text: str, max_length: int = 5000) -> str:
        if not text:
            return ""
        # Strip null bytes and non-printable control characters (except common newlines/tabs)
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        cleaned = cleaned.strip()
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        return cleaned

    @classmethod
    def inspect_query(cls, query: str) -> str:
        """Inspect and sanitize search query. Raises HTTPException on malicious input."""
        cleaned = cls.sanitize_text(query, max_length=cls.MAX_QUERY_LENGTH)
        if not cleaned:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, cleaned):
                logger.warning(f"Potential prompt injection detected in query: {cleaned[:100]}")
                raise HTTPException(
                    status_code=400,
                    detail="Query contains disallowed instructions or injection patterns."
                )
        return cleaned

    @classmethod
    def inspect_job_description(cls, jd_text: str) -> str:
        """Inspect and sanitize Job Description text."""
        cleaned = cls.sanitize_text(jd_text, max_length=cls.MAX_JD_LENGTH)
        if not cleaned:
            raise HTTPException(status_code=400, detail="Job description cannot be empty")
        
        # Soft check on JD: sanitize suspicious tags if present
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, cleaned):
                logger.warning(f"Suspicious instruction detected in job description: {cleaned[:100]}")
                # Neutralize rather than outright block since recruiters might paste messy JDs
                cleaned = re.sub(pattern, "[removed instruction]", cleaned)
        return cleaned
