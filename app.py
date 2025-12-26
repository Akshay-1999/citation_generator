from fastapi import FastAPI

app = FastAPI()

from db.userendpoint import userrouter
from routes.main import mainrouter
from utils.auth_utils import authrouter
from test import test_router
app.include_router(userrouter, prefix="/user", tags=["user"])
app.include_router(mainrouter, prefix="/main", tags=["main"])
app.include_router(authrouter, prefix="/auth", tags=["auth"])
app.include_router(test_router, prefix="/test", tags=["test"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Citation Generator API"}