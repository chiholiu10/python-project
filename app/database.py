from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./skills.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} 
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class SkillDB(Base):
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    demand = Column(Integer, nullable=False)
    trend = Column(String, nullable=False)
    salary = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_skill(db, skill_id: int):
    """Haal één skill op basis van ID"""
    return db.query(SkillDB).filter(SkillDB.id == skill_id).first()

def get_all_skills(db, skip: int = 0, limit: int = 100):
    """Haal alle skills op met paginering"""
    return db.query(SkillDB).offset(skip).limit(limit).all()

def get_skills_count(db):
    """Totaal aantal skills"""
    return db.query(SkillDB).count()

def search_skills_by_demand(db, min_demand: int = 0, max_demand: int = 100):
    """Zoek skills op basis van demand range"""
    return db.query(SkillDB).filter(SkillDB.demand >= min_demand, SkillDB.demand <= max_demand).all()

def update_skill(db, skill_id: int, **kwargs):
    """Update een skill"""
    skill = db.query(SkillDB).filter(SkillDB.id == skill_id).first()
    if skill:
        for key, value in kwargs.items():
            if hasattr(skill, key):
                setattr(skill, key, value)
        db.commit()
        db.refresh(skill)
    return skill

def delete_skill(db, skill_id: int):
    """Verwijder een skill"""
    skill = db.query(SkillDB).filter(SkillDB.id == skill_id).first()
    if skill:
        db.delete(skill)
        db.commit()
        return True
    return False

def create_skill(db: Session, name: str, demand: int, trend: str, salary: str, reason: str):
    """Voeg een nieuwe skill toe aan de database"""
    db_skill = SkillDB(
        name=name,
        demand=demand,
        trend=trend,
        salary=salary,
        reason=reason
    )
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return db_skill