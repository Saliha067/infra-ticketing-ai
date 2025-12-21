"""JIRA integration tools (optional)."""
from langchain.tools import tool
from typing import Dict, Any, Optional
import requests
from requests.auth import HTTPBasicAuth


def create_jira_tools(jira_url: Optional[str], jira_email: Optional[str], jira_token: Optional[str], project_key: Optional[str]):
    """Create JIRA tools if credentials are provided."""
    
    if not all([jira_url, jira_email, jira_token, project_key]):
        # Return dummy tools if JIRA is not configured
        @tool
        def create_jira_ticket_disabled(summary: str, description: str, team: str, priority: str = "Medium") -> str:
            """JIRA integration is not configured. This is a placeholder."""
            return f"JIRA integration disabled. Would have created ticket:\n- Summary: {summary}\n- Team: {team}\n- Priority: {priority}"
        
        return [create_jira_ticket_disabled]
    
    auth = HTTPBasicAuth(jira_email, jira_token)
    headers = {"Content-Type": "application/json"}
    
    @tool
    def create_jira_ticket(summary: str, description: str, team: str, priority: str = "Medium") -> str:
        """Create a JIRA ticket for infrastructure inquiry.
        
        Args:
            summary: Brief ticket summary (max 100 chars)
            description: Detailed description
            team: Team to assign (platform, devops, database, security, network)
            priority: Ticket priority (Low, Medium, High, Critical)
        
        Returns:
            Ticket ID and URL or error message
        """
        try:
            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary[:100],
                    "description": description,
                    "issuetype": {"name": "Task"},
                    "priority": {"name": priority},
                    "labels": [team, "infrastructure", "automated"]
                }
            }
            
            response = requests.post(
                f"{jira_url}/rest/api/2/issue",
                json=payload,
                auth=auth,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                ticket_id = data["key"]
                ticket_url = f"{jira_url}/browse/{ticket_id}"
                return f"Ticket created: {ticket_id}\nURL: {ticket_url}\nStatus: Open\nTeam: {team}"
            else:
                return f"Error creating ticket: {response.status_code} - {response.text}"
        
        except Exception as e:
            return f"Error creating JIRA ticket: {str(e)}"
    
    @tool
    def get_jira_ticket_status(ticket_id: str) -> str:
        """Get the current status of a JIRA ticket.
        
        Args:
            ticket_id: JIRA ticket ID (e.g., INFRA-123)
        
        Returns:
            Ticket status information
        """
        try:
            response = requests.get(
                f"{jira_url}/rest/api/2/issue/{ticket_id}",
                auth=auth,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data["fields"]["status"]["name"]
                assignee = data["fields"].get("assignee", {})
                assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"
                
                return f"Ticket: {ticket_id}\nStatus: {status}\nAssignee: {assignee_name}"
            else:
                return f"Error fetching ticket: {response.status_code}"
        
        except Exception as e:
            return f"Error fetching JIRA ticket: {str(e)}"
    
    return [create_jira_ticket, get_jira_ticket_status]
