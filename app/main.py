from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime
from .config import settings
from .data import SKILLS_DB
import random
import os

environment = os.getenv("ENVIRONMENT", "development") 

show_docs = environment != "production"

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    docs_url="/docs" if show_docs else None, 
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

@app.get("/trending")
async def get_trending(limit: int = Query(10, ge=1, le=50)):
    """Skills met hoogste groei"""
    trending = sorted(
        SKILLS_DB.items(),
        key=lambda x: x[1].get("demand", 0), 
        reverse=True
    )[:limit]
    return {"trending": [{"name": k, **v} for k, v in trending]}

@app.get("/compare")
async def compare_skills(skills: List[str] = Query(...)):
    """Vergelijk meerdere skills"""
    result = {}
    for skill in skills:
        if skill not in SKILLS_DB:
            raise HTTPException(404, f"Skill '{skill}' niet gevonden")
        result[skill] = SKILLS_DB[skill]
    return {"comparison": result}

@app.get("/advice")
async def get_advice(skill: str = Query(...)):
    """Krijg carrière advies"""
    if skill not in SKILLS_DB:
        raise HTTPException(404, f"Skill '{skill}' niet gevonden")
    
    data = SKILLS_DB[skill]
    advice = f"{skill} heeft een hoge vraag ({data['demand']}/10). "
    advice += "Aanbevolen: online cursussen en certificeringen."
    return {"skill": skill, "advice": advice}