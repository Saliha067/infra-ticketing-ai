"""Slack Bot integration with LangChain agents."""
import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from typing import Dict, Any
import re
from datetime import datetime, timedelta, timezone
from collections import Counter
from sqlalchemy import func

from config.prompts import (
    SLACK_RESPONSE_TEMPLATE,
    KNOWLEDGE_BASE_FOUND_TEMPLATE,
    TICKET_CREATED_TEMPLATE,
    GATHERING_INFO_TEMPLATE,
    ERROR_TEMPLATE
)


class SlackBot:
    """Slack Bot handler for infrastructure inquiries."""
    
    def __init__(
        self,
        bot_token: str,
        app_token: str,
        supervisor_agent,
        jira_tools,
        db_session,
        logger
    ):
        """Initialize Slack Bot."""
        self.app = App(token=bot_token)
        self.app_token = app_token
        self.client = WebClient(token=bot_token)
        self.supervisor = supervisor_agent
        self.jira_tools = jira_tools
        self.db_session = db_session
        self.logger = logger
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register Slack event handlers."""
        
        @self.app.command("/infra-inquiry")
        def handle_infra_inquiry(ack, command, logger):
            """Handle /infra-inquiry slash command."""
            ack()
            self.logger.info(f"Received /infra-inquiry from {command['user_id']} in {command['channel_id']}")
            
            # Store the channel_id in the modal's private_metadata so we can retrieve it later
            self._show_inquiry_modal(command)
        
        @self.app.command("/infra-metrics")
        def handle_infra_metrics(ack, command, say):
            """Handle /infra-metrics slash command."""
            ack()
            self.logger.info(f"Received /infra-metrics from {command['user_id']} in {command['channel_id']}")
            
            # Get metrics period from command text (default: today)
            period = command.get("text", "").strip().lower() or "today"
            
            try:
                metrics_text = self._generate_metrics(period)
                say(metrics_text, channel=command["channel_id"])
            except Exception as e:
                self.logger.error(f"Error generating metrics: {e}")
                say(f"❌ Error generating metrics: {str(e)}", channel=command["channel_id"])
        
        @self.app.view("inquiry_submission")
        def handle_inquiry_submission(ack, body, view, logger):
            """Handle inquiry form submission."""
            ack()
            self.logger.info(f"Processing inquiry submission from {body['user']['id']}")
            
            # Extract form values
            values = view["state"]["values"]
            question = values["question_block"]["question_input"]["value"]
            
            # Get selected environments (multi-select)
            env_selected = values["environment_block"]["environment_select"].get("selected_options", [])
            environment = ", ".join([opt["value"] for opt in env_selected]) if env_selected else "Not specified"
            
            # Get deadline from datepicker
            deadline_date = values["deadline_block"]["deadline_select"].get("selected_date")
            deadline = deadline_date if deadline_date else "Not specified"
            
            user_id = body["user"]["id"]
            
            # Get the channel_id from private_metadata
            import json
            metadata = json.loads(view.get("private_metadata", "{}"))
            channel_id = metadata.get("channel_id", user_id)  # Fallback to DM if not found
            
            # Process the inquiry
            self._process_inquiry_async(
                question=question,
                environment=environment,
                deadline=deadline,
                user_id=user_id,
                channel_id=channel_id
            )
        
        @self.app.event("app_mention")
        def handle_mention(event, say):
            """Handle @bot mentions."""
            self.logger.info(f"Bot mentioned in {event['channel']}")
            
            # Extract question from mention
            text = event["text"]
            # Remove bot mention
            question = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
            
            if question:
                self._process_inquiry_async(
                    question=question,
                    environment=None,
                    deadline=None,
                    user_id=event["user"],
                    channel_id=event["channel"],
                    thread_ts=event.get("ts")
                )
            else:
                say("Hi! Use `/infra-inquiry` to submit an infrastructure question.", thread_ts=event.get("ts"))
    
    def _show_inquiry_modal(self, command: Dict[str, Any]):
        """Show inquiry submission modal."""
        try:
            import json
            
            # Extract question from command text if provided
            # e.g., /infra-inquiry How to configure load balancer?
            command_text = command.get("text", "").strip()
            initial_question = command_text if command_text else ""
            
            # Store channel_id in private_metadata so we can retrieve it after submission
            private_metadata = json.dumps({
                "channel_id": command["channel_id"]
            })
            
            self.client.views_open(
                trigger_id=command["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "inquiry_submission",
                    "private_metadata": private_metadata,
                    "title": {"type": "plain_text", "text": "Infrastructure Inquiry"},
                    "submit": {"type": "plain_text", "text": "Submit"},
                    "close": {"type": "plain_text", "text": "Cancel"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "question_block",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "question_input",
                                "multiline": True,
                                "initial_value": initial_question,
                                "placeholder": {"type": "plain_text", "text": "Describe your infrastructure issue or question..."}
                            },
                            "label": {"type": "plain_text", "text": "Your Question"}
                        },
                        {
                            "type": "input",
                            "block_id": "environment_block",
                            "element": {
                                "type": "multi_static_select",
                                "action_id": "environment_select",
                                "placeholder": {"type": "plain_text", "text": "Select environment(s)"},
                                "options": [
                                    {
                                        "text": {"type": "plain_text", "text": "Production"},
                                        "value": "PROD"
                                    },
                                    {
                                        "text": {"type": "plain_text", "text": "Staging"},
                                        "value": "STG"
                                    },
                                    {
                                        "text": {"type": "plain_text", "text": "Performance"},
                                        "value": "PERF"
                                    },
                                    {
                                        "text": {"type": "plain_text", "text": "Development"},
                                        "value": "DEV"
                                    }
                                ]
                            },
                            "label": {"type": "plain_text", "text": "Environment"},
                            "optional": True
                        },
                        {
                            "type": "input",
                            "block_id": "deadline_block",
                            "element": {
                                "type": "datepicker",
                                "action_id": "deadline_select",
                                "placeholder": {"type": "plain_text", "text": "Select deadline date"}
                            },
                            "label": {"type": "plain_text", "text": "Deadline/Urgency"},
                            "optional": True
                        }
                    ]
                }
            )
        except Exception as e:
            self.logger.error(f"Error showing modal: {e}")
    
    def _process_inquiry_async(
        self,
        question: str,
        environment: str,
        deadline: str,
        user_id: str,
        channel_id: str,
        thread_ts: str = None
    ):
        """Process inquiry asynchronously."""
        try:
            # Send initial "processing" message to the channel where command was invoked
            response = self.client.chat_postMessage(
                channel=channel_id,
                text="🔍 Processing your inquiry...",
                thread_ts=thread_ts
            )
            message_ts = response["ts"]
            
            # Process with supervisor agent
            result = self.supervisor.process_inquiry(
                question=question,
                user_id=user_id,
                channel_id=channel_id,
                environment=environment,
                deadline=deadline
            )
            
            # Format and send response
            formatted_response = self._format_response(result)
            
            # Update the message
            self.client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=formatted_response["text"],
                blocks=formatted_response.get("blocks")
            )
            
            # If ticket needed, create it
            if result["action"] == "create_ticket" and self.jira_tools:
                self._create_ticket_and_notify(result, channel_id, message_ts)
            
            # Save to database
            self._save_inquiry(result)
            
        except Exception as e:
            self.logger.error(f"Error processing inquiry: {e}", exc_info=True)
            
            # Try to send error message to channel
            try:
                error_msg = ERROR_TEMPLATE.format(
                    error_message="Failed to process your inquiry. Please try again.",
                    error_id=f"ERR-{user_id[-6:]}"
                )
                self.client.chat_postMessage(
                    channel=channel_id,
                    text=error_msg,
                    thread_ts=thread_ts
                )
            except Exception as inner_e:
                self.logger.error(f"Error sending error message: {inner_e}")
    
    def _format_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format the inquiry result for Slack."""
        if result["action"] == "answer_from_kb":
            source = result["source"]
            text = KNOWLEDGE_BASE_FOUND_TEMPLATE.format(
                answer=result["answer"],
                team=source.get("team", "N/A"),
                tags=", ".join(source.get("tags", []))
            )
            
            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Your Question:*\n{result['question']}"}
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"✅ *Found in Knowledge Base*\n\n{result['answer']}"}
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"*Team:* {source.get('team', 'N/A')} | *Tags:* {', '.join(source.get('tags', []))}"}
                    ]
                }
            ]
            
            return {"text": text, "blocks": blocks}
        else:
            text = f"📋 Your inquiry has been received and will be routed to the **{result['assigned_team']}** team."
            return {"text": text}
    
    def _create_ticket_and_notify(self, result: Dict[str, Any], channel_id: str, thread_ts: str):
        """Create JIRA ticket and notify user."""
        try:
            ticket_details = result["ticket_details"]
            
            # Create ticket using JIRA tool
            jira_create_tool = self.jira_tools[0]
            ticket_response = jira_create_tool.func(
                summary=ticket_details["summary"],
                description=ticket_details["description"],
                team=ticket_details["team"],
                priority=ticket_details["priority"]
            )
            
            # Parse ticket ID from response
            ticket_id = "N/A"
            ticket_url = "N/A"
            if "Ticket created:" in ticket_response:
                lines = ticket_response.split("\n")
                for line in lines:
                    if "Ticket created:" in line:
                        ticket_id = line.split(":")[1].strip()
                    if "URL:" in line:
                        ticket_url = line.split("URL:")[1].strip()
            
            # Send ticket notification
            message = TICKET_CREATED_TEMPLATE.format(
                ticket_id=ticket_id,
                summary=ticket_details["summary"],
                status="Open",
                team=ticket_details["team"],
                ticket_url=ticket_url,
                sla="24-48 hours"
            )
            
            self.client.chat_postMessage(
                channel=channel_id,
                text=message,
                thread_ts=thread_ts
            )
            
        except Exception as e:
            self.logger.error(f"Error creating ticket: {e}")
    
    def _save_inquiry(self, result: Dict[str, Any]):
        """Save inquiry to database."""
        try:
            from src.db.models import Inquiry
            
            inquiry = Inquiry(
                slack_user_id=result["user_id"],
                slack_channel_id=result["channel_id"],
                question=result["question"],
                environment=result.get("environment"),
                deadline=result.get("deadline"),
                urgency=result["classification"].get("urgency"),
                category=result["classification"].get("category"),
                resolved_from_kb=result["action"] == "answer_from_kb",
                kb_answer=result.get("answer"),
                assigned_team=result.get("assigned_team"),
                status="resolved" if result["action"] == "answer_from_kb" else "open",
                inquiry_metadata=result
            )
            
            self.db_session.add(inquiry)
            self.db_session.commit()
            
        except Exception as e:
            self.logger.error(f"Error saving inquiry: {e}")
            self.db_session.rollback()
    
    def _generate_metrics(self, period: str) -> str:
        """Generate metrics report for Slack."""
        from src.db.models import Inquiry
        
        try:
            if period in ["today", "daily"]:
                return self._get_daily_metrics()
            elif period in ["week", "weekly"]:
                return self._get_weekly_metrics()
            elif period in ["month", "monthly"]:
                return self._get_monthly_metrics()
            elif period in ["all", "total", "alltime"]:
                return self._get_alltime_metrics()
            else:
                return self._get_daily_metrics()
        except Exception as e:
            self.logger.error(f"Error generating {period} metrics: {e}")
            raise
    
    def _get_daily_metrics(self) -> str:
        """Get today's metrics."""
        from src.db.models import Inquiry
        
        today = datetime.now(timezone.utc).date()
        inquiries = self.db_session.query(Inquiry).filter(
            func.date(Inquiry.created_at) == today
        ).all()
        
        resolved = len([i for i in inquiries if i.resolved_from_kb])
        tickets = len([i for i in inquiries if not i.resolved_from_kb])
        
        text = f"📊 *TODAY'S METRICS*\n\n"
        text += f"Total Inquiries: *{len(inquiries)}*\n"
        text += f"✅ Resolved from KB: {resolved}\n"
        text += f"🎫 Needs Team Action: {tickets}\n"
        
        if inquiries:
            teams = Counter([i.assigned_team for i in inquiries if i.assigned_team])
            if teams:
                text += f"\n*Team Distribution:*\n"
                for team, count in teams.most_common():
                    text += f"  • {team}: {count}\n"
            
            categories = Counter([i.category for i in inquiries if i.category])
            if categories:
                text += f"\n*Top Categories:*\n"
                for cat, count in categories.most_common(3):
                    text += f"  • {cat}: {count}\n"
        else:
            text += "\n_No inquiries today yet!_"
        
        return text
    
    def _get_weekly_metrics(self) -> str:
        """Get this week's metrics."""
        from src.db.models import Inquiry
        
        today = datetime.now(timezone.utc)
        week_start = today - timedelta(days=today.weekday())
        inquiries = self.db_session.query(Inquiry).filter(
            Inquiry.created_at >= week_start
        ).all()
        
        resolved = len([i for i in inquiries if i.resolved_from_kb])
        tickets = len([i for i in inquiries if not i.resolved_from_kb])
        kb_rate = (resolved/len(inquiries)*100) if inquiries else 0
        
        text = f"📈 *THIS WEEK'S METRICS*\n\n"
        text += f"Total Inquiries: *{len(inquiries)}*\n"
        text += f"✅ Resolved from KB: {resolved} ({kb_rate:.1f}%)\n"
        text += f"🎫 Created Tickets: {tickets}\n"
        
        if inquiries:
            teams = Counter([i.assigned_team for i in inquiries if i.assigned_team])
            if teams:
                text += f"\n*Top Teams:*\n"
                for team, count in teams.most_common(3):
                    text += f"  • {team}: {count}\n"
        else:
            text += "\n_No inquiries this week yet!_"
        
        return text
    
    def _get_monthly_metrics(self) -> str:
        """Get this month's metrics."""
        from src.db.models import Inquiry
        
        today = datetime.now(timezone.utc)
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        inquiries = self.db_session.query(Inquiry).filter(
            Inquiry.created_at >= month_start
        ).all()
        
        resolved = len([i for i in inquiries if i.resolved_from_kb])
        tickets = len([i for i in inquiries if not i.resolved_from_kb])
        kb_rate = (resolved/len(inquiries)*100) if inquiries else 0
        
        text = f"📅 *THIS MONTH'S METRICS*\n\n"
        text += f"Total Inquiries: *{len(inquiries)}*\n"
        text += f"✅ Resolved from KB: {resolved} ({kb_rate:.1f}%)\n"
        text += f"🎫 Created Tickets: {tickets}\n"
        text += f"\n📊 *KB Hit Rate: {kb_rate:.1f}%*\n"
        
        if inquiries:
            teams = Counter([i.assigned_team for i in inquiries if i.assigned_team])
            if teams:
                text += f"\n*Team Distribution:*\n"
                for team, count in teams.most_common():
                    pct = (count/len(inquiries)*100)
                    text += f"  • {team}: {count} ({pct:.1f}%)\n"
            
            categories = Counter([i.category for i in inquiries if i.category])
            if categories:
                text += f"\n*Top Categories:*\n"
                for cat, count in categories.most_common(5):
                    text += f"  • {cat}: {count}\n"
        else:
            text += "\n_No inquiries this month yet!_"
        
        return text
    
    def _get_alltime_metrics(self) -> str:
        """Get all-time metrics."""
        from src.db.models import Inquiry
        
        inquiries = self.db_session.query(Inquiry).all()
        
        if not inquiries:
            return "🏆 *ALL-TIME METRICS*\n\n_No inquiries yet!_"
        
        resolved = len([i for i in inquiries if i.resolved_from_kb])
        tickets = len([i for i in inquiries if not i.resolved_from_kb])
        kb_rate = (resolved/len(inquiries)*100)
        
        first = min(inquiries, key=lambda i: i.created_at)
        last = max(inquiries, key=lambda i: i.created_at)
        
        text = f"🏆 *ALL-TIME METRICS*\n\n"
        text += f"Total Inquiries: *{len(inquiries)}*\n"
        text += f"✅ Resolved from KB: {resolved} ({kb_rate:.1f}%)\n"
        text += f"🎫 Created Tickets: {tickets}\n"
        text += f"\nFirst: {first.created_at.strftime('%Y-%m-%d')}\n"
        text += f"Latest: {last.created_at.strftime('%Y-%m-%d')}\n"
        
        teams = Counter([i.assigned_team for i in inquiries if i.assigned_team])
        if teams:
            text += f"\n*Team Workload:*\n"
            for team, count in teams.most_common():
                pct = (count/len(inquiries)*100)
                text += f"  • {team}: {count} ({pct:.1f}%)\n"
        
        return text
    
    def start(self):
        """Start the Slack bot in Socket Mode."""
        self.logger.info("Starting Slack bot in Socket Mode...")
        handler = SocketModeHandler(self.app, self.app_token)
        handler.start()
