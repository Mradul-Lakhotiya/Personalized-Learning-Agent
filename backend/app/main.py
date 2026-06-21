from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
# Load environment variables from the parent directory
load_dotenv(dotenv_path="../.env")

from app.routes import router as agent_router

app = FastAPI(
    title="Personalized Learning Agent API",
    description="Backend for the LangGraph-based Personalized Learning Agent",
    version="1.0.0"
)

# CORS Setup
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)

@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "message": "Personalized Learning Agent API is running."}

@app.get("/")
async def root():
    return {"message": "Welcome to the Personalized Learning Agent API. Go to /docs for the Swagger UI."}
