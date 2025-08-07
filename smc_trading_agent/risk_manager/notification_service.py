"""
Notification Service for SMC Trading Agent.

This module provides comprehensive notification capabilities including:
- Email notifications via SendGrid API
- SMS notifications via Twilio API
- Slack notifications via webhooks
- Notification templating with Jinja2
- Rate limiting and throttling
- Delivery confirmation and tracking
- Fallback mechanisms for failed notifications
"""

import asyncio
import logging
import time
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import aiohttp
from jinja2 import Template, Environment, FileSystemLoader

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification channels."""
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NotificationRequest:
    """Notification request data."""
    channel: NotificationChannel
    priority: NotificationPriority
    subject: str
    message: str
    recipients: List[str]
    template_data: Dict[str, Any] = None
    template_name: str = None
    timestamp: float = None


@dataclass
class NotificationResult:
    """Notification delivery result."""
    channel: NotificationChannel
    success: bool
    message_id: str = ""
    delivery_time: float = 0
    error_message: str = ""
    retry_count: int = 0
    timestamp: float = None


class NotificationService:
    """
    Comprehensive notification service with multi-channel support.
    
    Supports email, SMS, and Slack notifications with templating,
    rate limiting, and delivery confirmation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize notification service.
        
        Args:
            config: Configuration dictionary with notification settings
        """
        self.config = config
        
        # Channel configurations
        self.email_config = config.get('email', {})
        self.sms_config = config.get('sms', {})
        self.slack_config = config.get('slack', {})
        
        # Rate limiting settings
        self.rate_limits = config.get('rate_limits', {
            NotificationChannel.EMAIL: 100,  # emails per hour
            NotificationChannel.SMS: 50,     # SMS per hour
            NotificationChannel.SLACK: 200   # Slack messages per hour
        })
        
        # Throttling settings
        self.throttle_delay = config.get('throttle_delay', 1.0)  # seconds
        self.max_retry_attempts = config.get('max_retry_attempts', 3)
        self.retry_delay = config.get('retry_delay', 5.0)  # seconds
        
        # Rate limiting tracking
        self.message_counts = {channel: 0 for channel in NotificationChannel}
        self.last_reset_time = {channel: time.time() for channel in NotificationChannel}
        self.rate_limit_window = 3600  # 1 hour
        
        # Notification history
        self.notification_history: List[NotificationResult] = []
        self.max_history_size = config.get('max_history_size', 1000)
        
        # Template environment
        self.template_env = Environment(
            loader=FileSystemLoader(config.get('template_path', './templates')),
            autoescape=True
        )
        
        # HTTP session for API calls
        self.http_session = None
        
        logger.info("Initialized notification service with multi-channel support")
    
    async def send_alert(self, channel: NotificationChannel, priority: NotificationPriority,
                        subject: str, message: str, recipients: List[str],
                        template_data: Optional[Dict[str, Any]] = None,
                        template_name: Optional[str] = None) -> NotificationResult:
        """
        Send notification via specified channel.
        
        Args:
            channel: Notification channel
            priority: Notification priority
            subject: Notification subject
            message: Notification message
            recipients: List of recipients
            template_data: Data for template rendering
            template_name: Template name to use
            
        Returns:
            NotificationResult: Delivery result
        """
        try:
            # Check rate limits
            if not await self._check_rate_limit(channel):
                return NotificationResult(
                    channel=channel,
                    success=False,
                    error_message="Rate limit exceeded",
                    timestamp=time.time()
                )
            
            # Create notification request
            request = NotificationRequest(
                channel=channel,
                priority=priority,
                subject=subject,
                message=message,
                recipients=recipients,
                template_data=template_data,
                template_name=template_name,
                timestamp=time.time()
            )
            
            # Process template if specified
            if template_name and template_data:
                try:
                    rendered_message = await self._render_template(template_name, template_data)
                    request.message = rendered_message
                except Exception as e:
                    logger.error(f"Template rendering failed: {e}")
                    # Continue with original message
            
            # Send notification based on channel
            if channel == NotificationChannel.EMAIL:
                result = await self._send_email(request)
            elif channel == NotificationChannel.SMS:
                result = await self._send_sms(request)
            elif channel == NotificationChannel.SLACK:
                result = await self._send_slack(request)
            else:
                result = NotificationResult(
                    channel=channel,
                    success=False,
                    error_message=f"Unsupported channel: {channel}",
                    timestamp=time.time()
                )
            
            # Update rate limiting
            self._update_rate_limit(channel)
            
            # Store in history
            self.notification_history.append(result)
            if len(self.notification_history) > self.max_history_size:
                self.notification_history = self.notification_history[-self.max_history_size:]
            
            logger.info(f"Notification sent via {channel.value}: {result.success}")
            return result
            
        except Exception as e:
            logger.error(f"Notification sending failed: {e}")
            return NotificationResult(
                channel=channel,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )
    
    async def send_multi_channel_alert(self, channels: List[NotificationChannel],
                                     priority: NotificationPriority,
                                     subject: str, message: str,
                                     recipients: Dict[NotificationChannel, List[str]],
                                     template_data: Optional[Dict[str, Any]] = None,
                                     template_name: Optional[str] = None) -> List[NotificationResult]:
        """
        Send notification via multiple channels concurrently.
        
        Args:
            channels: List of notification channels
            priority: Notification priority
            subject: Notification subject
            message: Notification message
            recipients: Dictionary of recipients by channel
            template_data: Data for template rendering
            template_name: Template name to use
            
        Returns:
            List[NotificationResult]: Delivery results for all channels
        """
        try:
            # Create tasks for all channels
            tasks = []
            for channel in channels:
                channel_recipients = recipients.get(channel, [])
                if channel_recipients:
                    task = self.send_alert(
                        channel, priority, subject, message,
                        channel_recipients, template_data, template_name
                    )
                    tasks.append(task)
            
            # Execute all tasks concurrently
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                notification_results = []
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Multi-channel notification failed: {result}")
                        continue
                    if result:
                        notification_results.append(result)
                
                return notification_results
            else:
                return []
                
        except Exception as e:
            logger.error(f"Multi-channel notification failed: {e}")
            return []
    
    async def _send_email(self, request: NotificationRequest) -> NotificationResult:
        """Send email notification."""
        try:
            start_time = time.time()
            
            # Try SendGrid first
            if self.email_config.get('sendgrid_api_key'):
                result = await self._send_email_sendgrid(request)
                if result.success:
                    return result
            
            # Fallback to SMTP
            if self.email_config.get('smtp'):
                result = await self._send_email_smtp(request)
                if result.success:
                    return result
            
            # If both failed
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                success=False,
                error_message="All email methods failed",
                delivery_time=time.time() - start_time,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )
    
    async def _send_email_sendgrid(self, request: NotificationRequest) -> NotificationResult:
        """Send email via SendGrid API."""
        try:
            start_time = time.time()
            
            # Prepare HTTP session
            if not self.http_session:
                self.http_session = aiohttp.ClientSession()
            
            # Prepare email data
            email_data = {
                "personalizations": [
                    {
                        "to": [{"email": recipient} for recipient in request.recipients],
                        "subject": request.subject
                    }
                ],
                "from": {"email": self.email_config.get('from_email', 'noreply@smc-trading.com')},
                "content": [
                    {
                        "type": "text/html",
                        "value": request.message
                    }
                ]
            }
            
            # Send via SendGrid API
            headers = {
                "Authorization": f"Bearer {self.email_config['sendgrid_api_key']}",
                "Content-Type": "application/json"
            }
            
            async with self.http_session.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers=headers,
                json=email_data,
                timeout=30
            ) as response:
                if response.status == 202:
                    return NotificationResult(
                        channel=NotificationChannel.EMAIL,
                        success=True,
                        message_id=f"sg_{int(time.time())}",
                        delivery_time=time.time() - start_time,
                        timestamp=time.time()
                    )
                else:
                    error_text = await response.text()
                    return NotificationResult(
                        channel=NotificationChannel.EMAIL,
                        success=False,
                        error_message=f"SendGrid API error: {response.status} - {error_text}",
                        delivery_time=time.time() - start_time,
                        timestamp=time.time()
                    )
                    
        except Exception as e:
            logger.error(f"SendGrid email sending failed: {e}")
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )
    
    async def _send_email_smtp(self, request: NotificationRequest) -> NotificationResult:
        """Send email via SMTP."""
        try:
            start_time = time.time()
            
            smtp_config = self.email_config.get('smtp', {})
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = request.subject
            msg['From'] = smtp_config.get('from_email', 'noreply@smc-trading.com')
            msg['To'] = ', '.join(request.recipients)
            
            # Add HTML content
            html_part = MIMEText(request.message, 'html')
            msg.attach(html_part)
            
            # Send via SMTP
            with smtplib.SMTP(smtp_config.get('host', 'localhost'), smtp_config.get('port', 587)) as server:
                if smtp_config.get('use_tls', True):
                    server.starttls()
                
                if smtp_config.get('username') and smtp_config.get('password'):
                    server.login(smtp_config['username'], smtp_config['password'])
                
                server.send_message(msg)
            
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                success=True,
                message_id=f"smtp_{int(time.time())}",
                delivery_time=time.time() - start_time,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"SMTP email sending failed: {e}")
            return NotificationResult(
                channel=NotificationChannel.EMAIL,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )
    
    async def _send_sms(self, request: NotificationRequest) -> NotificationResult:
        """Send SMS notification via Twilio."""
        try:
            start_time = time.time()
            
            if not self.sms_config.get('twilio_account_sid') or not self.sms_config.get('twilio_auth_token'):
                return NotificationResult(
                    channel=NotificationChannel.SMS,
                    success=False,
                    error_message="Twilio credentials not configured",
                    timestamp=time.time()
                )
            
            # Prepare HTTP session
            if not self.http_session:
                self.http_session = aiohttp.ClientSession()
            
            # Send SMS to each recipient
            successful_sends = 0
            error_messages = []
            
            for recipient in request.recipients:
                try:
                    # Prepare SMS data
                    sms_data = {
                        "To": recipient,
                        "From": self.sms_config.get('from_number', ''),
                        "Body": f"{request.subject}: {request.message[:150]}"  # Truncate for SMS
                    }
                    
                    # Send via Twilio API
                    auth = aiohttp.BasicAuth(
                        self.sms_config['twilio_account_sid'],
                        self.sms_config['twilio_auth_token']
                    )
                    
                    url = f"https://api.twilio.com/2010-04-01/Accounts/{self.sms_config['twilio_account_sid']}/Messages.json"
                    
                    async with self.http_session.post(
                        url,
                        auth=auth,
                        data=sms_data,
                        timeout=30
                    ) as response:
                        if response.status == 201:
                            successful_sends += 1
                        else:
                            error_text = await response.text()
                            error_messages.append(f"Twilio API error: {response.status} - {error_text}")
                            
                except Exception as e:
                    error_messages.append(f"SMS send error: {str(e)}")
            
            if successful_sends == len(request.recipients):
                return NotificationResult(
                    channel=NotificationChannel.SMS,
                    success=True,
                    message_id=f"twilio_{int(time.time())}",
                    delivery_time=time.time() - start_time,
                    timestamp=time.time()
                )
            else:
                return NotificationResult(
                    channel=NotificationChannel.SMS,
                    success=False,
                    error_message=f"Partial SMS failure: {', '.join(error_messages)}",
                    delivery_time=time.time() - start_time,
                    timestamp=time.time()
                )
                
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return NotificationResult(
                channel=NotificationChannel.SMS,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )
    
    async def _send_slack(self, request: NotificationRequest) -> NotificationResult:
        """Send Slack notification via webhook."""
        try:
            start_time = time.time()
            
            webhook_url = self.slack_config.get('webhook_url')
            if not webhook_url:
                return NotificationResult(
                    channel=NotificationChannel.SLACK,
                    success=False,
                    error_message="Slack webhook URL not configured",
                    timestamp=time.time()
                )
            
            # Prepare HTTP session
            if not self.http_session:
                self.http_session = aiohttp.ClientSession()
            
            # Prepare Slack message
            slack_message = {
                "text": f"*{request.subject}*\n{request.message}",
                "username": self.slack_config.get('username', 'SMC Trading Agent'),
                "icon_emoji": self.slack_config.get('icon_emoji', ':warning:'),
                "channel": self.slack_config.get('channel', '#alerts')
            }
            
            # Add priority color
            priority_colors = {
                NotificationPriority.LOW: "#36a64f",      # Green
                NotificationPriority.MEDIUM: "#ffa500",   # Orange
                NotificationPriority.HIGH: "#ff8c00",     # Dark Orange
                NotificationPriority.CRITICAL: "#ff0000"  # Red
            }
            
            if request.priority in priority_colors:
                slack_message["attachments"] = [{
                    "color": priority_colors[request.priority],
                    "fields": [
                        {
                            "title": "Priority",
                            "value": request.priority.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(request.timestamp)),
                            "short": True
                        }
                    ]
                }]
            
            # Send via Slack webhook
            async with self.http_session.post(
                webhook_url,
                json=slack_message,
                timeout=30
            ) as response:
                if response.status == 200:
                    return NotificationResult(
                        channel=NotificationChannel.SLACK,
                        success=True,
                        message_id=f"slack_{int(time.time())}",
                        delivery_time=time.time() - start_time,
                        timestamp=time.time()
                    )
                else:
                    error_text = await response.text()
                    return NotificationResult(
                        channel=NotificationChannel.SLACK,
                        success=False,
                        error_message=f"Slack webhook error: {response.status} - {error_text}",
                        delivery_time=time.time() - start_time,
                        timestamp=time.time()
                    )
                    
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return NotificationResult(
                channel=NotificationChannel.SLACK,
                success=False,
                error_message=str(e),
                timestamp=time.time()
            )
    
    async def _render_template(self, template_name: str, template_data: Dict[str, Any]) -> str:
        """Render notification template."""
        try:
            template = self.template_env.get_template(f"{template_name}.html")
            return template.render(**template_data)
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            # Return a simple fallback template
            return f"""
            <h2>Alert Notification</h2>
            <p><strong>Subject:</strong> {template_data.get('subject', 'No subject')}</p>
            <p><strong>Message:</strong> {template_data.get('message', 'No message')}</p>
            <p><strong>Timestamp:</strong> {template_data.get('timestamp', 'Unknown')}</p>
            <p><strong>Priority:</strong> {template_data.get('priority', 'Unknown')}</p>
            """
    
    async def _check_rate_limit(self, channel: NotificationChannel) -> bool:
        """Check if rate limit allows new notification."""
        try:
            current_time = time.time()
            
            # Reset counter if window has passed
            if current_time - self.last_reset_time[channel] >= self.rate_limit_window:
                self.message_counts[channel] = 0
                self.last_reset_time[channel] = current_time
            
            # Check if limit exceeded
            limit = self.rate_limits.get(channel, 100)
            if self.message_counts[channel] >= limit:
                logger.warning(f"Rate limit exceeded for {channel.value}: {self.message_counts[channel]}/{limit}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow if check fails
    
    def _update_rate_limit(self, channel: NotificationChannel):
        """Update rate limit counter."""
        try:
            self.message_counts[channel] += 1
        except Exception as e:
            logger.error(f"Rate limit update failed: {e}")
    
    async def get_notification_summary(self) -> Dict[str, Any]:
        """Get notification service summary and statistics."""
        try:
            # Calculate statistics
            total_notifications = len(self.notification_history)
            successful_notifications = [n for n in self.notification_history if n.success]
            failed_notifications = [n for n in self.notification_history if not n.success]
            
            # Calculate success rate by channel
            channel_stats = {}
            for channel in NotificationChannel:
                channel_notifications = [n for n in self.notification_history if n.channel == channel]
                if channel_notifications:
                    success_count = len([n for n in channel_notifications if n.success])
                    channel_stats[channel.value] = {
                        "total": len(channel_notifications),
                        "successful": success_count,
                        "failed": len(channel_notifications) - success_count,
                        "success_rate": success_count / len(channel_notifications)
                    }
            
            return {
                "timestamp": time.time(),
                "total_notifications": total_notifications,
                "successful_notifications": len(successful_notifications),
                "failed_notifications": len(failed_notifications),
                "overall_success_rate": len(successful_notifications) / total_notifications if total_notifications > 0 else 1.0,
                "channel_statistics": channel_stats,
                "rate_limits": self.rate_limits,
                "current_message_counts": self.message_counts,
                "configuration": {
                    "email_configured": bool(self.email_config.get('sendgrid_api_key') or self.email_config.get('smtp')),
                    "sms_configured": bool(self.sms_config.get('twilio_account_sid')),
                    "slack_configured": bool(self.slack_config.get('webhook_url'))
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification summary: {e}")
            return {}
    
    async def clear_notification_history(self):
        """Clear notification history."""
        self.notification_history.clear()
        logger.info("Cleared notification history")
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get notification service status."""
        try:
            return {
                "service_healthy": True,
                "channels_configured": {
                    channel.value: bool(self._is_channel_configured(channel))
                    for channel in NotificationChannel
                },
                "rate_limits": self.rate_limits,
                "current_counts": self.message_counts,
                "history_size": len(self.notification_history)
            }
            
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {"service_healthy": False, "error": str(e)}
    
    def _is_channel_configured(self, channel: NotificationChannel) -> bool:
        """Check if a channel is properly configured."""
        try:
            if channel == NotificationChannel.EMAIL:
                return bool(self.email_config.get('sendgrid_api_key') or self.email_config.get('smtp'))
            elif channel == NotificationChannel.SMS:
                return bool(self.sms_config.get('twilio_account_sid') and self.sms_config.get('twilio_auth_token'))
            elif channel == NotificationChannel.SLACK:
                return bool(self.slack_config.get('webhook_url'))
            return False
        except Exception:
            return False
    
    async def close(self):
        """Close notification service and cleanup resources."""
        try:
            if self.http_session:
                await self.http_session.close()
            logger.info("Notification service closed")
        except Exception as e:
            logger.error(f"Error closing notification service: {e}")
