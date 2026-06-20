"""
Planner Agent: Analyzes diagnostic inputs and creates report outline
LLM Call #1
"""

from typing import Dict, Any, List, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import json


class ReportPlan(BaseModel):
    """Structured report plan output"""
    executive_summary_points: List[str] = Field(description="3-5 key points for executive summary")
    sections: List[Dict[str, str]] = Field(
        description="List of report sections as array of objects, each with 'title' and 'focus' keys. Example: [{{title: Introduction, focus: Overview}}, {{title: Analysis, focus: Root cause}}]"
    )
    critical_findings: List[str] = Field(description="Critical issues requiring immediate attention")
    chart_requirements: List[str] = Field(description="Charts needed to visualize the incident")
    estimated_severity: str = Field(description="Incident severity: critical, high, medium, low")
    target_audience: str = Field(description="Primary audience: ops_manager, engineering_team, executive")


class PlannerAgent:
    """
    Analyzes diagnostic inputs and creates structured report outline.
    """
    
    def __init__(self, llm: Union[BaseChatModel, None] = None, google_api_key: str = None, model_name: str = None):
        """
        Initialize PlannerAgent with either an LLM instance or API credentials.
        
        Args:
            llm: Pre-configured LLM instance from factory (preferred)
            google_api_key: Google API key (backward compatibility)
            model_name: Model name (backward compatibility)
        """
        if llm is not None:
            self.llm = llm
        elif google_api_key and model_name:
            # Backward compatibility: create LLM from API key
            self.llm = ChatGoogleGenerativeAI(
                google_api_key=google_api_key,
                model=model_name,
                temperature=0.3
            )
        else:
            raise ValueError(
                "Either provide 'llm' instance or both 'google_api_key' and 'model_name'"
            )
        
        # Create structured output LLM
        self.structured_llm = self.llm.with_structured_output(ReportPlan)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior DevOps analyst at a fintech platform. Your role is to analyze diagnostic data and create a structured report plan for Ops Managers.

Your responsibilities:
1. Review the RCA output, metrics, news feed, and data streams
2. Identify critical findings and their business impact
3. Create a logical report structure
4. Determine what charts would best visualize the incident
5. Assess severity and target audience

Guidelines:
- Focus on actionable insights for Ops Managers
- Prioritize business impact over technical details
- Keep executive summary concise (3-5 points)
- Ensure report structure flows logically
- Consider both immediate and long-term implications

IMPORTANT - Output Format:
- sections MUST be an array of objects, each with "title" and "focus" keys
- Example: [{{"title": "Introduction", "focus": "Incident overview and timeline"}}, {{"title": "Root Cause Analysis", "focus": "Detailed analysis"}}]
- DO NOT use a single object with section names as keys

For chart_requirements:
- ALWAYS request a "Span Topology Diagram" to visualize the error trace through the system
- The topology diagram will show all nodes/services with affected nodes highlighted
- This is the PRIMARY chart type - it shows how the error propagated through the system
- Example chart requirement: "Span topology flowchart showing error propagation with affected nodes highlighted"
- All metric changes should also be conveyed through emphasized text and data tables
- Keep chart_requirements focused on the span topology visualization"""),
            ("user", """Analyze this diagnostic data from telemetry analysis and create a report plan:

**RCA Output:**
{rca_output}

**Live Data Stream (30-minute window):**
{live_data_stream}

Create a comprehensive report plan based on the RCA findings from telemetry data.""")
        ])
        
        self.chain = self.prompt | self.structured_llm
    
    def plan(self, diagnostic_data: Dict[str, Any]) -> ReportPlan:
        """
        Create report plan from diagnostic data.
        
        Args:
            diagnostic_data: Complete diagnostic inputs
            
        Returns:
            Structured ReportPlan object
        """
        result = self.chain.invoke({
            "rca_output": json.dumps(diagnostic_data.get("rca_output", {}), indent=2),
            "external_news": json.dumps(diagnostic_data.get("external_news", []), indent=2),
            "live_data_stream": json.dumps(diagnostic_data.get("live_data_stream", {}), indent=2)
        })
        
        return result
