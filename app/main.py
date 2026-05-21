from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime
from .config import settings
from .data import SKILLS_DB
import random

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "environment": settings.environment,
        "version": "1.0.0",
        "status": "online",
        "endpoints": ["/skills", "/trending", "/compare", "/advice"]
    }

@app.get("/skills")
async def get_all_skills():
    """Alle skills met marktdata"""
    return {
      "skills": SKILLS_DB,
      "total": len(SKILLS_DB),
      "timestamp": datetime.now().isoformat()
    }