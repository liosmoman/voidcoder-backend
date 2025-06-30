# app/schemas/prompt.py
import datetime
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid

# --- Core Schemas for AI Vision Analysis (Your existing rich structure) ---
# No changes needed in this section

class ImageMetadata(BaseModel):
    original_filename: Optional[str] = None
    image_dimensions: Optional[Dict[str, int]] = None
    analysis_timestamp: Optional[str] = None

class OverallAnalysis(BaseModel):
    page_title_guess: Optional[str] = "Untitled Page"
    page_purpose_and_audience: Optional[str] = "General purpose webpage for a broad audience."
    dominant_theme: Optional[str] = "Neutral theme."
    primary_layout_type: Optional[str] = "Standard single column."
    general_description: Optional[str] = "A webpage screenshot."
    key_takeaways: List[str] = Field(default_factory=list)

class StyleHintItem(BaseModel): 
    property: str 
    value: str    

class BaseElementSchema(BaseModel):
    id: str = Field(default_factory=lambda: f"el_{uuid.uuid4().hex[:8]}")
    element_type: str 
    semantic_guess: Optional[str] = None 
    text_content: Optional[str] = None 
    bounding_box: Optional[Dict[str, int]] = None 
    style_hints: List[StyleHintItem] = Field(default_factory=list) 
    interaction_notes: Optional[str] = None 
    accessibility_notes: Optional[str] = None 
    children: List['BaseElementSchema'] = Field(default_factory=list)

BaseElementSchema.update_forward_refs()

class NavElementSchema(BaseModel):
    id: str = Field(default_factory=lambda: f"nav_el_{uuid.uuid4().hex[:6]}")
    element_type: str 
    items: List[str] = Field(default_factory=list)
    style_hints: Optional[str] = None 

class LayoutComponentSchema(BaseModel):
    id: str = Field(default_factory=lambda: f"layout_comp_{uuid.uuid4().hex[:6]}")
    element_type: str 
    description: Optional[str] = None 
    grid_details: Optional[str] = None

class ContentSectionSchema(BaseModel):
    id: str = Field(default_factory=lambda: f"content_sec_{uuid.uuid4().hex[:6]}")
    element_type: str 
    headline: Optional[str] = None
    text_elements: List[str] = Field(default_factory=list) 
    image_elements: List[str] = Field(default_factory=list) 

class InteractiveControlSchema(BaseModel):
    id: str = Field(default_factory=lambda: f"control_{uuid.uuid4().hex[:6]}")
    element_type: str 
    label_or_text: Optional[str] = None 
    purpose: Optional[str] = None 

class VisualStyleColorSchema(BaseModel):
    hex: Optional[str] = None 
    name: Optional[str] = None
    usage_hint: Optional[str] = None

class VisualStyleTypographySchema(BaseModel):
    font_family_guess: Optional[str] = None
    font_size_category: Optional[str] = None 
    font_weight_guess: Optional[str] = None 
    usage_hint: Optional[str] = None 

class VisualStyleSchema(BaseModel):
    primary_colors: List[VisualStyleColorSchema] = Field(default_factory=list)
    secondary_colors: List[VisualStyleColorSchema] = Field(default_factory=list)
    accent_colors: List[VisualStyleColorSchema] = Field(default_factory=list)
    neutral_colors: List[VisualStyleColorSchema] = Field(default_factory=list)
    primary_font_family: Optional[str] = "Inter, sans-serif"
    secondary_font_family: Optional[str] = None
    heading_typography: List[Dict[str, str]] = Field(default_factory=list)
    body_typography: Optional[Dict[str, str]] = Field(default_factory=dict)
    spacing_density: Optional[str] = "Normal" 
    component_spacing: Optional[str] = None
    corner_radius_style: Optional[str] = "Slightly Rounded (4-8px)"
    shadow_style: Optional[str] = "Subtle box shadows"
    iconography_style: Optional[str] = None

class RichImageAnalysisSchema(BaseModel): 
    image_metadata: Optional[ImageMetadata] = None
    overall_analysis: Optional[OverallAnalysis] = None
    navigation_elements: List[NavElementSchema] = Field(default_factory=list)
    layout_components: List[LayoutComponentSchema] = Field(default_factory=list)
    content_sections: List[ContentSectionSchema] = Field(default_factory=list)
    interactive_controls: List[InteractiveControlSchema] = Field(default_factory=list)
    visual_style_guide: Optional[VisualStyleSchema] = None 
    detected_elements_tree: List[BaseElementSchema] = Field(default_factory=list) 

    class Config:
        from_attributes = True

# --- Schemas for Database Interaction & API Responses ---

class ImageEntryBase(BaseModel):
    title: str
    original_filename: Optional[str] = None
    analysis_output_json: Optional[RichImageAnalysisSchema] = None
    order_in_session: Optional[int] = 0

class ImageEntryCreate(ImageEntryBase):
    pass

class ImageEntryInDB(ImageEntryBase):
    id: int
    prompt_session_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class GeneratedPromptBase(BaseModel):
    prompt_type: Optional[str] = "ultra_detailed_multi_page_app"
    prompt_text: str 
    order_in_session: Optional[int] = 0

class GeneratedPromptCreate(GeneratedPromptBase):
    pass

class GeneratedPromptInDB(GeneratedPromptBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class PromptSessionBase(BaseModel):
    session_name: Optional[str] = None
    image_filename: Optional[str] = None 

class PromptSessionCreate(PromptSessionBase):
    pass

class PromptSessionInDB(BaseModel): 
    id: int
    owner_id: int 
    session_name: Optional[str] = None
    image_filename: Optional[str] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    image_entries: List[ImageEntryInDB] = [] 
    generated_prompts: List[GeneratedPromptInDB] = []

    class Config:
        from_attributes = True
            
class GeneratedPromptData(BaseModel): 
    prompt_type: str
    prompt_text: str

class PromptAnalysisResponse(BaseModel):
    id: Optional[int] = None 
    session_name: Optional[str] = None 
    image_filename: Optional[str] = None 
    prompts: List[GeneratedPromptData] 

    class Config:
        from_attributes = True

# --- NEW SCHEMA FOR PAGINATED HISTORY RESPONSE ---
class HistoryResponse(BaseModel):
    total_count: int
    sessions: List[PromptSessionInDB]
# --- END OF NEW SCHEMA ---