"""Supervisor Agent - Main orchestration agent."""
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from typing import Dict, Any, Optional
from datetime import datetime


class SupervisorAgent:
    """Main supervisor agent that orchestrates the inquiry handling workflow."""
    
    def __init__(
        self,
        llm: ChatOllama,
        knowledge_agent,
        router_agent,
        system_prompt: str
    ):
        """Initialize Supervisor Agent."""
        self.llm = llm
        self.knowledge_agent = knowledge_agent
        self.router_agent = router_agent
        self.system_prompt = system_prompt
        
        # Classifier prompt
        self.classifier_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an inquiry classifier for infrastructure support."),
            ("human", """Classify this infrastructure inquiry:

Question: {question}

Determine:
1. Urgency: low, medium, high, critical
2. Category: kubernetes, database, network, security, deployment, monitoring, other
3. Needs ticket: yes or no (yes if complex/no knowledge base answer likely)

Respond in this exact format:
URGENCY: <level>
CATEGORY: <category>
NEEDS_TICKET: <yes/no>""")
        ])
        
        self.classifier_chain = self.classifier_prompt | self.llm | StrOutputParser()
    
    def process_inquiry(
        self,
        question: str,
        user_id: str,
        channel_id: str,
        environment: Optional[str] = None,
        deadline: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an infrastructure inquiry end-to-end."""
        
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "question": question,
            "user_id": user_id,
            "channel_id": channel_id,
            "environment": environment,
            "deadline": deadline,
            "steps": []
        }
        
        # Step 1: Classify the inquiry
        classification = self._classify_inquiry(question)
        result["classification"] = classification
        result["steps"].append("classified")
        
        # Step 2: Search knowledge base
        kb_result = self.knowledge_agent.answer_question(question)
        result["knowledge_base"] = kb_result
        result["steps"].append("searched_kb")
        
        # Step 3: Decide action based on KB results
        if kb_result["found"] and kb_result["confidence"] in ["high", "medium"]:
            # Answer found in KB
            result["action"] = "answer_from_kb"
            result["answer"] = kb_result["answer"]
            result["source"] = kb_result["source"]
            result["requires_ticket"] = False
            result["steps"].append("answered_from_kb")
        else:
            # Need to create ticket
            result["action"] = "create_ticket"
            result["requires_ticket"] = True
            
            # Step 4: Route to appropriate team
            routing = self.router_agent.route_inquiry(question, classification.get("category", ""))
            result["routing"] = routing
            result["assigned_team"] = routing["team"]
            result["steps"].append("routed_to_team")
            
            # Generate ticket details
            ticket_details = self._generate_ticket_details(
                question=question,
                classification=classification,
                team=routing["team"],
                environment=environment,
                deadline=deadline
            )
            result["ticket_details"] = ticket_details
            result["steps"].append("generated_ticket_details")
        
        result["completed"] = True
        return result
    
    def _classify_inquiry(self, question: str) -> Dict[str, Any]:
        """Classify the inquiry."""
        try:
            response = self.classifier_chain.invoke({"question": question})
            
            # Parse response
            classification = {}
            for line in response.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower().replace("_", " ")
                    value = value.strip().lower()
                    
                    if "urgency" in key:
                        classification["urgency"] = value
                    elif "category" in key:
                        classification["category"] = value
                    elif "needs" in key or "ticket" in key:
                        classification["needs_ticket"] = value == "yes"
            
            return classification
        except Exception as e:
            print(f"Error classifying inquiry: {e}")
            return {
                "urgency": "medium",
                "category": "other",
                "needs_ticket": True
            }
    
    def _generate_ticket_details(
        self,
        question: str,
        classification: Dict[str, Any],
        team: str,
        environment: Optional[str],
        deadline: Optional[str]
    ) -> Dict[str, Any]:
        """Generate JIRA ticket details."""
        # Generate summary (first 100 chars of question)
        summary = question[:97] + "..." if len(question) > 100 else question
        
        # Build description
        description = f"""Infrastructure Inquiry

**Question:**
{question}

**Details:**
- Environment: {environment or 'Not specified'}
- Deadline: {deadline or 'Not specified'}
- Urgency: {classification.get('urgency', 'medium')}
- Category: {classification.get('category', 'general')}

**Assigned Team:** {team}

This ticket was automatically created by the Infrastructure Bot.
"""
        
        # Generate labels
        labels = [
            team,
            classification.get("category", "general"),
            classification.get("urgency", "medium"),
            "automated",
            "infrastructure"
        ]
        
        return {
            "summary": summary,
            "description": description,
            "labels": labels,
            "team": team,
            "priority": self._urgency_to_priority(classification.get("urgency", "medium"))
        }
    
    def _urgency_to_priority(self, urgency: str) -> str:
        """Convert urgency to JIRA priority."""
        mapping = {
            "low": "Low",
            "medium": "Medium",
            "high": "High",
            "critical": "Critical"
        }
        return mapping.get(urgency.lower(), "Medium")
