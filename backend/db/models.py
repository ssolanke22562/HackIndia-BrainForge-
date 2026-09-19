import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    func
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Note(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_type = Column(String(32), nullable=False)  # pdf, docx, image, audio, csv, link, note
    raw_path = Column(String(512), nullable=True)
    wiki_path = Column(String(512), nullable=True)
    title = Column(String(256), nullable=False, default="Untitled Note")
    category = Column(String(64), nullable=True)  # Projects, Areas, Resources, Archives
    tags_json = Column(Text, nullable=False, default="[]")  # JSON encoded list of tags
    summary = Column(Text, nullable=True)
    sha256_hash = Column(String(64), nullable=True, index=True)
    confidence = Column(Float, default=1.0)
    status = Column(String(32), default="captured")  # captured, processing, indexed, failed
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    # Relationships
    chunks = relationship("Chunk", back_populates="note", cascade="all, delete-orphan")
    outgoing_links = relationship("Link", foreign_keys="Link.source_note_id", back_populates="source_note", cascade="all, delete-orphan")
    incoming_links = relationship("Link", foreign_keys="Link.target_note_id", back_populates="target_note", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    note_id = Column(String(36), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=False)
    embedding_id = Column(String(64), nullable=True)  # Reference index/id in FAISS
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    # Relationships
    note = relationship("Note", back_populates="chunks")

class Link(Base):
    __tablename__ = "links"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_note_id = Column(String(36), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_note_id = Column(String(36), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    similarity_score = Column(Float, nullable=False, default=0.0)
    link_type = Column(String(32), nullable=False, default="semantic")  # semantic, category_hub, manual
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    # Relationships
    source_note = relationship("Note", foreign_keys=[source_note_id], back_populates="outgoing_links")
    target_note = relationship("Note", foreign_keys=[target_note_id], back_populates="incoming_links")

    __table_args__ = (
        Index("idx_links_source_target", "source_note_id", "target_note_id"),
    )

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(256), nullable=False, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="messages")
    retrievals = relationship("Retrieval", back_populates="message", cascade="all, delete-orphan")

class Retrieval(Base):
    __tablename__ = "retrievals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    note_id = Column(String(36), nullable=True)
    chunk_id = Column(String(36), nullable=True)
    snippet_text = Column(Text, nullable=False)
    relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="retrievals")

class UserPersona(Base):
    __tablename__ = "user_persona"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(128), nullable=False, default="SecondSelf User")
    role_profession = Column(String(256), nullable=False, default="Knowledge Worker & Researcher")
    communication_tone = Column(String(128), nullable=False, default="Direct, technical, and concise")
    perspective = Column(String(32), nullable=False, default="First-Person (I, my)")
    custom_vocabulary = Column(Text, nullable=True, default="tradeoffs, architecture, synthesis, high-leverage, action items")
    writing_sample = Column(Text, nullable=True, default="")
    response_format = Column(String(256), nullable=False, default="TL;DR summary first, followed by clear bullet points and actionable takeaways")
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
