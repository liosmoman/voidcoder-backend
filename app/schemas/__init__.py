# app/schemas/__init__.py
from .prompt import (
    # Core AI Vision Analysis Schemas (New Rich Structure)
    ImageMetadata, 
    OverallAnalysis, 
    StyleHintItem,         # For BaseElementSchema's style_hints
    BaseElementSchema,     # For detected_elements_tree
    NavElementSchema, 
    LayoutComponentSchema,
    ContentSectionSchema, 
    InteractiveControlSchema, 
    VisualStyleColorSchema,
    VisualStyleTypographySchema, 
    VisualStyleSchema,
    RichImageAnalysisSchema, # Main schema for Vision LLM output

    # Database Interaction Schemas
    ImageEntryBase, 
    ImageEntryCreate, 
    ImageEntryInDB,
    GeneratedPromptBase, 
    GeneratedPromptCreate, 
    GeneratedPromptInDB,
    PromptSessionBase, 
    PromptSessionCreate, 
    PromptSessionInDB,
    
    # API Response Schemas
    GeneratedPromptData, 
    PromptAnalysisResponse
)
from .token import Token, TokenData
from .user import User, UserCreate, UserUpdate, UserInDB # Assuming UserInDB is your main User schema