from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
from fastapi import Request


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
                raise HTTPException(status_code=401, detail="Invalid email or password")    
        
    
app.add_middleware(customMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/")
async def root():
    return RedirectResponse(url="/static/login.html")