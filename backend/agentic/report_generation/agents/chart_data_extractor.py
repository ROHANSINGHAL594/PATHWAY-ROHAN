"""
Chart Data Extractor: Extracts span topology data for diagram generation
NO LLM - Pure data transformation
"""

from typing import Dict, Any, List


class ChartDataExtractor:
    """
    Extracts span topology data from RCA output for mermaid diagram generation.
    Transforms span data into chart-ready format for ChartGenAgent.
    """
    
    def __init__(self):
        pass
    
    def extract(self, diagnostic_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract span topology data from RCA output for chart generation.
        
        Args:
            diagnostic_data: Complete diagnostic inputs including rca_output with span_data
            
        Returns:
            List with one chart data object containing span topology
        """
        rca_output = diagnostic_data.get("rca_output", {})
        span_data = rca_output.get("span_data", {})
        
        # If no span data, return empty list
        if not span_data or not span_data.get("nodes"):
            return []
        
        # Return span data as chart data
        return [
            {
                "chart_type": "span_topology",
                "title": "Span Topology - Error Propagation",
                "span_data": span_data
            }
        ]
