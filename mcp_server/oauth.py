"""
OAuth 2.1 + PKCE Authentication for MCP Connector.
Wraps the existing cookie/JWT auth system with an OAuth layer that Claude can use.
"""
import os
import secrets
import hashlib
import base64
import time
import json
from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Depends, Form, Query
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel

from utils.auth_utils import auth_manger
from db.config import Database
from utils.logging_utils import set_system_logger

logger = set_system_logger("mcp_oauth_logger")

oauth_router = APIRouter()

# ─── In-memory stores (replace with Redis/DB in production for multi-worker) ──
# These store OAuth artifacts: authorization codes, tokens, PKCE challenges
_authorization_codes: dict = {}   # code -> {user_id, redirect_uri, code_challenge, expires_at}
_access_tokens: dict = {}         # token -> {user_id, username, email, role, expires_at}
_refresh_tokens: dict = {}        # refresh_token -> {user_id, access_token, expires_at}

# ─── Configuration ──────────────────────────────────────────────────────────────
CLIENT_ID = os.getenv("MCP_OAUTH_CLIENT_ID", "recai-mcp-connector")
ALLOWED_CLIENT_IDS = {CLIENT_ID, "claude", "claude-ai", "mcp-inspector"}
# For public clients (Claude), client_secret is NOT used with PKCE
AUTHORIZATION_CODE_EXPIRY = 600      # 10 minutes
ACCESS_TOKEN_EXPIRY = 3600           # 1 hour
REFRESH_TOKEN_EXPIRY = 86400 * 30    # 30 days

ALLOWED_REDIRECT_URIS = [
    "https://claude.ai/api/mcp/auth_callback",
    "http://localhost:3000/callback",    # local testing
    "http://127.0.0.1:3000/callback",   # local testing
    "http://localhost:8000/callback",   # backend local testing
    "http://localhost:5173/callback",   # frontend local testing
    "https://modelcontextprotocol.io/inspector", # official MCP Inspector
]
extra_uris = os.getenv("MCP_ALLOWED_REDIRECT_URIS", "")
if extra_uris:
    ALLOWED_REDIRECT_URIS.extend([u.strip() for u in extra_uris.split(",") if u.strip()])

# Load existing auth manager to validate user credentials
secret_key = os.getenv("secret_key", "")


def _generate_token(length: int = 64) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def _verify_pkce(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """Verify PKCE code_verifier against stored code_challenge."""
    if method == "S256":
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        computed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return computed_challenge == code_challenge
    elif method == "plain":
        return code_verifier == code_challenge
    return False


def _cleanup_expired():
    """Remove expired authorization codes and tokens."""
    now = time.time()
    expired_codes = [k for k, v in _authorization_codes.items() if v["expires_at"] < now]
    for k in expired_codes:
        del _authorization_codes[k]
    expired_tokens = [k for k, v in _access_tokens.items() if v["expires_at"] < now]
    for k in expired_tokens:
        del _access_tokens[k]
    expired_refresh = [k for k, v in _refresh_tokens.items() if v["expires_at"] < now]
    for k in expired_refresh:
        del _refresh_tokens[k]


# ─── OAuth Discovery Endpoint ───────────────────────────────────────────────────
@oauth_router.get("/.well-known/oauth-authorization-server")
async def oauth_discovery(request: Request):
    """OAuth 2.1 Authorization Server Metadata (RFC 8414)."""
    base_url = str(request.base_url).rstrip("/")
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],  # public client
    }


# ─── Authorization Endpoint ─────────────────────────────────────────────────────
@oauth_router.get("/authorize")
async def authorize(
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    state: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query("S256"),
    scope: str = Query(""),
):
    """
    OAuth 2.1 Authorization Endpoint.
    Shows a login form. On successful login, redirects with an authorization code.
    """
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Only response_type=code is supported")
    
    if client_id not in ALLOWED_CLIENT_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown client_id: {client_id}")
    
    if redirect_uri not in ALLOWED_REDIRECT_URIS:
        raise HTTPException(status_code=400, detail=f"Invalid redirect_uri: {redirect_uri}")
    
    if code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="Only S256 code_challenge_method is supported")

    # Render a simple login form that POSTs to /oauth/login
    login_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RecAI — Authorize Claude Connector</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #e0e0e0;
            }}
            .card {{
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                padding: 40px;
                width: 100%;
                max-width: 420px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }}
            h2 {{ text-align: center; margin-bottom: 8px; font-size: 24px; color: #fff; }}
            .subtitle {{ text-align: center; margin-bottom: 28px; font-size: 14px; color: #999; }}
            label {{ display: block; margin-bottom: 6px; font-size: 14px; color: #bbb; }}
            input {{
                width: 100%;
                padding: 12px 16px;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px;
                background: rgba(255,255,255,0.08);
                color: #fff;
                font-size: 15px;
                margin-bottom: 20px;
                outline: none;
                transition: border 0.2s;
            }}
            input:focus {{ border-color: #7c5cfc; }}
            button {{
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #7c5cfc, #5a3fd4);
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: opacity 0.2s;
            }}
            button:hover {{ opacity: 0.9; }}
            .error {{ color: #ff6b6b; text-align: center; margin-bottom: 16px; font-size: 14px; }}
            .info {{ text-align: center; margin-top: 16px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>RecAI</h2>
            <p class="subtitle">Authorize Claude to connect to your account</p>
            <form method="POST" action="/oauth/login">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}" />
                <input type="hidden" name="state" value="{state}" />
                <input type="hidden" name="code_challenge" value="{code_challenge}" />
                <input type="hidden" name="code_challenge_method" value="{code_challenge_method}" />
                <label for="email">Email</label>
                <input type="email" id="email" name="email" required placeholder="you@company.com" />
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required placeholder="Your password" />
                <button type="submit">Authorize</button>
            </form>
            <p class="info">By authorizing, Claude will be able to search resumes and retrieve screening reports on your behalf.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=login_html)


@oauth_router.post("/login")
async def oauth_login(
    email: str = Form(...),
    password: str = Form(...),
    redirect_uri: str = Form(...),
    state: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form("S256"),
):
    """
    Handle the login form submission.
    On success, redirect to the redirect_uri with an authorization code.
    """
    _cleanup_expired()
    
    # Authenticate using existing DB function
    from db.endpoints.auth import authenticate_user
    user_data = await authenticate_user(email, password)
    
    if user_data is None:
        logger.warning(f"OAuth login failed for email: {email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Generate authorization code
    auth_code = _generate_token(32)
    _authorization_codes[auth_code] = {
        "user_id": user_data["user_id"],
        "username": user_data["username"],
        "email": user_data["email"],
        "role": user_data["role"],
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "expires_at": time.time() + AUTHORIZATION_CODE_EXPIRY,
    }
    
    logger.info(f"OAuth authorization code issued for user: {email}")
    
    # Redirect back to Claude with the code
    redirect_url = f"{redirect_uri}?code={auth_code}&state={state}"
    return RedirectResponse(url=redirect_url, status_code=302)


# ─── Token Endpoint ──────────────────────────────────────────────────────────────
@oauth_router.post("/token")
async def token_exchange(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
):
    """
    OAuth 2.1 Token Endpoint.
    Supports grant_type=authorization_code (with PKCE) and grant_type=refresh_token.
    """
    _cleanup_expired()
    
    if grant_type == "authorization_code":
        return await _handle_authorization_code_grant(code, redirect_uri, code_verifier)
    elif grant_type == "refresh_token":
        return await _handle_refresh_token_grant(refresh_token)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {grant_type}")


async def _handle_authorization_code_grant(
    code: Optional[str], redirect_uri: Optional[str], code_verifier: Optional[str]
):
    """Exchange authorization code + PKCE verifier for tokens."""
    if not code or not code_verifier:
        raise HTTPException(status_code=400, detail="code and code_verifier are required")
    
    stored = _authorization_codes.pop(code, None)
    if stored is None:
        raise HTTPException(status_code=400, detail="Invalid or expired authorization code")
    
    if stored["expires_at"] < time.time():
        raise HTTPException(status_code=400, detail="Authorization code has expired")
    
    if redirect_uri and stored["redirect_uri"] != redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri mismatch")
    
    # Verify PKCE
    if not _verify_pkce(code_verifier, stored["code_challenge"], stored["code_challenge_method"]):
        logger.warning(f"PKCE verification failed for user: {stored['email']}")
        raise HTTPException(status_code=400, detail="PKCE verification failed")
    
    # Issue tokens
    access_token = _generate_token(48)
    refresh_tok = _generate_token(48)
    now = time.time()
    
    token_data = {
        "user_id": stored["user_id"],
        "username": stored["username"],
        "email": stored["email"],
        "role": stored["role"],
        "expires_at": now + ACCESS_TOKEN_EXPIRY,
    }
    
    _access_tokens[access_token] = token_data
    _refresh_tokens[refresh_tok] = {
        "user_id": stored["user_id"],
        "access_token": access_token,
        "expires_at": now + REFRESH_TOKEN_EXPIRY,
    }
    
    logger.info(f"OAuth tokens issued for user: {stored['email']}")
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_EXPIRY,
        "refresh_token": refresh_tok,
    }


async def _handle_refresh_token_grant(refresh_token: Optional[str]):
    """Exchange a refresh token for a new access token."""
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token is required")
    
    stored = _refresh_tokens.get(refresh_token)
    if stored is None or stored["expires_at"] < time.time():
        # Clean up expired
        _refresh_tokens.pop(refresh_token, None)
        raise HTTPException(status_code=400, detail="Invalid or expired refresh token")
    
    # Revoke old access token
    old_access = stored.get("access_token")
    if old_access:
        _access_tokens.pop(old_access, None)
    
    # Issue new access token
    new_access_token = _generate_token(48)
    user_id = stored["user_id"]
    
    # Fetch user info from DB
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, username, email, user_role FROM core.users WHERE user_id = $1 AND is_active = true",
            __import__("uuid").UUID(user_id)
        )
    
    if not row:
        _refresh_tokens.pop(refresh_token, None)
        raise HTTPException(status_code=401, detail="User account is no longer active")
    
    now = time.time()
    _access_tokens[new_access_token] = {
        "user_id": str(row["user_id"]),
        "username": row["username"],
        "email": row["email"],
        "role": row["user_role"],
        "expires_at": now + ACCESS_TOKEN_EXPIRY,
    }
    
    # Update refresh token to point to new access token
    stored["access_token"] = new_access_token
    
    return {
        "access_token": new_access_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_EXPIRY,
        "refresh_token": refresh_token,  # same refresh token
    }


# ─── Token Validation (used by MCP tools) ────────────────────────────────────────
async def validate_oauth_token(request: Request) -> dict:
    """
    Validate authorization for MCP requests:
    1. Checks OAuth 2.1 Bearer token from header.
    2. Fallback to existing system JWT from Authorization header or cookie.
    3. Fallback to dev test token if enabled.
    Returns user data dict or raises 401.
    """
    _cleanup_expired()
    token = None
    auth_header = request.headers.get("Authorization", "")
    
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif request.cookies.get("auth_token"):
        token = request.cookies.get("auth_token")

    # Developer API key override for local testing
    dev_key = os.getenv("MCP_DEV_API_KEY", "")
    api_key_header = request.headers.get("X-API-Key", "")
    if dev_key and (token == dev_key or api_key_header == dev_key):
        return {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "username": "developer",
            "email": "dev@estuate.com",
            "role": "admin",
            "authenticated": True,
        }

    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization header or cookie")

    # 1. Check OAuth in-memory access tokens
    token_data = _access_tokens.get(token)
    if token_data:
        if token_data["expires_at"] < time.time():
            _access_tokens.pop(token, None)
            raise HTTPException(status_code=401, detail="Access token has expired")
        return {
            "user_id": token_data["user_id"],
            "username": token_data["username"],
            "email": token_data["email"],
            "role": token_data["role"],
            "authenticated": True,
        }

    # 2. Fallback to validating existing JWT auth token
    try:
        auth_mgr = auth_manger(secret_key=secret_key)
        user_jwt = auth_mgr.validate_authtoken(token)
        if user_jwt:
            return {
                "user_id": str(user_jwt.get("user_id")),
                "username": user_jwt.get("username", "user"),
                "email": user_jwt.get("email", ""),
                "role": user_jwt.get("role", "user"),
                "authenticated": True,
            }
    except Exception as e:
        logger.debug(f"JWT validation fallback failed: {e}")

    raise HTTPException(status_code=401, detail="Invalid or expired access token")
