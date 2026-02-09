from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime


app = FastAPI()

class customMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # ensure request context (auth, start time) is set before handling
        await self.add_request_context(request)
        start_time = getattr(request.state, "start_time", datetime.now())
        response = await call_next(request)
        end_time = datetime.now()
        execution_time = end_time - start_time
        response.headers["X-Execution-Time"] = str(execution_time.total_seconds())
        return response
    async def add_request_context(self, request):
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
            if user_data and user_data.get("authenticated"):
                request.state.user = user_data.get("user_id")
                request.state.role = user_data.get("role")
                request.state.authenticated = user_data.get("authenticated")
                request.state.email = user_data.get("email")
            else:
                raise HTTPException(status_code=401, detail="Invalid email or password")    
        
    
app.add_middleware(customMiddleware)
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
app.include_router(userrouter, prefix="/user", tags=["user"])
app.include_router(mainrouter, prefix="/main", tags=["main"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(file_router, prefix="/file", tags=["file"])
# app.include_router(test_router, prefix="/test", tags=["test"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Citation Generator API"}