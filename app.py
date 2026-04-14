from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import os
from dotenv import load_dotenv

app = FastAPI()

load_dotenv()
secret_key = os.getenv("secret_key")


# ─── Custom Middleware ───────────────────────────────────────────────────────
class customMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):

        # ✅ IMPORTANT: Skip OPTIONS requests (preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        await self.add_request_context(request)

        start_time = getattr(request.state, "start_time", datetime.now())
        response = await call_next(request)

        end_time = datetime.now()
        execution_time = end_time - start_time
        response.headers["X-Execution-Time"] = str(execution_time.total_seconds())

        return response

    async def add_request_context(self, request: Request):
        request.state.start_time = datetime.now()
        request.state.authenticated = False
        request.state.user = None

        token_data = request.cookies.get("auth_token")
        
        # 🐛 DEBUG: Log incoming cookies for troubleshooting
        from utils.logging_utils import set_system_logger
        debug_logger = set_system_logger("system_logger")
        debug_logger.info(f"--- Incoming Cookies: {list(request.cookies.keys())} ---")

        if token_data:
            from utils.auth_utils import auth_manger
            from dotenv import load_dotenv

            auth_manager_instance = auth_manger(secret_key=secret_key)
            user_data = auth_manager_instance.validate_authtoken(token_data)

            if user_data:
                request.state.user = user_data
                request.state.authenticated = True
            else:
                request.state.authenticated = False


# ─── Middleware Order (VERY IMPORTANT) ───────────────────────────────────────

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://citation-generator-teal.vercel.app",
    "http://192.168.0.69:5173",
]

# Add any additional origins from environment variable
extra_origins = os.getenv("ALLOWED_ORIGINS")
if extra_origins:
    ALLOWED_ORIGINS.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

# 🐛 DEBUG: Log allowed origins at startup
from utils.logging_utils import set_system_logger
startup_logger = set_system_logger("system_logger")
startup_logger.info(f"--- CORS Allowed Origins: {ALLOWED_ORIGINS} ---")

# 1️⃣ Custom middleware FIRST (inner)
app.add_middleware(customMiddleware)

# 2️⃣ CORS middleware LAST (outermost) — handles preflight OPTIONS before anything else
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*-akshay-1999s-projects\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ────────────────────────────────────────────────────────────────
from db.userendpoint import userrouter
from routes.main import mainrouter
from routes.auth import auth_router
from routes.file import file_router
from routes.chat import chat_router
from routes.folderprocesser import folder_processer_router

app.include_router(userrouter, prefix="/user", tags=["user"])
app.include_router(mainrouter, prefix="/main", tags=["main"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(file_router, prefix="/file", tags=["file"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(folder_processer_router, prefix="/folder", tags=["folder"])

# ─── Health Check ───────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Backend is running"}