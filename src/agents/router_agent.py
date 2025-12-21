"""Router Agent for team assignment."""
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from typing import Dict, Any
import re


class RouterAgent:
    """Agent specialized in routing inquiries to appropriate teams."""
    
    TEAMS = {
        "platform": ["kubernetes", "k8s", "pod", "deployment", "container", "docker", "scaling", "orchestration"],
        "devops": ["ci/cd", "pipeline", "jenkins", "gitlab", "monitoring", "prometheus", "grafana", "alert", "automation"],
        "database": ["postgres", "postgresql", "mysql", "database", "db", "sql", "connection", "query", "performance"],
        "security": ["ssl", "tls", "certificate", "auth", "access", "permission", "vulnerability", "compliance", "firewall"],
        "network": ["dns", "load balancer", "nginx", "connectivity", "network", "routing", "port", "ip"]
    }
    
    def __init__(self, llm: ChatOllama, system_prompt: str):
        """Initialize Router Agent."""
        self.llm = llm
        self.system_prompt = system_prompt
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """Analyze this infrastructure inquiry and determine which team should handle it:

Question: {question}
Category: {category}

Available teams:
- platform: Kubernetes, containers, deployments, scaling
- devops: CI/CD, monitoring, alerts, infrastructure automation
- database: PostgreSQL, MySQL, database performance, connections
- security: SSL/TLS, access control, vulnerabilities, compliance
- network: Load balancers, DNS, firewalls, connectivity issues

Respond with ONLY the team name (one word) and a brief reason (one sentence).""")
        ])
        
        self.chain = self.prompt | self.llm | StrOutputParser()
    
    def route_inquiry(self, question: str, category: str = "") -> Dict[str, Any]:
        """Route inquiry to appropriate team."""
        # First try keyword matching for fast routing
        keyword_team = self._keyword_match(question.lower())
        
        if keyword_team:
            return {
                "team": keyword_team,
                "method": "keyword",
                "confidence": "high",
                "reason": f"Matched keywords for {keyword_team} team"
            }
        
        # If no keyword match, use LLM
        try:
            response = self.chain.invoke({
                "question": question,
                "category": category or "general"
            })
            
            # Parse response
            team = self._extract_team(response)
            
            return {
                "team": team,
                "method": "llm",
                "confidence": "medium",
                "reason": response.strip()
            }
        except Exception as e:
            print(f"Error routing inquiry: {e}")
            return {
                "team": "platform",
                "method": "default",
                "confidence": "low",
                "reason": "Default routing due to error"
            }
    
    def _keyword_match(self, text: str) -> str:
        """Match keywords to teams."""
        team_scores = {team: 0 for team in self.TEAMS}
        
        for team, keywords in self.TEAMS.items():
            for keyword in keywords:
                if keyword in text:
                    team_scores[team] += 1
        
        # Return team with highest score
        max_score = max(team_scores.values())
        if max_score > 0:
            return max(team_scores, key=team_scores.get)
        
        return None
    
    def _extract_team(self, response: str) -> str:
        """Extract team name from LLM response."""
        response_lower = response.lower()
        
        for team in self.TEAMS.keys():
            if team in response_lower:
                return team
        
        # Default to platform if no team found
        return "platform"
