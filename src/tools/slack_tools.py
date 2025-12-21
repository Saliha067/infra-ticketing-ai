"""Slack interaction tools."""
from langchain.tools import tool
from typing import Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def create_slack_tools(slack_client: WebClient):
    """Create Slack tools with client dependency injection."""
    
    @tool
    def send_slack_message(channel: str, text: str, thread_ts: Optional[str] = None) -> str:
        """Send a message to a Slack channel or thread.
        
        Args:
            channel: Channel ID to send message to
            text: Message text to send
            thread_ts: Optional thread timestamp to reply in thread
        
        Returns:
            Success or error message
        """
        try:
            response = slack_client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts
            )
            return f"Message sent successfully. Timestamp: {response['ts']}"
        except SlackApiError as e:
            return f"Error sending message: {e.response['error']}"
    
    @tool
    def post_slack_block_message(channel: str, blocks: list, text: str, thread_ts: Optional[str] = None) -> str:
        """Post a formatted block message to Slack.
        
        Args:
            channel: Channel ID
            blocks: List of block elements
            text: Fallback text
            thread_ts: Optional thread timestamp
        
        Returns:
            Success or error message
        """
        try:
            response = slack_client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=text,
                thread_ts=thread_ts
            )
            return f"Block message sent successfully. Timestamp: {response['ts']}"
        except SlackApiError as e:
            return f"Error sending block message: {e.response['error']}"
    
    @tool
    def update_slack_message(channel: str, ts: str, text: str) -> str:
        """Update an existing Slack message.
        
        Args:
            channel: Channel ID
            ts: Message timestamp to update
            text: New message text
        
        Returns:
            Success or error message
        """
        try:
            slack_client.chat_update(
                channel=channel,
                ts=ts,
                text=text
            )
            return "Message updated successfully."
        except SlackApiError as e:
            return f"Error updating message: {e.response['error']}"
    
    @tool
    def add_slack_reaction(channel: str, timestamp: str, emoji: str) -> str:
        """Add a reaction emoji to a Slack message.
        
        Args:
            channel: Channel ID
            timestamp: Message timestamp
            emoji: Emoji name (without colons)
        
        Returns:
            Success or error message
        """
        try:
            slack_client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=emoji
            )
            return f"Added reaction :{emoji}:"
        except SlackApiError as e:
            return f"Error adding reaction: {e.response['error']}"
    
    return [send_slack_message, post_slack_block_message, update_slack_message, add_slack_reaction]
