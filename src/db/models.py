"""Database models for the application."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


Base = declarative_base()


class Inquiry(Base):
    """Model for tracking infrastructure inquiries."""
    
    __tablename__ = "inquiries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    slack_user_id = Column(String(50), nullable=False, index=True)
    slack_channel_id = Column(String(50), nullable=False)
    slack_thread_ts = Column(String(50), nullable=True)
    
    question = Column(Text, nullable=False)
    environment = Column(String(50), nullable=True)
    deadline = Column(String(100), nullable=True)
    urgency = Column(String(20), nullable=True)
    category = Column(String(50), nullable=True)
    
    resolved_from_kb = Column(Boolean, default=False)
    kb_answer = Column(Text, nullable=True)
    
    jira_ticket_id = Column(String(50), nullable=True, index=True)
    jira_ticket_url = Column(String(500), nullable=True)
    assigned_team = Column(String(50), nullable=True)
    
    status = Column(String(50), default="open")  # open, in_progress, resolved, closed
    
    inquiry_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Inquiry(id={self.id}, slack_user={self.slack_user_id}, status={self.status})>"


class KnowledgeBaseEntry(Base):
    """Model for knowledge base entries."""
    
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String(50), unique=True, nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    team = Column(String(50), nullable=True)
    tags = Column(JSON, nullable=True)
    
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<KnowledgeBaseEntry(id={self.entry_id}, team={self.team})>"


def get_db_engine(database_url: str):
    """Create database engine."""
    return create_engine(database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)


def get_session_maker(engine):
    """Create session maker."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(database_url: str):
    """Initialize database tables."""
    engine = get_db_engine(database_url)
    Base.metadata.create_all(engine)
    return engine
