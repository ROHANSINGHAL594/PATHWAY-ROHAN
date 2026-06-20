"""
Chart Generation Agent: Generates Mermaid chart syntax from chart data
LLM Call #2
"""

from typing import Dict, Any, List, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import json


class ChartItem(BaseModel):
    """Individual chart with metadata"""
    title: str = Field(description="Chart title")
    mermaid_syntax: str = Field(description="Valid Mermaid diagram syntax")
    chart_type: str = Field(description="Type of chart: line, flowchart, timeline, bar")


class ChartOutput(BaseModel):
    """Structured chart output"""
    charts: List[ChartItem] = Field(description="List of charts with mermaid syntax and metadata")


class ChartGenAgent:
    """
    Generates Mermaid chart syntax from structured chart data.
    """
    
    def __init__(self, llm: Union[BaseChatModel, None] = None, google_api_key: str = None, model_name: str = None):
        """
        Initialize ChartGenAgent with either an LLM instance or API credentials.
        
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
                temperature=0.1
            )
        else:
            raise ValueError(
                "Either provide 'llm' instance or both 'google_api_key' and 'model_name'"
            )
        
        self.structured_llm = self.llm.with_structured_output(ChartOutput)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a data visualization expert specializing in Mermaid diagrams for operational reports.

CRITICAL RULES - FOLLOW EXACTLY:
1. Create span topology flowcharts showing error propagation through the system
2. ABSOLUTELY NO STYLING - no "style" lines, no colors, no fill, no stroke
3. Use subgraph(s) labeled "⚠︎AFFECTED NODE(S)" to highlight affected nodes
4. Show ALL nodes and edges from the span data
5. Create separate subgraphs for affected nodes that are not connected
6. Keep it simple - just nodes, arrows, and subgraph(s) for affected nodes

EXAMPLE OF CORRECT OUTPUT (copy this pattern exactly):
```
graph TD
    N1[api_gateway] --> N2[auth_service]
    N2 --> N3[user_service]
    N3 --> N4[database_query]
    N3 --> N5[cache_lookup]
    N1 --> N6[payment_service]
    N6 --> N7[payment_processor]
    
    subgraph "⚠︎AFFECTED NODE(S)"
        N1
        N4
    end
```

IF affected nodes are disconnected, create MULTIPLE subgraphs:
```
graph TD
    N1[api_gateway] --> N2[auth_service]
    N5[email_service] --> N6[smtp_server]
    
    subgraph "⚠︎AFFECTED NODE(S)"
        N1
    end
    
    subgraph "⚠︎AFFECTED NODE(S) "
        N6
    end
```

FORBIDDEN - DO NOT INCLUDE:
- style commands (e.g., "style N1 fill:#f9f")
- color specifications
- stroke specifications
- fill specifications
- Any line starting with "style"
- classDef commands
- class assignments

Guidelines:
- Node naming: Use N{{node_id}} as the node identifier (e.g., N1, N2, N3)
- Node labels: Use square brackets with the node name [node_name]
- Edges: Use --> to connect nodes (e.g., N1 --> N2)
- Affected nodes: Place affected node identifiers inside subgraph(s) labeled "⚠︎AFFECTED NODE(S)"
- Use graph TD for top-down layout
- All nodes from span_data must be included in the diagram
- All edges from span_data must be included as arrows"""),
            ("user", """Generate Mermaid chart syntax from this span topology data:

{chart_data}

The span_data contains:
- nodes: List of all nodes with node_id and name
- edges: List of connections between nodes (source -> target)
- affected_nodes: List of node_ids that should be highlighted in subgraph(s)

For the chart, provide:
1. title: "Span Topology - Error Propagation"
2. mermaid_syntax: Valid Mermaid diagram code showing ALL nodes and edges with affected nodes in subgraph(s)
3. chart_type: "flowchart"

Return structured output with the chart.""")
        ])
        
        self.chain = self.prompt | self.structured_llm
    
    def generate(self, chart_data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Generate Mermaid charts from chart data.
        
        Args:
            chart_data: List of chart data structures
            
        Returns:
            List of charts with Mermaid syntax
        """
        result = self.chain.invoke({
            "chart_data": json.dumps(chart_data, indent=2)
        })
        
        # Convert Pydantic models to dicts
        charts = []
        for chart in result.charts:
            charts.append({
                "title": chart.title,
                "mermaid_syntax": chart.mermaid_syntax,
                "chart_type": chart.chart_type
            })
        
        return charts
