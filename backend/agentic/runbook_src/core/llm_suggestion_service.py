"""
LLM Suggestion Service - Generates error registry suggestions for low confidence matches

When no high/medium confidence match is found, this service uses LLM to:
1. Analyze the error message and available actions
2. Suggest new error registry entries using existing actions
3. Provide reasoning for the suggestions
"""

import logging
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ActionSuggestion(BaseModel):
    """Suggested action for the error"""
    action_id: str = Field(description="The action ID to use")
    reason: str = Field(description="Why this action is appropriate for this error")


class ErrorRegistrySuggestion(BaseModel):
    """Suggestion for a new error registry entry"""
    error_name: str = Field(description="Suggested name for the error type (e.g., 'DatabaseConnectionPoolExhausted')")
    description: str = Field(description="Clear description of when this error occurs")
    suggested_actions: List[ActionSuggestion] = Field(description="Actions to associate with this error")
    confidence_reasoning: str = Field(description="Why these actions are appropriate for this error")
    feasible: bool = Field(description="Whether the suggestion is feasible with existing actions")
    additional_actions_needed: Optional[str] = Field(
        default=None,
        description="If not feasible, what actions need to be implemented (in natural language)"
    )


class LLMSuggestionService:
    """Service that uses LLM to suggest error registry entries"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the suggestion service
        
        Args:
            api_key: Google AI API key (defaults to GOOGLE_API_KEY or GEMINI_API_KEY from .env)
            model: Model to use (defaults to LLM_MODEL from .env)
        """
        api_key = api_key or os.getenv('GOOGLE_API_KEY')
        model = model or os.getenv('LLM_MODEL', 'gemini-2.5-flash')
        
        if not api_key:
            raise ValueError(
                "Google AI API key not found. Set GOOGLE_API_KEY in .env file or pass api_key parameter."
            )
        
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.3,
            max_tokens=2048,
            timeout=60,
            max_retries=2
        )
    
    async def suggest_error_registry_entry(
        self,
        error_message: str,
        existing_errors: List[Dict[str, Any]],
        available_actions: List[Dict[str, Any]]
    ) -> ErrorRegistrySuggestion:
        """
        Suggest a new error registry entry based on the error message and available resources
        
        Args:
            error_message: The error message that had low confidence
            existing_errors: List of existing error definitions for context
            available_actions: List of available actions with their descriptions
            
        Returns:
            ErrorRegistrySuggestion with recommendations
        """
        # Format existing errors for context
        errors_context = "\n".join([
            f"- {err.get('error', 'Unknown')}: {err.get('description', 'No description')}"
            for err in existing_errors[:10]  # Limit to avoid token overflow
        ])
        
        # Format available actions
        actions_context = "\n".join([
            f"- {act.get('action_id', 'unknown')} ({act.get('method', 'unknown')}): "
            f"{act.get('definition', 'No description')} "
            f"[Risk: {act.get('risk_level', 'unknown')}, "
            f"Requires Approval: {act.get('requires_approval', False)}]"
            for act in available_actions
        ])
        
        prompt = f"""You are an expert system administrator analyzing an error message that doesn't match any existing error definitions well.

ERROR MESSAGE: "{error_message}"

EXISTING ERROR DEFINITIONS:
{errors_context}

AVAILABLE ACTIONS:
{actions_context}

TASK:
1. Analyze the error message and determine what type of issue it represents
2. Suggest a new error registry entry name (use PascalCase like "DatabaseConnectionTimeout")
3. Write a clear description of when this error occurs
4. Select appropriate existing actions that could remediate this error
5. Explain why each action is suitable
6. Determine if the suggestion is feasible with existing actions

If existing actions are sufficient, set feasible=true and provide the mapping.
If new actions are needed, set feasible=false and describe what actions should be implemented in natural language.

GUIDELINES:
- Choose actions that logically address the root cause
- Consider action risk levels and approval requirements
- Prioritize diagnostic actions before destructive ones
- Be specific about why each action helps
- If no existing actions fit, clearly explain what's missing"""

        try:
            # Use structured output
            structured_llm = self.llm.with_structured_output(ErrorRegistrySuggestion)
            suggestion = await structured_llm.ainvoke(prompt)
            
            # Handle case where LLM returns None
            if suggestion is None:
                logger.warning("LLM returned None, using fallback")
                raise ValueError("LLM returned None")
            
            logger.info(f"Generated suggestion for error: {error_message}")
            logger.info(f"Feasible with existing actions: {suggestion.feasible}")
            
            return suggestion
            
        except Exception as e:
            logger.error(f"Failed to generate suggestion: {e}", exc_info=True)
            # Return a fallback suggestion
            return ErrorRegistrySuggestion(
                error_name="UnknownError",
                description=f"Error message: {error_message}",
                suggested_actions=[],
                confidence_reasoning="Failed to generate suggestion due to LLM error",
                feasible=False,
                additional_actions_needed=(
                    "Unable to generate suggestions. Please manually create error definition "
                    "and implement appropriate remediation actions."
                )
            )
