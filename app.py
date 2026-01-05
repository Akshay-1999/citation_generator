from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime

app = FastAPI()

class customMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = datetime.now()
        response = await call_next(request)
        end_time = datetime.now()
        execution_time = end_time - start_time
        response.headers["X-Execution-Time"] = str(execution_time.total_seconds())
        return response
app.add_middleware(customMiddleware)
app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from db.userendpoint import userrouter
from routes.main import mainrouter
from utils.auth_utils import authrouter
from test import test_router
app.include_router(userrouter, prefix="/user", tags=["user"])
app.include_router(mainrouter, prefix="/main", tags=["main"])
app.include_router(authrouter, prefix="/auth", tags=["auth"])
# app.include_router(test_router, prefix="/test", tags=["test"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Citation Generator API"}