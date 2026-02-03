# Security Analysis Report - Citation Generator Application

## Executive Summary
The application has **moderate security concerns** with some good practices in place (password hashing, role-based access control, logging) but also several critical vulnerabilities that need immediate attention.

---

## 🔴 CRITICAL ISSUES

### 1. **Hardcoded JWT Secret Key** ⚠️ CRITICAL
**Location:** `utils/auth_utils.py:16`
```python
SECRET_KEY = uuid.uuid4().hex  # Generated every time module loads!
```
**Issue:** 
- Secret key is regenerated on every module import, invalidating all existing tokens
- Should be stored in environment variables
- Changes break authentication for all users

**Impact:** High - Authentication/Authorization bypass
**Fix:**
```python
from dotenv import load_dotenv
import os

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY not found in environment variables")
```

---

### 2. **CORS Misconfiguration - Allow All Origins** ⚠️ CRITICAL
**Location:** `app.py:15-20`
```python
app.add_middleware(CORSMiddleware,
    allow_origins=["*"],  # ❌ Allows requests from ANY domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
**Issue:**
- `allow_origins=["*"]` with `allow_credentials=True` enables CSRF attacks
- Exposes API to cross-site request forgery
- Any website can make authenticated requests on behalf of users

**Impact:** High - Cross-Site Request Forgery (CSRF)
**Fix:**
```python
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Explicit methods
    allow_headers=["Authorization", "Content-Type"],  # Explicit headers
)
```

---

### 3. **No Rate Limiting** ⚠️ CRITICAL
**Issue:** No rate limiting on authentication endpoints
- Brute force attacks on login are possible
- No protection against credential stuffing
- No DDoS mitigation

**Impact:** High - Brute force attacks
**Fix:** Add rate limiting middleware
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@authrouter.post("/token")
@limiter.limit("5/minute")  # 5 requests per minute
async def login_for_access_token(...):
    ...
```

---

### 4. **Plain Text Error Messages Expose System Details** ⚠️ HIGH
**Location:** Multiple endpoints
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))  # ❌ Exposes internals
```
**Issue:**
- Stack traces and database errors exposed to clients
- Information disclosure vulnerability
- Helps attackers understand system architecture

**Impact:** High - Information disclosure
**Fix:**
```python
except Exception as e:
    logger.error(f"Error details: {e}", exc_info=True)  # Log internally
    raise HTTPException(status_code=500, detail="An error occurred. Please try again.")
```

---

### 5. **Weak Password Validation** ⚠️ HIGH
**Location:** `db/userendpoint.py:18`
```python
class User(BaseModel):
    password: str = Field(..., example="strongpassword123")
```
**Issue:**
- No password complexity requirements
- No minimum length enforced
- No validation of password strength
- Users can set simple passwords like "123" or "password"

**Impact:** High - Weak passwords
**Fix:**
```python
from pydantic import field_validator

class User(BaseModel):
    password: str = Field(..., min_length=12, example="StrongP@ssw0rd!")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain special character')
        return v
```

---

## 🟠 HIGH PRIORITY ISSUES

### 6. **Missing HTTPS/TLS Enforcement**
**Issue:**
- No enforcement of HTTPS in production
- Credentials transmitted in plain text over HTTP
- Session tokens vulnerable to interception

**Impact:** High - Man-in-the-Middle (MITM) attacks
**Fix:**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com"])

# In production, configure HTTPS:
# uvicorn app:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

---

### 7. **No Request Body Size Limits**
**Location:** `routes/file.py` - File upload endpoint
**Issue:**
- Users can upload unlimited file sizes
- Leads to DoS attacks and storage exhaustion
- No file type validation visible

**Impact:** High - Denial of Service
**Fix:**
```python
from fastapi import File, UploadFile, HTTPException

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@file_router.post("/upload_file")
async def upload_file(file: UploadFile = File(...)):
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    
    # Validate file type
    allowed_types = {"application/pdf", "text/plain", "application/json"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")
```

---

### 8. **Incomplete Input Validation**
**Location:** `utils/auth_utils.py:64`
```python
async def get_user_details(token: str = Depends(oauth2scheme)):
    # No token length validation
    # No token format validation
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```
**Issue:**
- No validation of token format before decoding
- Could lead to exception handling issues
- No protection against malformed tokens

**Fix:**
```python
import re

async def get_user_details(token: str = Depends(oauth2scheme)):
    if not token or len(token) > 4096:  # Reasonable token size limit
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Validate JWT structure (3 parts separated by dots)
    if token.count('.') != 2:
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception
```

---

### 9. **SQL Injection Risk in Parameterized Queries - But Verify All**
**Location:** Database queries (partially reviewed)
**Good:** Using parameterized queries (`$1`, `$2` syntax)
**Issue:** Some queries may not be fully parameterized
```python
# Good:
await connection.fetchrow("SELECT * FROM core.users WHERE email = $1", email)

# Need to verify ALL database interactions use this pattern
```

---

### 10. **No Logging of Security Events**
**Location:** Throughout the application
**Issue:**
- Some error logs don't include timestamp context
- No audit trail for sensitive operations
- Failed login attempts could be missed

**Improvement:** Already good, but enhance with:
```python
# Add structured logging for security events
logger.warning(f"Failed login attempt from IP: {request.client.host} for email: {email}")
logger.warning(f"Unauthorized access attempt by user {user_id} to resource {resource}")
logger.info(f"Admin action: User {admin_id} deleted user {target_user_id}")
```

---

## 🟡 MEDIUM PRIORITY ISSUES

### 11. **Token Not Rotated / No Token Refresh**
**Location:** `utils/auth_utils.py:30`
```python
ACCESS_TOKEN_EXPIRE_MINUTES = 30
```
**Issue:**
- No refresh token mechanism
- Users forced to re-login after token expires
- No way to revoke tokens (stateless JWT)

**Fix:**
```python
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_tokens(data: dict):
    access_token = create_access_token(data, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_refresh_token(data, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    return {"access_token": access_token, "refresh_token": refresh_token}

@authrouter.post("/refresh")
async def refresh_token(refresh_token: str):
    # Validate and refresh
    ...
```

---

### 12. **Incomplete File Upload Endpoint**
**Location:** `routes/file.py` and `db/endpoints/files.py`
**Issue:**
- Endpoint is incomplete/unfinished
- No file validation
- No antivirus scanning
- No file storage location validation

---

### 13. **No Password Change Confirmation**
**Location:** `db/userendpoint.py:63`
```python
async def update_user_password(email: str, new_password: str):
    # No confirmation required
    # No old password verification
```
**Issue:**
- Anyone with a valid token can change another user's password
- No verification of identity

**Fix:**
```python
@userrouter.put("/update_password/{email}")
async def update_password(
    email: EmailStr, 
    old_password: str,  # Add old password requirement
    new_password: str,
    user_details = Depends(get_user_details)
):
    # Verify old password first
    auth_user = await authenticate_user(email, old_password)
    if not auth_user:
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    # Then update
```

---

### 14. **Missing Security Headers**
**Issue:**
- No X-Content-Type-Options header
- No X-Frame-Options header
- No Content-Security-Policy header
- No Strict-Transport-Security header

**Fix:**
```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

---

### 15. **No SQL Injection Prevention on Dynamic Queries**
**Issue:** Need to verify ALL database functions use parameterized queries
**Recommendation:** Audit all SQL files (db/table.sql)

---

## 🟢 GOOD PRACTICES IDENTIFIED

✅ **Password Hashing:** Using `crypt()` function with bcrypt salt (`gen_salt('bf')`)  
✅ **Role-Based Access Control (RBAC):** Implemented checks for admin/user/guest roles  
✅ **Comprehensive Logging:** Good logging throughout the application  
✅ **Email Validation:** Using Pydantic's `EmailStr` type  
✅ **Environment Variables:** Using `.env` for sensitive configuration  
✅ **Async Database:** Using connection pooling for performance  
✅ **Token-Based Auth:** JWT implementation with expiration  

---

## 📋 SUMMARY TABLE

| Issue | Severity | Type | Status |
|-------|----------|------|--------|
| Hardcoded JWT Secret Key | CRITICAL | Auth | ❌ Not Fixed |
| CORS Allow All Origins | CRITICAL | CSRF | ❌ Not Fixed |
| No Rate Limiting | CRITICAL | DoS | ❌ Not Fixed |
| Error Message Disclosure | HIGH | InfoDisclosure | ❌ Not Fixed |
| Weak Password Validation | HIGH | Auth | ❌ Not Fixed |
| No HTTPS Enforcement | HIGH | Transport | ❌ Not Fixed |
| No File Size Limits | HIGH | DoS | ❌ Not Fixed |
| Incomplete Input Validation | HIGH | Injection | ❌ Not Fixed |
| No Token Rotation | MEDIUM | Auth | ❌ Not Fixed |
| No Refresh Token | MEDIUM | Auth | ❌ Not Fixed |
| Missing Security Headers | MEDIUM | Headers | ❌ Not Fixed |
| No Password Verification | MEDIUM | Auth | ❌ Not Fixed |

---

## 🎯 RECOMMENDED FIXES (Priority Order)

1. **IMMEDIATE:**
   - Fix JWT secret key from environment
   - Fix CORS configuration
   - Implement rate limiting
   - Hide error details from responses

2. **URGENT (Within 1 week):**
   - Add password complexity requirements
   - Implement HTTPS/TLS enforcement
   - Add request body size limits
   - Add security headers middleware

3. **IMPORTANT (Within 2 weeks):**
   - Implement token refresh mechanism
   - Add old password verification for password changes
   - Complete file upload validation
   - Audit all SQL queries

4. **NICE-TO-HAVE:**
   - Implement token revocation (blacklist)
   - Add rate limiting per user
   - Implement 2FA/MFA
   - Add request signing/integrity checks

---

## 🔒 Security Best Practices Checklist

- [ ] Store all secrets in environment variables (no hardcoding)
- [ ] Use HTTPS/TLS in production
- [ ] Implement rate limiting on all auth endpoints
- [ ] Validate all input (type, length, format)
- [ ] Hide sensitive error information from users
- [ ] Log all security-relevant events with context
- [ ] Use parameterized queries for all database operations
- [ ] Implement proper CORS configuration
- [ ] Add security headers to all responses
- [ ] Implement password complexity requirements
- [ ] Use strong encryption for sensitive data
- [ ] Implement account lockout after failed attempts
- [ ] Regular security audits and penetration testing
- [ ] Keep dependencies updated (check requirements.txt)
- [ ] Implement request signing/integrity checks

---

**Report Generated:** January 13, 2026  
**Application:** Citation Generator API  
**Status:** Requires Security Improvements
