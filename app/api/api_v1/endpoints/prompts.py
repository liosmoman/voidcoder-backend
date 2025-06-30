# app/api/api_v1/endpoints/prompts.py

import base64, io, datetime, httpx, re, traceback, uuid
from typing import Optional, List, Dict, Any, Union

from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends, Request
from PIL import Image
from sqlalchemy.orm import Session
from pydantic import ValidationError 
import json

from app.api.deps.user_deps import get_current_user
from app.models.prompt_session import User as UserModel
# Ensure this name matches what you have in your schemas/prompt.py for the detailed structure
from app.schemas import (
    RichImageAnalysisSchema, 
    GeneratedPromptData,
    PromptAnalysisResponse,
    PromptSessionCreate,
    GeneratedPromptCreate,
    PromptSessionInDB,
    # ImageEntryCreate is used by CRUD
)
from app.core.config import settings
from app.db.session import get_db
from app.crud.crud_prompt_session import prompt_session as crud_prompt_session

# --- AI Provider Configurations ---
# ... (This section is fine as you pasted it) ...
import google.generativeai as genai
GEMINI_CONFIGURED_SUCCESSFULLY = False
if settings.ACTIVE_AI_PROVIDER == "GEMINI":
    if settings.GEMINI_API_KEY:
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            print(f"Successfully configured Gemini API key.")
            GEMINI_CONFIGURED_SUCCESSFULLY = True
        except Exception as e:
            print(f"ERROR: Failed to configure Gemini API key: {e}")
    else:
        print("WARNING: ACTIVE_AI_PROVIDER is GEMINI, but GEMINI_API_KEY not found.")

OPENROUTER_CONFIGURED_SUCCESSFULLY = False
if settings.ACTIVE_AI_PROVIDER == "OPENROUTER":
    if settings.OPENROUTER_API_KEY and settings.OPENROUTER_MODEL_IDENTIFIER and settings.OPENROUTER_PLANNER_MODEL_IDENTIFIER:
        OPENROUTER_CONFIGURED_SUCCESSFULLY = True
        print(f"OpenRouter configuration: API key and models found. Will use base URL: {settings.OPENROUTER_BASE_URL}")
    else:
        print("ERROR: ACTIVE_AI_PROVIDER is OPENROUTER, but API_KEY, VISION MODEL, or PLANNER MODEL is missing in settings.")

router = APIRouter()

# --- HELPER FUNCTIONS ---

def format_specific_elements_for_prompt(elements: Optional[List[Any]], category_name: str, indent_level: int = 1) -> str:
    if not elements: return "" 
    indent = "  " * indent_level
    output_str = f"{indent}{category_name}:\n"
    sub_indent = "  " * (indent_level + 1)
    for el_data in elements:
        el_type = getattr(el_data, 'element_type', 'N/A')
        line_parts = [f"{sub_indent}- Type: {el_type}"]
        if hasattr(el_data, 'id'): line_parts.append(f"ID: {getattr(el_data, 'id', 'N/A')}")
        if hasattr(el_data, 'items'): items = getattr(el_data, 'items', []); line_parts.append(f"Items: {', '.join(items[:3])}{'...' if len(items) > 3 else ''}")
        if hasattr(el_data, 'style_hints') and isinstance(getattr(el_data, 'style_hints'), str) : line_parts.append(f"Style: {getattr(el_data, 'style_hints', 'N/A')}")
        if hasattr(el_data, 'description'): line_parts.append(f"Desc: {str(getattr(el_data, 'description', 'N/A'))[:100]}")
        if hasattr(el_data, 'grid_details'): line_parts.append(f"Grid: {getattr(el_data, 'grid_details', 'N/A')}")
        if hasattr(el_data, 'headline'): line_parts.append(f"Headline: {str(getattr(el_data, 'headline', 'N/A'))[:70]}")
        if hasattr(el_data, 'label_or_text'): line_parts.append(f"Label/Text: '{getattr(el_data, 'label_or_text', 'N/A')}'")
        if hasattr(el_data, 'purpose'): line_parts.append(f"Purpose: {getattr(el_data, 'purpose', 'N/A')}")
        output_str += ", ".join(line_parts) + "\n"
    return output_str

def format_detected_elements_tree_for_prompt(elements: Optional[List[Any]], indent_level: int = 1) -> str:
    if not elements: return f"{'  ' * indent_level}- None\n"
    indent = "  " * indent_level
    output_str = ""
    for el_data in elements: 
        line = f"{indent}- Type: {el_data.element_type}"
        if el_data.semantic_guess: line += f" (Semantic: {el_data.semantic_guess})"
        if el_data.text_content: line += f"\n{indent}  Content: \"{el_data.text_content.strip()[:70]}{'...' if len(el_data.text_content.strip()) > 70 else ''}\""
        if el_data.style_hints:
            hints_summary = [f"{sh.property}: {sh.value}" for sh in el_data.style_hints[:2]] 
            if hints_summary: line += f"\n{indent}  Styles: {'; '.join(hints_summary)}{'...' if len(el_data.style_hints) > 2 else ''}"
        output_str += line + "\n"
        if el_data.children:
            output_str += f"{indent}  Children:\n"
            output_str += format_detected_elements_tree_for_prompt(el_data.children, indent_level + 1)
    return output_str

async def call_openrouter_vision_api(image_bytes: bytes, image_filename: Optional[str]) -> RichImageAnalysisSchema:
    # ... (Keep your working call_openrouter_vision_api function from response #43) ...
    # This function seems to be working correctly now, returning parsable JSON.
    if not OPENROUTER_CONFIGURED_SUCCESSFULLY:
        raise HTTPException(status_code=503, detail="OpenRouter API is not configured.")
    openrouter_model_identifier = settings.OPENROUTER_MODEL_IDENTIFIER
    print(f"--- Using OpenRouter vision model: '{openrouter_model_identifier}' ---")
    img_width, img_height = None, None
    image_dimensions_json_part = '"width": "integer", "height": "integer"'
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img_width, img_height = img.width, img.height
        if img_width is not None and img_height is not None:
            image_dimensions_json_part = f'"width": {img_width}, "height": {img_height}'
    except Exception as img_err:
        print(f"Could not get image dimensions: {img_err}")
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    mime_type = "image/png"
    try:
        img_for_mime = Image.open(io.BytesIO(image_bytes))
        if img_for_mime.format == "JPEG": mime_type = "image/jpeg"
        elif img_for_mime.format == "WEBP": mime_type = "image/webp"
    except Exception: pass
    json_instruction_prompt = f"""Your task is to meticulously analyze the provided UI screenshot and return ONLY a valid JSON object. This JSON object MUST strictly adhere to the following Pydantic-style schema. Do NOT include any explanatory text, markdown backticks, or comments outside or inside the JSON structure.

Schema Definition:
{{
    "image_metadata": {{ "original_filename": "{image_filename or 'uploaded_image.png'}", "image_dimensions": {{ {image_dimensions_json_part} }}, "analysis_timestamp": "{datetime.datetime.now(datetime.timezone.utc).isoformat()}" }},
    "overall_analysis": {{ "page_title_guess": "string (Concise title)", "page_purpose_and_audience": "string", "dominant_theme": "string", "primary_layout_type": "string", "general_description": "string", "key_takeaways": ["string"] }},
    "navigation_elements": [ {{ "id": "string_id", "element_type": "string", "items": ["string"], "style_hints": "string" }} ],
    "layout_components": [ {{ "id": "string_id", "element_type": "string", "description": "string", "grid_details": "string" }} ],
    "content_sections": [ {{ "id": "string_id", "element_type": "string", "headline": "string", "text_elements": ["string"], "image_elements": ["string"] }} ],
    "interactive_controls": [ {{ "id": "string_id", "element_type": "string", "label_or_text": "string", "purpose": "string" }} ],
    "visual_style_guide": {{ "primary_colors": [{{ "hex": "string", "name": "string", "usage": "string" }}], "secondary_colors": [], "accent_colors": [], "neutral_colors": [], "primary_font_family": "string", "secondary_font_family": "string", "heading_typography": [{{ "level": "string", "font_size": "string", "font_weight": "string", "line_height": "string" }}], "body_typography": {{ "font_size": "string", "line_height": "string" }}, "spacing_density": "string", "component_spacing": "string", "corner_radius_style": "string", "shadow_style": "string", "iconography_style": "string" }},
    "detected_elements_tree": [ {{ "id": "string", "element_type": "string", "semantic_guess": "string", "text_content": "string", "bounding_box": {{ "x": 0, "y": 0, "width": 0, "height": 0 }}, "style_hints": [{{ "property": "string", "value": "string" }}], "interaction_notes": "string", "accessibility_notes": "string", "children": [] }} ]
}}
Return an empty list [] for array fields if no items apply. Return null for optional string/object fields if not applicable. No comments.
"""
    payload = { "model": openrouter_model_identifier, "messages": [{"role": "user", "content": [{"type": "text", "text": json_instruction_prompt}, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}]}], "max_tokens": 500000, "response_format": {"type": "json_object"}}
    headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "Content-Type": "application/json", "HTTP-Referer": settings.PROJECT_NAME, "X-Title": settings.PROJECT_NAME}
    raw_json_text_for_error_reporting = "AI response content not retrieved due to an early error."
    ai_data_dict_for_error_reporting = None
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{settings.OPENROUTER_BASE_URL}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        api_response_json = response.json()
        if not (choices := api_response_json.get("choices")) or not (message := choices[0].get("message")) or not (raw_json_text := message.get("content")):
            raw_json_text_for_error_reporting = str(api_response_json)
            raise ValueError("Unexpected response structure from OpenRouter vision model (choices/message/content path).")
        raw_json_text_for_error_reporting = raw_json_text 
        if isinstance(raw_json_text, str):
            raw_json_text = re.sub(r"//.*", "", raw_json_text)
            raw_json_text = raw_json_text.strip()
        if not raw_json_text:
            raise ValueError("AI returned empty content after stripping comments/whitespace.")
        ai_data_dict = json.loads(raw_json_text) 
        ai_data_dict_for_error_reporting = ai_data_dict 
        strict_analysis = RichImageAnalysisSchema.model_validate(ai_data_dict)
        return strict_analysis
    except httpx.HTTPStatusError as e: print(f"HTTP error calling OpenRouter Vision: {e.response.status_code} - {e.response.text}"); raise HTTPException(status_code=e.response.status_code, detail=f"OpenRouter Vision API Error: {e.response.text}")
    except json.JSONDecodeError as e: print(f"JSONDecodeError from Vision: {e}"); print(f"Raw text that failed JSON parsing: {raw_json_text_for_error_reporting}"); raise HTTPException(status_code=500, detail=f"AI Vision response was not valid JSON: {e.msg} at pos {e.pos}")
    except ValidationError as e: print(f"Pydantic ValidationError from Vision: {e}"); print(f"Data that failed Pydantic validation: {ai_data_dict_for_error_reporting}"); raise HTTPException(status_code=500, detail=f"AI Vision response schema error: {e.errors()}")
    except Exception as e: print(f"General error in vision call: {e}"); traceback.print_exc(); raise HTTPException(status_code=500, detail=f"Vision processing error: {str(e)}")


async def call_planner_llm(
    project_title: str,
    all_page_analyses_json_strings: List[str], 
    page_titles: List[str],
    overall_requirements: str
) -> str:
    # ... (Keep your existing call_planner_llm function from response #41) ...
    if not OPENROUTER_CONFIGURED_SUCCESSFULLY: 
        print("WARNING: Planner LLM (OpenRouter) not configured, returning basic planning.")
        return f"<development_planning>\n<error_in_planning>Planner LLM was not configured or failed.</error_in_planning>\n1. Project Structure: Basic Next.js structure.\n</development_planning>"
    planner_model_identifier = settings.OPENROUTER_PLANNER_MODEL_IDENTIFIER
    print(f"--- Calling Planner LLM: '{planner_model_identifier}' ---")
    planning_prompt_parts = [f"{overall_requirements}\n\n", f"<project_summary_title>\n{project_title}\n</project_summary_title>\n\n"]
    for i, analysis_json_str in enumerate(all_page_analyses_json_strings):
        planning_prompt_parts.append(f"--- DETAILED JSON ANALYSIS FOR PAGE: {page_titles[i]} ---\n{analysis_json_str}\n\n")
    planning_prompt_parts.append(f"""
Based on ALL the above page analyses (provided as structured JSON) and the overall project requirements, generate ONLY the content for a <development_planning> XML-style block.
This block MUST detail:
1.  A suggested Project Structure (detailed file/folder layout for a Next.js/React/Tailwind project, showing key components specific to EACH analyzed page, and shared components).
2.  A list of Key Features to implement across the entire application, derived from a holistic view of all pages.
3.  High-level suggestions for State Management if complex global state or interactivity spanning multiple pages is implied by the analyses.
4.  A comprehensive list of main Routes needed, including potential dynamic routes if apparent from page structures.
5.  A Component Architecture philosophy (e.g., atomic design principles, layout wrappers, core UI elements, feature-specific composites).
6.  Notes on Responsive Breakpoints and specific Tailwind CSS strategies for achieving responsiveness based on the analyzed layouts.
7.  Suggestions for data fetching or placeholder data if dynamic content is implied.

The plan should be coherent, actionable, and directly based on the provided structured analyses. Ensure the output is ONLY the content for the <development_planning> section, starting with "1. Project Structure..." and ending after all planning points. Do not include the <development_planning> tags themselves in your response text.
""")
    full_planning_prompt = "".join(planning_prompt_parts)
    payload = { "model": planner_model_identifier, "messages": [{"role": "user", "content": full_planning_prompt}], "max_tokens": 3500 }
    headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "Content-Type": "application/json", "HTTP-Referer": settings.PROJECT_NAME, "X-Title": settings.PROJECT_NAME}
    raw_planner_output_for_error = "Planner LLM did not produce output."
    try:
        async with httpx.AsyncClient(timeout=240.0) as client:
            response = await client.post(f"{settings.OPENROUTER_BASE_URL}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        api_response_json = response.json()
        if not (choices := api_response_json.get("choices")) or not (message := choices[0].get("message")) or not (dev_plan_text := message.get("content")):
            raise ValueError("Unexpected response structure from Planner LLM.")
        raw_planner_output_for_error = dev_plan_text
        print(f"--- Planner LLM Raw Output (first 500 chars): {dev_plan_text[:500]}... ---")
        return dev_plan_text 
    except Exception as e:
        print(f"Error during Planner LLM call: {e}")
        if isinstance(e, httpx.HTTPStatusError): print(f"Planner LLM HTTP Error Response: {e.response.text}")
        traceback.print_exc()
        return f"""<error_in_planning>Planner LLM failed: {str(e)}\nRaw output for debug (if any): {raw_planner_output_for_error[:300]}...</error_in_planning>"""

# --- CONSOLIDATED PROMPT GENERATION (CORRECTED) ---
async def generate_final_consolidated_prompt_with_planner(
    all_image_analyses_structured: List[Dict[str, Any]], 
    session_name: Optional[str]
) -> List[GeneratedPromptData]:
    if not all_image_analyses_structured:
        return [GeneratedPromptData(prompt_type="error_no_analysis", prompt_text="No image analyses were provided.")]
    
    overall_requirements_text = settings.OVERALL_PROJECT_REQUIREMENTS
    project_title_for_planner = session_name
    if not project_title_for_planner:
        first_page_analysis_obj = all_image_analyses_structured[0].get("analysis_output") if all_image_analyses_structured else None
        project_title_for_planner = "Multi-Page Web Application"
        if first_page_analysis_obj and first_page_analysis_obj.overall_analysis:
            project_title_for_planner = first_page_analysis_obj.overall_analysis.page_title_guess or project_title_for_planner
    
    image_analysis_blocks_for_final_prompt = []
    analysis_json_strings_for_planner = []
    page_titles_for_planner = []

    for i, image_data in enumerate(all_image_analyses_structured):
        title = image_data.get("title", f"Page {i+1}")
        page_titles_for_planner.append(title)
        analysis_obj: Optional[RichImageAnalysisSchema] = image_data.get("analysis_output")
        error_msg = image_data.get("error")
        current_page_analysis_text_block = f"--- ANALYSIS FOR PAGE: {title} ---\n"
        if error_msg or not analysis_obj:
            current_page_analysis_text_block += f"<image_analysis_error>\nAnalysis failed. Error: {error_msg or 'Unknown'}\n</image_analysis_error>\n\n"
            analysis_json_strings_for_planner.append(f'{{"error_analysing_page": "{title}", "detail": "{error_msg or "Unknown"}"}}')
        else:
            analysis_json_strings_for_planner.append(analysis_obj.model_dump_json(indent=2))
            current_page_analysis_text_block += "<image_analysis>\n"
            if analysis_obj.overall_analysis:
                current_page_analysis_text_block += f"  Page Overview: {analysis_obj.overall_analysis.general_description or 'N/A'}\n"
                current_page_analysis_text_block += f"  Dominant Theme: {analysis_obj.overall_analysis.dominant_theme or 'N/A'}\n"
                current_page_analysis_text_block += f"  Primary Layout: {analysis_obj.overall_analysis.primary_layout_type or 'N/A'}\n"
            if analysis_obj.navigation_elements: current_page_analysis_text_block += "  1. Navigation Elements:\n" + format_specific_elements_for_prompt(analysis_obj.navigation_elements, "", 2)
            if analysis_obj.layout_components: current_page_analysis_text_block += "  2. Layout Components:\n" + format_specific_elements_for_prompt(analysis_obj.layout_components, "", 2)
            if analysis_obj.content_sections: current_page_analysis_text_block += "  3. Content Sections:\n" + format_specific_elements_for_prompt(analysis_obj.content_sections, "", 2)
            if analysis_obj.interactive_controls: current_page_analysis_text_block += "  4. Interactive Controls:\n" + format_specific_elements_for_prompt(analysis_obj.interactive_controls, "", 2)
            if analysis_obj.visual_style_guide:
                vs = analysis_obj.visual_style_guide
                current_page_analysis_text_block += "  5. Visual Style Guide:\n"
                # Use a combined list for colors for simplicity in display
                all_colors = (vs.primary_colors or []) + (vs.secondary_colors or []) + (vs.accent_colors or []) + (vs.neutral_colors or [])
                if all_colors: colors_str = [f"{cp.hex or 'N/A'} ({cp.name or cp.usage_hint or 'N/A'})" for cp in all_colors]; current_page_analysis_text_block += f"     - Colors: {', '.join(colors_str)}\n"
                
                # CORRECTED TYPOGRAPHY HANDLING
                typos_str = []
                if vs.heading_typography:
                    for typo_dict in vs.heading_typography:
                        level, size, weight = typo_dict.get('level', ''), typo_dict.get('font_size', ''), typo_dict.get('font_weight', '')
                        typos_str.append(f"{level or 'Heading'}: {size or 'N/A'}, {weight or 'N/A'}")
                if vs.body_typography:
                    size, lh = vs.body_typography.get('font_size', ''), vs.body_typography.get('line_height', '')
                    typos_str.append(f"Body: Size {size or 'N/A'}, Line Height {lh or 'N/A'}")
                if typos_str:
                    current_page_analysis_text_block += f"     - Typography: {'; '.join(typos_str)}\n"

                current_page_analysis_text_block += f"     - Spacing: {vs.spacing_density or 'N/A'}\n"
                current_page_analysis_text_block += f"     - Component Spacing: {vs.component_spacing or 'N/A'}\n"
                current_page_analysis_text_block += f"     - Corners: {vs.corner_radius_style or 'N/A'}\n"
                current_page_analysis_text_block += f"     - Shadows: {vs.shadow_style or 'N/A'}\n"
                current_page_analysis_text_block += f"     - Iconography: {vs.iconography_style or 'N/A'}\n"
            
            if analysis_obj.detected_elements_tree:
                current_page_analysis_text_block += "  6. Detailed Element Tree:\n" + format_detected_elements_tree_for_prompt(analysis_obj.detected_elements_tree, 2)
            
            current_page_analysis_text_block += "</image_analysis>\n\n"
        image_analysis_blocks_for_final_prompt.append(current_page_analysis_text_block)

    development_plan_str = await call_planner_llm(project_title=project_title_for_planner, all_page_analyses_json_strings=analysis_json_strings_for_planner, page_titles=page_titles_for_planner, overall_requirements=overall_requirements_text)
    final_prompt_text = overall_requirements_text + "\n\n"; final_prompt_text += f"<project_summary_title>\n{project_title_for_planner}\n</project_summary_title>\n\n"; final_prompt_text += "".join(image_analysis_blocks_for_final_prompt); final_prompt_text += f"<development_planning>\n{development_plan_str}\n</development_planning>"
    return [GeneratedPromptData(prompt_type="ultra_detailed_multi_page_app_with_ai_planning", prompt_text=final_prompt_text.strip())]

# --- Main API Endpoint ---
@router.post("/analyze-image", response_model=PromptAnalysisResponse)
async def analyze_image_endpoint(request: Request, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    # ... (This logic remains the same from your pasted code, it calls the updated helpers) ...
    form_data = await request.form()
    session_name_form: Optional[str] = form_data.get("session_name")
    image_files_form: List[UploadFile] = form_data.getlist("image_files")
    image_titles_form: List[str] = form_data.getlist("image_titles")
    print(f"--- analyze_image_endpoint by {current_user.email}, {len(image_files_form)} files, {len(image_titles_form)} titles ---")
    if not image_files_form or len(image_files_form) != len(image_titles_form): raise HTTPException(status_code=400, detail="Mismatch: images and titles count.")
    
    all_individual_analyses_for_db = []; prompt_generation_input = []
    for i, image_file_obj in enumerate(image_files_form):
        title = image_titles_form[i]; original_filename = image_file_obj.filename
        current_image_analysis_obj: Optional[RichImageAnalysisSchema] = None; analysis_dict_for_db = None; error_message_for_prompt_gen = None
        if not image_file_obj.content_type or not image_file_obj.content_type.startswith("image/"):
            print(f"--- Skipped non-image file: {original_filename} ---"); analysis_dict_for_db = {"error": f"Invalid file type: {original_filename}"}; error_message_for_prompt_gen = f"Invalid file type"
        else:
            image_bytes = await image_file_obj.read(); print(f"--- Processing image {i+1}: {original_filename}, Title: {title} ---")
            try:
                if settings.ACTIVE_AI_PROVIDER == "OPENROUTER" and OPENROUTER_CONFIGURED_SUCCESSFULLY:
                    current_image_analysis_obj = await call_openrouter_vision_api(image_bytes, original_filename)
                elif settings.ACTIVE_AI_PROVIDER == "GEMINI" and GEMINI_CONFIGURED_SUCCESSFULLY:
                    current_image_analysis_obj = await call_gemini_vision_api(image_bytes, original_filename) # Needs similar Rich Schema update
                else: raise HTTPException(status_code=503, detail=f"No active AI provider: {settings.ACTIVE_AI_PROVIDER}")
                
                analysis_dict_for_db = current_image_analysis_obj.model_dump() if current_image_analysis_obj else {"error": "AI vision analysis returned None."}
                if not current_image_analysis_obj: error_message_for_prompt_gen = "AI vision analysis returned None."

            except Exception as e_vision: 
                error_message_for_prompt_gen = str(e_vision)
                analysis_dict_for_db = {"error": f"Vision AI call failed: {error_message_for_prompt_gen}"}
                print(f"--- Error Vision AI for {original_filename}: {e_vision} ---")
                if not isinstance(e_vision, HTTPException): # Don't print traceback for our own HTTPExceptions
                    traceback.print_exc()       
        
        all_individual_analyses_for_db.append({"title": title, "original_filename": original_filename, "analysis_output_json": analysis_dict_for_db})
        prompt_generation_input.append({"title": title, "analysis_output": current_image_analysis_obj, "error": error_message_for_prompt_gen})

    final_prompts_for_ui = await generate_final_consolidated_prompt_with_planner(prompt_generation_input, session_name_form)
    session_create_data = PromptSessionCreate(session_name=session_name_form or f"Multi-Page Analysis - {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')}", image_filename=image_files_form[0].filename if image_files_form else None)
    db_final_prompts_to_create = [GeneratedPromptCreate(prompt_type=p.prompt_type, prompt_text=p.prompt_text) for p in final_prompts_for_ui]
    created_db_session = crud_prompt_session.create_with_images_and_final_prompt(db=db, session_obj_in=session_create_data, image_analyses=all_individual_analyses_for_db, final_prompts_obj_in=db_final_prompts_to_create, owner_id=current_user.id)
    print(f"--- Saved PromptSession ID: {created_db_session.id} ---")
    return PromptAnalysisResponse(id=created_db_session.id, session_name=created_db_session.session_name, image_filename=created_db_session.image_filename, prompts=final_prompts_for_ui)

# --- GET HISTORY ENDPOINT ---
@router.get("/history", response_model=List[PromptSessionInDB], name="prompts:get_history")
async def get_prompt_history(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user), skip: int = 0, limit: int = 100):
    print(f"--- Getting history for user ID: {current_user.id} ---")
    history_sessions = crud_prompt_session.get_multi_by_owner(db=db, owner_id=current_user.id, skip=skip, limit=limit)
    return history_sessions