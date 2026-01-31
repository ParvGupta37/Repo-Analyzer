"""
SQLAlchemy models matching the exact schema specification.
All UUIDs stored as TEXT, JSON fields stored as TEXT.
"""
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from db.database import Base


class Repository(Base):
    __tablename__ = "repositories"
    
    id = Column(Text, primary_key=True)
    repo_url = Column(Text, unique=True, nullable=False)
    owner = Column(Text)
    name = Column(Text)
    primary_language = Column(Text)
    created_at = Column(DateTime)
    analyzed_at = Column(DateTime)


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"
    
    id = Column(Text, primary_key=True)
    repo_id = Column(Text, ForeignKey("repositories.id"))
    status = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


class RepoFile(Base):
    __tablename__ = "repo_files"
    
    id = Column(Text, primary_key=True)
    repo_id = Column(Text, ForeignKey("repositories.id"))
    file_path = Column(Text)
    language = Column(Text)
    role = Column(Text)
    summary = Column(Text)


class TechStack(Base):
    __tablename__ = "tech_stack"
    
    id = Column(Text, primary_key=True)
    repo_id = Column(Text, ForeignKey("repositories.id"))
    name = Column(Text)
    category = Column(Text)
    reasoning = Column(Text)


class ArchitectureSummary(Base):
    __tablename__ = "architecture_summary"
    
    repo_id = Column(Text, ForeignKey("repositories.id"), primary_key=True)
    overview = Column(Text)
    components = Column(Text)  # Serialized JSON
    data_flow = Column(Text)


class IssuesInsights(Base):
    __tablename__ = "issues_insights"
    
    repo_id = Column(Text, ForeignKey("repositories.id"), primary_key=True)
    recurring_problems = Column(Text)
    risky_areas = Column(Text)
    active_features = Column(Text)


class ContributorGuide(Base):
    __tablename__ = "contributor_guide"
    
    repo_id = Column(Text, ForeignKey("repositories.id"), primary_key=True)
    getting_started = Column(Text)
    safe_areas = Column(Text)
    caution_areas = Column(Text)
    feature_extension_guide = Column(Text)


class QALog(Base):
    __tablename__ = "qa_logs"
    
    id = Column(Text, primary_key=True)
    repo_id = Column(Text, ForeignKey("repositories.id"))
    question = Column(Text)
    answer = Column(Text)
    created_at = Column(DateTime, server_default=func.now())