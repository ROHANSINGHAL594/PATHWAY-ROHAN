"""
Weekly Summarizer Agent: Generates weekly summary reports
LLM Call for weekly report generation
"""

from typing import Dict, Any, List, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
import json


class WeeklySummarizerAgent:
    """
    Generates comprehensive weekly summary reports from incident history and news.
    """
    
    def __init__(self, llm: Union[BaseChatModel, None] = None, google_api_key: str = None, model_name: str = None):
        """
        Initialize WeeklySummarizerAgent with either an LLM instance or API credentials.
        
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
                temperature=0.4
            )
        else:
            raise ValueError(
                "Either provide 'llm' instance or both 'google_api_key' and 'model_name'"
            )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior DevOps analyst preparing weekly operational summary reports for engineering leadership.

Your responsibilities:
1. Analyze incidents from the past week and identify trends
2. Synthesize external news about industry outages and risks
3. Provide actionable recommendations for the upcoming week
4. Maintain professional tone suitable for executive audiences

Report Structure Required:

# Weekly Operational Report
**Report Period**: [Start Date] to [End Date]
**Generated**: [Timestamp]

## Executive Summary
- Brief 3-5 sentence overview of the week
- Highlight most critical incidents and trends
- Key takeaways for leadership

## Incident Analysis
### Overview
- Total incidents: [N]
- Severity breakdown: [Critical: X, High: Y, etc.]
- Most affected components
- Incident trends compared to previous weeks (if data available)

### Critical Incidents
For each critical incident:
- **Incident ID**: [ID]
- **Timestamp**: [When it occurred]
- **Affected Component**: [Node/Service]
- **Root Cause**: [Summary of what caused it]
- **Impact**: [Brief description of business/technical impact]
- **Resolution**: [How it was fixed - list key steps]

### Patterns and Trends
- Identify recurring issues (e.g., "3 memory leak incidents in transformation nodes")
- Common root causes across incidents
- Time-of-day patterns
- Component reliability trends
- Resolution effectiveness

## Top Affected Components
List the most problematic components with:
- Component name
- Number of incidents
- Primary issues
- Recommended actions

## Recommendations for Next Week
Provide 5-10 actionable recommendations:
1. **Immediate Actions**: Critical fixes needed
2. **Monitoring**: What to watch closely
3. **Preventive Measures**: How to avoid repeat incidents
4. **Infrastructure Improvements**: Long-term suggestions
5. **Team Actions**: Process or policy changes

## Pipeline Health Overview
Provide a brief assessment of overall system health and stability trends.

Guidelines:
- Use professional, concise language
- Focus on actionable insights
- Quantify where possible (percentages, counts, times)
- Highlight both problems and improvements
- Include Mermaid diagrams for pipeline topology if relevant
- DO NOT hallucinate data - only use information provided
- If no incidents occurred, focus on "all clear" message with preventive monitoring"""),
            ("user", """Generate a weekly summary report based on this data:

**Incident Reports (Last 7 Days):**
{incident_reports}

**Report Statistics:**
{report_statistics}

**External News:**
{external_news}

**Date Range**: {start_date} to {end_date}

Generate a comprehensive weekly report following the structure specified in your system prompt. Focus on telemetry-based analysis of the affected services.""")
        ])
        
        self.chain = self.prompt | self.llm
    
    def generate_weekly_summary(
        self,
        incident_reports: List[Dict[str, Any]],
        report_statistics: Dict[str, Any],
        external_news: List[Dict[str, Any]],
        start_date: str,
        end_date: str
    ) -> str:
        """
        Generate weekly summary report from telemetry-based incident analysis.
        
        Args:
            incident_reports: List of incident metadata from the week
            report_statistics: Statistics calculated from incidents
            external_news: News articles from GNews API
            start_date: Start date of report period
            end_date: End date of report period
            
        Returns:
            Complete weekly report as Markdown string
        """
        # Incident reports now include full data (root_cause, resolution_steps, etc.)
        # No need to reformat - pass them directly
        
        result = self.chain.invoke({
            "incident_reports": json.dumps(incident_reports, indent=2),
            "report_statistics": json.dumps(report_statistics, indent=2),
            "external_news": json.dumps(external_news, indent=2),
            "start_date": start_date,
            "end_date": end_date
        })
        
        return result.content
    
    def generate_all_clear_report(
        self,
        external_news: List[Dict[str, Any]],
        start_date: str,
        end_date: str
    ) -> str:
        """
        Generate "all clear" report when no incidents occurred.
        
        Args:
            external_news: News articles from GNews API
            start_date: Start date of report period
            end_date: End date of report period
            
        Returns:
            All-clear weekly report as Markdown string
        """
        all_clear_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior DevOps analyst preparing weekly operational summary reports.

This week had ZERO incidents - generate a positive "all clear" report.

Report Structure:

# Weekly Operational Report
**Report Period**: {start_date} to {end_date}
**Generated**: [Timestamp]
**Status**: All Systems Operational

## Executive Summary
Positive summary highlighting:
- Zero incidents this week
- System stability and reliability
- Continued monitoring in place

## System Health Status
Brief overview showing all monitored services operational based on telemetry data.

## External Threat Landscape
### Industry News
Summarize relevant external news that could affect future operations:
- Cloud provider incidents
- Security vulnerabilities
- Industry trends to monitor

### Monitoring Recommendations
What to watch for based on external news and industry trends.

## Preventive Actions for Next Week
Even with zero incidents, provide 3-5 recommendations:
- Continue monitoring key metrics
- Proactive maintenance suggestions
- Capacity planning considerations

Guidelines:
- Keep it brief and positive
- Focus on maintaining stability
- Include relevant external news
- DO NOT fabricate metrics or incidents
- NO diagrams or visualizations - text and tables only"""),
            ("user", """Generate an "all clear" weekly report:

**External News:**
{external_news}

**Date Range**: {start_date} to {end_date}

No incidents occurred this week. Generate a positive report acknowledging this and focusing on preventive monitoring.""")
        ])
        
        chain = all_clear_prompt | self.llm
        
        result = chain.invoke({
            "external_news": json.dumps(external_news, indent=2),
            "start_date": start_date,
            "end_date": end_date
        })
        
        return result.content
