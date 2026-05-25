from fastapi import FastAPI, Query, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime
from .config import settings
from .database import get_db, SkillDB, get_skill, get_all_skills, update_skill, delete_skill, search_skills_by_demand, get_skills_count
from pydantic import BaseModel
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
import random
import os

class SkillCreate(BaseModel):
    name: str
    demand: int
    trend: str
    salary: str
    reason: str

class SkillUpdate(BaseModel):
    name: Optional[str] = None
    demand: Optional[int] = None
    trend: Optional[str] = None
    salary: Optional[str] = None
    reason: Optional[str] = None

class SkillResponse(BaseModel):
    id: int
    name: str
    demand: int
    trend: str
    salary: str
    reason: str
    created_at: datetime
    updated_at: datetime

environment = os.getenv("ENVIRONMENT", "development") 

show_docs = environment != "production"

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    docs_url="/docs" if show_docs else None, 
)

app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SlowAPIMiddleware)

@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "environment": settings.environment,
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "read": ["/skills", "/skills/{skill_id}", "/trending", "/compare", "/advice"],
            "create": ["/skills (POST)"],
            "update": ["/skills/{skill_id} (PUT)", "/skills/{skill_id} (PATCH)"],
            "delete": ["/skills/{skill_id} (DELETE)"]
        }
    }

@app.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_new_skill(skill: SkillCreate, db: Session = Depends(get_db)):
    """Voeg een nieuwe skill toe aan de database"""
    # Check of skill al bestaat
    existing_skill = db.query(SkillDB).filter(SkillDB.name == skill.name).first()
    if existing_skill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill '{skill.name}' bestaat al"
        )
    
    db_skill = create_skill(
        db=db,
        name=skill.name,
        demand=skill.demand,
        trend=skill.trend,
        salary=skill.salary,
        reason=skill.reason
    )
    return db_skill

if settings.environment != "production":
  @app.get("/debug-db")
  async def debug_db(db: Session = Depends(get_db)):
      """Debug: check wat er in de database zit"""
      count = db.query(SkillDB).count()
      first = db.query(SkillDB).first()
      return {
          "count": count,
          "first_skill": first.name if first else None,
          "db_path": "skills.db"
      }

@app.get("/skills")
async def get_all_skills_db(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    skills = get_all_skills(db, skip=skip, limit=limit)
    total = get_skills_count(db)
    
    return {
        "skills": [
            {
                "id": s.id,
                "name": s.name,
                "demand": s.demand,
                "trend": s.trend,
                "salary": s.salary,
                "reason": s.reason,
                "created_at": s.created_at,
                "updated_at": s.updated_at
            }
            for s in skills
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_skill_by_id(skill_id: int, db: Session = Depends(get_db)):
    """Haal een specifieke skill op via ID"""
    skill = get_skill(db, skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill met ID {skill_id} niet gevonden"
        )
    return skill

@app.get("/skills/name/{skill_name}")
async def get_skill_by_name(skill_name: str, db: Session = Depends(get_db)):
    """Zoek een skill op naam"""
    skill = db.query(SkillDB).filter(SkillDB.name == skill_name).first()
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_name}' niet gevonden"
        )
    return skill

@app.get("/skills/search/demand")
async def search_by_demand(
    min_demand: int = Query(..., ge=0, le=100),
    max_demand: Optional[int] = Query(None, ge=0, le=100),
    db: Session = Depends(get_db)
):
    skills = search_skills_by_demand(db, min_demand, max_demand)
    return {
        "skills": [
            {
                "id": s.id,
                "name": s.name,
                "demand": s.demand,
                "trend": s.trend,
                "salary": s.salary,
                "reason": s.reason
            }
            for s in skills
        ],
        "count": len(skills),
        "min_demand": min_demand,
        "max_demand": max_demand
    }

@app.get("/skills/search/trend/{trend}")
async def search_by_trend(trend: str, db: Session = Depends(get_db)):
    skills = db.query(SkillDB).filter(SkillDB.trend == trend).all()
    return {
        "trend": trend,
        "skills": [
            {
                "id": s.id,
                "name": s.name,
                "demand": s.demand,
                "trend": s.trend,
                "salary": s.salary,
                "reason": s.reason
            }
            for s in skills
        ],
        "count": len(skills)
    }

@app.put("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill_full(
    skill_id: int, 
    skill_update: SkillCreate, 
    db: Session = Depends(get_db)
):
    """Volledige update van een skill"""
    # Check of skill bestaat
    existing_skill = get_skill(db, skill_id)
    if not existing_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill met ID {skill_id} niet gevonden"
        )
    
    # Check voor dubbele naam (behalve de huidige skill)
    duplicate = db.query(SkillDB).filter(
        SkillDB.name == skill_update.name,
        SkillDB.id != skill_id
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill '{skill_update.name}' bestaat al"
        )
    
    updated_skill = update_skill(
        db=db,
        skill_id=skill_id,
        name=skill_update.name,
        demand=skill_update.demand,
        trend=skill_update.trend,
        salary=skill_update.salary,
        reason=skill_update.reason
    )
    return updated_skill

@app.patch("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill_partial(
    skill_id: int,
    skill_update: SkillUpdate,
    db: Session = Depends(get_db)
):
    """Gedeeltelijke update van een skill (alleen meegegeven velden worden geüpdatet)"""
    existing_skill = get_skill(db, skill_id)
    if not existing_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill met ID {skill_id} niet gevonden"
        )
    
    update_data = skill_update.dict(exclude_unset=True)
    
    if "name" in update_data:
        duplicate = db.query(SkillDB).filter(
            SkillDB.name == update_data["name"],
            SkillDB.id != skill_id
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Skill '{update_data['name']}' bestaat al"
            )
    
    updated_skill = update_skill(db, skill_id, **update_data)
    return updated_skill

@app.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill_by_id(skill_id: int, db: Session = Depends(get_db)):
    """Verwijder een skill op basis van ID"""
    success = delete_skill(db, skill_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill met ID {skill_id} niet gevonden"
        )
    return None

@app.delete("/skills/batch/delete")
async def delete_multiple_skills(
    skill_ids: List[int] = Query(...),
    db: Session = Depends(get_db)
):
    """Verwijder meerdere skills tegelijk"""
    deleted = []
    not_found = []
    
    for skill_id in skill_ids:
        if delete_skill(db, skill_id):
            deleted.append(skill_id)
        else:
            not_found.append(skill_id)
    
    return {
        "deleted_count": len(deleted),
        "deleted_ids": deleted,
        "not_found_ids": not_found
    }

@app.get("/trending")
async def get_trending(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Skills met hoogste demand"""
    skills = db.query(SkillDB).order_by(SkillDB.demand.desc()).limit(limit).all()
    return {"trending": skills}

@app.get("/compare")
async def compare_skills(
    skills: List[str] = Query(...),
    db: Session = Depends(get_db)
):
    """Vergelijk meerdere skills"""
    result = {}
    for skill_name in skills:
        skill = db.query(SkillDB).filter(SkillDB.name == skill_name).first()
        if not skill:
            raise HTTPException(404, f"Skill '{skill_name}' niet gevonden")
        result[skill_name] = skill
    return {"comparison": result}

@app.get("/advice")
async def get_advice(
    skill: str = Query(...),
    db: Session = Depends(get_db)
):
    """Krijg carrière advies"""
    skill_data = db.query(SkillDB).filter(SkillDB.name == skill).first()
    if not skill_data:
        raise HTTPException(404, f"Skill '{skill}' niet gevonden")
    
    advice = f"{skill} heeft een hoge vraag ({skill_data.demand}/10). "
    
    if skill_data.trend == "stijgend":
        advice += "De trend is stijgend, dus investeren in deze skill is verstandig. "
    elif skill_data.trend == "dalend":
        advice += "Let op: deze skill is dalend in populariteit. "
    else:
        advice += "De marktvraag is stabiel. "
    
    advice += f"Aanbevolen: {skill_data.reason}"
    
    return {
        "skill": skill,
        "advice": advice,
        "data": skill_data
    }

@app.get("/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """Krijg statistieken over alle skills"""
    skills = get_all_skills(db, skip=0, limit=1000)
    
    if not skills:
        return {"message": "Geen skills gevonden in database"}
    
    avg_demand = sum(s.demand for s in skills) / len(skills)
    trends = {}
    for skill in skills:
        trends[skill.trend] = trends.get(skill.trend, 0) + 1
    
    return {
        "total_skills": len(skills),
        "average_demand": round(avg_demand, 2),
        "trend_distribution": trends,
        "highest_demand": max(skills, key=lambda x: x.demand).name if skills else None,
        "timestamp": datetime.now().isoformat()
    }