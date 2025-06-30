# app/crud/crud_prompt_session.py
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict

from app.crud.crud_base import CRUDBase
from app.models.prompt_session import PromptSession, GeneratedPrompt, User, ImageEntry # Import ImageEntry model
# Ensure GeminiVisionAnalysis is your rich schema if you named it that, or RichImageAnalysisSchema
from app.schemas.prompt import PromptSessionCreate, GeneratedPromptCreate 

class CRUDPromptSession(CRUDBase[PromptSession, PromptSessionCreate, PromptSessionCreate]):
    def create_with_images_and_final_prompt(
        self, 
        db: Session, 
        *, 
        session_obj_in: PromptSessionCreate, 
        image_analyses: List[Dict[str, Any]],
        final_prompts_obj_in: List[GeneratedPromptCreate],
        owner_id: int
    ) -> PromptSession:
        """
        Create a new PromptSession, its associated ImageEntry objects (with their analyses),
        and the final consolidated GeneratedPrompt object(s).
        """
        

        db_session = PromptSession(
            session_name=session_obj_in.session_name,
            image_filename=session_obj_in.image_filename,
            owner_id=owner_id 
        )
        db.add(db_session)
        db.flush() 

        db_image_entries = []
        for order, img_analysis_data in enumerate(image_analyses):
            analysis_json_for_db = img_analysis_data.get("analysis_output_json")
            if not isinstance(analysis_json_for_db, dict) and analysis_json_for_db is not None:
                print(f"WARNING CRUD: analysis_output_json for {img_analysis_data.get('title')} is not a dict, type: {type(analysis_json_for_db)}")
                analysis_json_for_db = None

            db_image_entry = ImageEntry(
                title=img_analysis_data.get("title", "Untitled Image"),
                original_filename=img_analysis_data.get("original_filename"),
                analysis_output_json=analysis_json_for_db,
                order_in_session=order,
                prompt_session_id=db_session.id 
            )
            db_image_entries.append(db_image_entry)
        
        if db_image_entries:
            db.add_all(db_image_entries)
        
        db_final_prompts = []
        for order, prompt_in in enumerate(final_prompts_obj_in):
            db_final_prompt = GeneratedPrompt(
                prompt_type=prompt_in.prompt_type or "consolidated_multi_page",
                prompt_text=prompt_in.prompt_text,
                order_in_session=order,
                session_id=db_session.id 
            )
            db_final_prompts.append(db_final_prompt)

        if db_final_prompts:
            db.add_all(db_final_prompts)
            
        db.commit()
        db.refresh(db_session)
        
        return db_session

    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[PromptSession]:
        return (
            db.query(self.model)
            .filter(PromptSession.owner_id == owner_id)
            .order_by(PromptSession.created_at.desc()) 
            .offset(skip)
            .limit(limit)
            .all()
        )

    # --- ADD THIS NEW METHOD ---
    def get_count_by_owner(self, db: Session, *, owner_id: int) -> int:
        """
        Get the total count of prompt sessions for a specific owner.
        """
        return db.query(self.model).filter(PromptSession.owner_id == owner_id).count()
    # --- END OF NEW METHOD ---

prompt_session = CRUDPromptSession(PromptSession)