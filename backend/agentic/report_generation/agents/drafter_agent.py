"""
Drafter Agent: Writes the final comprehensive report
LLM Call #3
"""

from typing import Dict, Any, List, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
import json


class DrafterAgent:
    """
    Writes the final comprehensive report based on all gathered information.
    """
    
    def __init__(self, llm: Union[BaseChatModel, None] = None, google_api_key: str = None, model_name: str = None):
        """
        Initialize DrafterAgent with either an LLM instance or API credentials.
        
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
                temperature=0.5
            )
        else:
            raise ValueError(
                "Either provide 'llm' instance or both 'google_api_key' and 'model_name'"
            )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior operations analyst at Laminar, writing reports for Ops Managers. Your reports are known for being clear, actionable, and comprehensive.

Your writing guidelines:
1. **Audience**: Write for Ops Managers who need to make quick decisions
2. **Tone**: Professional, direct, data-driven
3. **Structure**: Follow the provided outline exactly
4. **Length**: Minimum 2000 words, with detailed analysis
5. **Focus**: Balance technical accuracy with business impact

Report sections to include:
- **Executive Summary**: 3-5 bullet points highlighting key findings (include brief mention of financial impact)
- **Incident Overview**: What happened, when, and impact
- **Root Cause Analysis**: Detailed RCA findings with evidence from error_citations
- **Technical Analysis**: Deep dive with error log citations in a table
- **Affected Services**: List all affected services (from affected_services field)
- **Span Topology Diagram**: Include the mermaid diagram showing error propagation (from charts)
- **Impact Assessment**: Business and technical impact quantification
- **Remediation Actions**: Immediate fixes and long-term improvements
- **Recommendations**: Strategic recommendations based on matched rules

RCA Output Structure (use these fields):
- severity: Impact severity (CRITICAL, HIGH, MEDIUM, LOW)
- affected_services: List of services affected (primary service first)
- narrative: Clear explanation of what happened and why
- error_citations: Specific log entries with timestamp, service, and message
- root_cause: Technical root cause (specific and actionable)
- financial_impact: Estimated financial impact with estimated_loss_usd, affected_transactions, duration_minutes
- span_data: Topology showing how the error propagated (visualized in charts)

Writing best practices:
- Start each section with a clear topic sentence
- Reference the narrative field for incident overview
- Use error_citations to create the error log table with columns: | Timestamp | Service | Message |
- List all affected_services and their roles in the incident
- Quote the root_cause directly in the Root Cause Analysis section
- **IMPORTANT**: Mention financial_impact BRIEFLY in executive summary with disclaimer: "(Note: Financial impact values are currently hardcoded estimates for demo purposes)"
- Include the span topology diagram from charts to visualize error propagation
- Quantify impact wherever possible based on telemetry data
- Provide actionable next steps
- Use clear subheadings for readability

Data presentation:
- Present data in tables and highlighted text
- For error logs: create a markdown table from error_citations
- Use tables for metric comparisons (before/after values)
- Highlight key metrics and thresholds in bold text
- Include the span topology mermaid diagram in a dedicated section
- The chart will show affected nodes in subgraph(s) labeled "⚠︎AFFECTED NODE(S)"
- CRITICAL: DO NOT add any "style" commands after the chart - use the chart exactly as provided
- For metric changes: write as clear text paragraphs
- Keep table formatting clean with properly aligned pipes
- NO time-series flowcharts - convey trends through text only
- NO emoji (except in mermaid diagrams as provided), NO colors, NO style commands in the final output"""),
            ("user", """Write a comprehensive operational report based on this telemetry analysis:

**Report Plan:**
{report_plan}

**Diagnostic Data:**
RCA Output: {rca_output}
External News: {external_news}
Live Data Stream (30-minute window): {live_data_stream}

**Matched Rules:**
{matched_rules}

**Charts (Span Topology):**
{charts}

Write a complete, professional report that is at least 2000 words. Follow the report plan structure. 
Include the span topology diagram to visualize error propagation.
Mention the financial_impact briefly in the executive summary with the disclaimer about hardcoded demo values.
Present other data in tables and text format.""")
        ])
        
        self.chain = self.prompt | self.llm
    
    def draft(
        self,
        report_plan: Dict[str, Any],
        diagnostic_data: Dict[str, Any],
        matched_rules: List[Dict[str, Any]],
        charts: List[Dict[str, str]]
    ) -> str:
        """
        Write the final comprehensive report.
        
        Args:
            report_plan: Structured plan from PlannerAgent
            diagnostic_data: Complete diagnostic inputs
            matched_rules: Matched rules from RulebookMatcher
            charts: Generated charts from ChartGenAgent
            
        Returns:
            Complete report as Markdown string
        """
        result = self.chain.invoke({
            "report_plan": json.dumps(report_plan, indent=2),
            "rca_output": json.dumps(diagnostic_data.get("rca_output", {}), indent=2),
            "external_news": json.dumps(diagnostic_data.get("external_news", []), indent=2),
            "live_data_stream": json.dumps(diagnostic_data.get("live_data_stream", {}), indent=2),
            "matched_rules": json.dumps(matched_rules, indent=2),
            "charts": json.dumps(charts, indent=2)
        })
        
        return result.content
