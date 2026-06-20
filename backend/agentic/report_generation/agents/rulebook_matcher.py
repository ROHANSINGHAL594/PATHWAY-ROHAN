"""
Rulebook Matcher: Rule-based matching of incidents to operational guidelines
(no llm call just fuzzy matching)
"""

from typing import Dict, Any, List


class RulebookMatcher:
    """
    Matches incident characteristics to relevant rulebook entries.
    Pure rule-based logic - no LLM calls.
    """
    
    def __init__(self):
        pass
    
    def match(self, diagnostic_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find relevant rulebook entries based on RCA and metrics.
        
        Args:
            diagnostic_data: Complete diagnostic inputs
            
        Returns:
            List of matched rules with relevance scores
        """
        rulebook = diagnostic_data.get("rulebook", [])
        rca = diagnostic_data.get("rca_output", {})
        
        # Extract incident characteristics from RCAAnalysisOutput schema
        affected_services = rca.get("affected_services", [])
        affected_node = affected_services[0] if affected_services else ""  # Primary service
        root_cause = rca.get("root_cause", "").lower()  # Technical root cause
        narrative = rca.get("narrative", "").lower()  # Narrative explanation
        
        # Extract key symptoms from error citations (new structure)
        error_messages = [cite.get("message", "").lower() for cite in rca.get("error_citations", [])]
        
        severity = rca.get("severity", "").lower()
        
        matched_rules = []
        
        for rule in rulebook:
            relevance_score = 0
            match_reasons = []
            
            rule_issue_type = rule.get("issue_type", "").lower()
            rule_component = rule.get("affected_component", "").lower()
            rule_root_cause = rule.get("root_cause", "").lower()
            rule_symptoms = [s.lower() for s in rule.get("identifiable_symptoms", [])]
            
            # Match affected component/node
            if affected_node and affected_node.lower() in rule_component:
                relevance_score += 40
                match_reasons.append(f"Affected node matches: {rule.get('affected_component')}")
            
            # Match root cause (check both root_cause field and narrative)
            if root_cause and any(keyword in root_cause.lower() for keyword in rule_root_cause.split()):
                relevance_score += 35
                match_reasons.append(f"Root cause matches: {rule.get('root_cause')[:50]}...")
            elif narrative and any(keyword in narrative.lower() for keyword in ["memory", "gc", "garbage collection", "deployment"]):
                if any(keyword in rule_root_cause for keyword in ["memory", "gc", "garbage", "deployment"]):
                    relevance_score += 30
                    match_reasons.append(f"Root cause keywords match from narrative")
            
            # Match symptoms from error messages
            for error_msg in error_messages:
                error_msg_lower = error_msg.lower()
                for symptom in rule_symptoms:
                    # Check if symptom keywords appear in error messages
                    symptom_keywords = [k for k in symptom.split() if len(k) > 3]
                    if any(keyword in error_msg_lower for keyword in symptom_keywords):
                        relevance_score += 15
                        match_reasons.append(f"Error message matches symptom: {symptom[:40]}...")
                        break
            
            # Match issue type in narrative or root cause
            if narrative and rule_issue_type in narrative.lower():
                relevance_score += 20
                match_reasons.append(f"Issue type matches in narrative: {rule.get('issue_type')}")
            elif root_cause and rule_issue_type in root_cause.lower():
                relevance_score += 20
                match_reasons.append(f"Issue type matches in root cause: {rule.get('issue_type')}")
            
            # Match severity
            if severity and "critical" in severity.lower() and "latency" in rule_issue_type:
                relevance_score += 10
                match_reasons.append(f"Critical latency issue match")
            
            # Add rule if relevant
            if relevance_score > 0:
                matched_rules.append({
                    "rule": rule,
                    "relevance_score": relevance_score,
                    "match_reasons": match_reasons
                })
        
        # Sort by relevance
        matched_rules.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Return top 3 most relevant rules
        return matched_rules[:3]
