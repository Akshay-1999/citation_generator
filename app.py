from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
from fastapi import Request
import os


app = FastAPI()

class customMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)   
    async def dispatch(self, request: Request, call_next):  
        await self.add_request_context(request)
        start_time = getattr(request.state, "start_time", datetime.now())
        response = await call_next(request)
        end_time = datetime.now()
        execution_time = end_time - start_time
        response.headers["X-Execution-Time"] = str(execution_time.total_seconds())
        return response

    async def add_request_context(self , request : Request ):
        request.state.start_time = datetime.now()
        request.state.authenticated = False
        request.state.user = None
        token_data = request.cookies.get("auth_token")
        if token_data:
            from utils.auth_utils import auth_manger
            import os
            from dotenv import load_dotenv
            load_dotenv()
            secret_key = os.getenv("secret_key")
            auth_manager_instance = auth_manger(secret_key=secret_key)
            user_data = auth_manager_instance.validate_authtoken(token_data)
            if user_data:
                request.state.user = user_data
                request.state.authenticated = True
            else:
                # Instead of raising 401 here which breaks static file serving sometimes, 
                # we just set authenticated to false. Routers will handle the rest.
                request.state.authenticated = False
        
    
app.add_middleware(customMiddleware)

# API Routers
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


# Serve Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve React Assets specifically to avoid conflicts
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SPA Routing: Serve index.html for all non-API routes
@app.get("/{full_path:path}")
async def serve_react_app(request: Request, full_path: str):
    # Skip API routes and static files
    if full_path.startswith(("user", "main", "auth", "file", "chat", "folder", "static", "assets")):
        raise HTTPException(status_code=404)
    
    index_path = os.path.join("frontend", "dist", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return RedirectResponse(url="/static/login.html")