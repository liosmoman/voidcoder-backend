# app/models/prompt_session.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.session import Base 

# User model remains the same
class User(Base):
    __tablename__ = "users"
    # ... (existing User model code) ...
    id = Column(Integer, primary_key=True, index=True)
    oauth_provider = Column(String, index=True, nullable=True) 
    oauth_id = Column(String, unique=True, index=True, nullable=True) 
    email = Column(String, unique=True, index=True, nullable=False) 
    display_name = Column(String, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    prompt_sessions = relationship("PromptSession", back_populates="owner", cascade="all, delete-orphan")


# NEW MODEL for individual image entries
class ImageEntry(Base):
    __tablename__ = "image_entries"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False) # Title given by the user
    original_filename = Column(String, nullable=True)  # Original filename of this specific image
    # Store the AI analysis specific to this image
    analysis_output_json = Column(JSONB, nullable=True) 
    order_in_session = Column(Integer, default=0) # Its order within the session

    prompt_session_id = Column(Integer, ForeignKey("prompt_sessions.id"), nullable=False)
    prompt_session = relationship("PromptSession", back_populates="image_entries")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PromptSession(Base):
    __tablename__ = "prompt_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_name = Column(String, index=True, nullable=True) 
    # image_filename is now less relevant here, or could be first image. Let's make it optional.
    image_filename = Column(String, nullable=True) 
    
    # analysis_output_json on PromptSession will now store the FINAL CONSOLIDATED PROMPT'S AI source,
    # OR it might be removed if all detailed analysis is per ImageEntry.
    # For now, let's assume it might hold a summary or the AI's understanding of the multi-page structure.
    # We will remove the per-image analysis from this top-level session for now.
    # analysis_output_json = Column(JSONB, nullable=True) # REMOVE OR REPURPOSE LATER

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Assuming sessions must have owners
    owner = relationship("User", back_populates="prompt_sessions") 

    # Relationship to ImageEntry objects
    image_entries = relationship("ImageEntry", back_populates="prompt_session", cascade="all, delete-orphan", order_by="ImageEntry.order_in_session")

    # GeneratedPrompts will now ideally be the FINAL consolidated prompt(s) for the whole session
    generated_prompts = relationship("GeneratedPrompt", back_populates="session", cascade="all, delete-orphan")


class GeneratedPrompt(Base):
    __tablename__ = "generated_prompts"
    # ... (existing GeneratedPrompt model code - no change here for now, but its meaning shifts) ...
    # This will store the *final consolidated prompt* for the multi-image session.
    id = Column(Integer, primary_key=True, index=True)
    prompt_type = Column(String, index=True, nullable=True) # e.g., "consolidated_multi_page"
    prompt_text = Column(Text, nullable=False)
    order_in_session = Column(Integer, default=0) # Usually just one consolidated prompt
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    session_id = Column(Integer, ForeignKey("prompt_sessions.id"), nullable=False) 
    session = relationship("PromptSession", back_populates="generated_prompts")