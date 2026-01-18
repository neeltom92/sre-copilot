"""
AWS SQS integration tools for SRE Copilot.

Provides read-only tools for:
- Listing SQS queues
- Getting queue attributes (message count, age, etc.)
- Peeking at messages (without removing them)
- Getting dead-letter queue statistics
"""

from dataclasses import dataclass
from typing import Any, Optional, List
import json


@dataclass
class SQSTools:
    """AWS SQS tools for SRE operations (read-only)."""

    aws_region: str = "us-east-1"
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    aws_profile: Optional[str] = None
    _client: Any = None

    def __post_init__(self):
        """Initialize AWS SQS client lazily."""
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError

            session_kwargs = {}
            if self.aws_profile:
                session_kwargs["profile_name"] = self.aws_profile

            session = boto3.Session(**session_kwargs)

            client_kwargs = {"region_name": self.aws_region}
            if self.aws_access_key and self.aws_secret_key:
                client_kwargs["aws_access_key_id"] = self.aws_access_key
                client_kwargs["aws_secret_access_key"] = self.aws_secret_key

            self._client = session.client("sqs", **client_kwargs)

            # Test connection
            try:
                self._client.list_queues(MaxResults=1)
            except (NoCredentialsError, ClientError) as e:
                self._client = None
                print(f"AWS credentials not configured or invalid: {e}")
        except ImportError:
            print("boto3 not installed. Install with: pip install boto3")
            self._client = None

    def _ensure_client(self) -> bool:
        """Ensure SQS client is initialized."""
        return self._client is not None

    def _handle_error(self, e: Exception, operation: str = "operation") -> dict:
        """Handle errors and return user-friendly messages."""
        error_str = str(e)

        try:
            from botocore.exceptions import NoCredentialsError, ClientError

            if isinstance(e, NoCredentialsError):
                return {
                    "error": "AWS credentials not configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, "
                            "configure AWS CLI, or use IAM roles."
                }

            if isinstance(e, ClientError):
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get("Message", str(e))

                if error_code == "AccessDenied":
                    return {"error": f"Access denied. Check IAM permissions for SQS: {error_message}"}
                elif error_code == "InvalidAddress":
                    return {"error": f"Invalid queue URL or region: {error_message}"}

                return {"error": f"AWS SQS error ({error_code}): {error_message}"}
        except ImportError:
            pass

        return {"error": f"Failed to {operation}: {error_str}"}

    def list_queues(
        self,
        queue_name_prefix: Optional[str] = None,
        max_results: int = 100,
    ) -> dict:
        """
        List SQS queues.

        Args:
            queue_name_prefix: Filter queues by name prefix
            max_results: Maximum number of queues to return (1-1000)

        Returns:
            List of queue URLs and names
        """
        if not self._ensure_client():
            return {"error": "AWS SQS client not configured"}

        try:
            params = {"MaxResults": min(max_results, 1000)}
            if queue_name_prefix:
                params["QueueNamePrefix"] = queue_name_prefix

            response = self._client.list_queues(**params)
            queue_urls = response.get("QueueUrls", [])

            return {
                "queues": [
                    {
                        "url": url,
                        "name": url.split("/")[-1],
                    }
                    for url in queue_urls
                ],
                "count": len(queue_urls),
            }

        except Exception as e:
            return self._handle_error(e, "list queues")

    def get_queue_attributes(
        self,
        queue_url: str,
    ) -> dict:
        """
        Get queue attributes and statistics.

        Args:
            queue_url: SQS queue URL

        Returns:
            Queue attributes including message counts, age, etc.
        """
        if not self._ensure_client():
            return {"error": "AWS SQS client not configured"}

        try:
            response = self._client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=["All"],
            )

            attrs = response.get("Attributes", {})

            result = {
                "queue_url": queue_url,
                "queue_name": queue_url.split("/")[-1],
                "metrics": {
                    "approximate_messages": int(attrs.get("ApproximateNumberOfMessages", 0)),
                    "approximate_messages_delayed": int(attrs.get("ApproximateNumberOfMessagesDelayed", 0)),
                    "approximate_messages_not_visible": int(attrs.get("ApproximateNumberOfMessagesNotVisible", 0)),
                },
                "configuration": {
                    "visibility_timeout_seconds": int(attrs.get("VisibilityTimeout", 0)),
                    "message_retention_seconds": int(attrs.get("MessageRetentionPeriod", 0)),
                    "max_message_size_bytes": int(attrs.get("MaximumMessageSize", 0)),
                    "delay_seconds": int(attrs.get("DelaySeconds", 0)),
                },
                "timestamps": {
                    "created": attrs.get("CreatedTimestamp"),
                    "last_modified": attrs.get("LastModifiedTimestamp"),
                },
            }

            # Add age of oldest message if available
            if "ApproximateAgeOfOldestMessage" in attrs:
                age_seconds = int(attrs["ApproximateAgeOfOldestMessage"])
                result["metrics"]["oldest_message_age_seconds"] = age_seconds
                result["metrics"]["oldest_message_age_minutes"] = round(age_seconds / 60, 2)
                result["metrics"]["oldest_message_age_hours"] = round(age_seconds / 3600, 2)

            # Add DLQ info if available
            if "RedrivePolicy" in attrs:
                try:
                    redrive_policy = json.loads(attrs["RedrivePolicy"])
                    result["dead_letter_queue"] = {
                        "target_arn": redrive_policy.get("deadLetterTargetArn"),
                        "max_receive_count": redrive_policy.get("maxReceiveCount"),
                    }
                except json.JSONDecodeError:
                    pass

            # Check if this is a FIFO queue
            result["is_fifo"] = attrs.get("FifoQueue", "false").lower() == "true"
            if result["is_fifo"]:
                result["fifo_config"] = {
                    "content_based_deduplication": attrs.get("ContentBasedDeduplication", "false").lower() == "true",
                    "deduplication_scope": attrs.get("DeduplicationScope"),
                    "fifo_throughput_limit": attrs.get("FifoThroughputLimit"),
                }

            return result

        except Exception as e:
            return self._handle_error(e, "get queue attributes")

    def peek_messages(
        self,
        queue_url: str,
        max_messages: int = 10,
        wait_time_seconds: int = 0,
    ) -> dict:
        """
        Peek at messages in a queue without removing them.

        Messages are received with visibility timeout of 0, meaning they
        become immediately visible again for other consumers.

        Args:
            queue_url: SQS queue URL
            max_messages: Maximum messages to peek at (1-10)
            wait_time_seconds: Long polling wait time (0-20 seconds)

        Returns:
            List of messages with body and attributes
        """
        if not self._ensure_client():
            return {"error": "AWS SQS client not configured"}

        try:
            response = self._client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max(1, max_messages), 10),
                WaitTimeSeconds=min(max(0, wait_time_seconds), 20),
                VisibilityTimeout=0,  # Messages remain visible (peek only)
                AttributeNames=["All"],
                MessageAttributeNames=["All"],
            )

            messages = response.get("Messages", [])

            parsed_messages = []
            for msg in messages:
                body = msg.get("Body", "")
                # Try to parse body as JSON for display
                try:
                    body_parsed = json.loads(body)
                except json.JSONDecodeError:
                    body_parsed = body

                attrs = msg.get("Attributes", {})

                parsed_messages.append({
                    "message_id": msg.get("MessageId"),
                    "body": body_parsed,
                    "body_raw": body[:1000] + "..." if len(body) > 1000 else body,
                    "md5_of_body": msg.get("MD5OfBody"),
                    "sent_timestamp": attrs.get("SentTimestamp"),
                    "approximate_receive_count": int(attrs.get("ApproximateReceiveCount", 0)),
                    "approximate_first_receive_timestamp": attrs.get("ApproximateFirstReceiveTimestamp"),
                    "sender_id": attrs.get("SenderId"),
                    "message_attributes": {
                        k: v.get("StringValue") or v.get("BinaryValue")
                        for k, v in msg.get("MessageAttributes", {}).items()
                    },
                })

            return {
                "queue_url": queue_url,
                "queue_name": queue_url.split("/")[-1],
                "messages": parsed_messages,
                "count": len(parsed_messages),
                "note": "Messages peeked with visibility_timeout=0 (not removed from queue)",
            }

        except Exception as e:
            return self._handle_error(e, "peek messages")

    def get_queue_url(
        self,
        queue_name: str,
        account_id: Optional[str] = None,
    ) -> dict:
        """
        Get the URL of a queue by its name.

        Args:
            queue_name: Name of the queue
            account_id: AWS account ID (optional, for cross-account access)

        Returns:
            Queue URL
        """
        if not self._ensure_client():
            return {"error": "AWS SQS client not configured"}

        try:
            params = {"QueueName": queue_name}
            if account_id:
                params["QueueOwnerAWSAccountId"] = account_id

            response = self._client.get_queue_url(**params)

            return {
                "queue_name": queue_name,
                "queue_url": response.get("QueueUrl"),
            }

        except Exception as e:
            return self._handle_error(e, "get queue URL")


# Tool definitions for LangChain
SQS_TOOLS = [
    {
        "name": "sqs_list_queues",
        "description": "List AWS SQS queues. Use this to discover available queues or find a specific queue by name prefix.",
        "input_schema": {
            "type": "object",
            "properties": {
                "queue_name_prefix": {
                    "type": "string",
                    "description": "Filter queues by name prefix (optional)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of queues to return (default: 100, max: 1000)",
                    "default": 100,
                },
            },
        },
    },
    {
        "name": "sqs_get_queue_attributes",
        "description": "Get detailed queue attributes and statistics including message counts, age of oldest message, visibility timeout, and dead-letter queue configuration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "queue_url": {
                    "type": "string",
                    "description": "SQS queue URL",
                },
            },
            "required": ["queue_url"],
        },
    },
    {
        "name": "sqs_peek_messages",
        "description": "Peek at messages in a queue WITHOUT removing them (read-only). Messages remain visible for other consumers. Use to inspect queue contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "queue_url": {
                    "type": "string",
                    "description": "SQS queue URL",
                },
                "max_messages": {
                    "type": "integer",
                    "description": "Maximum messages to peek at (1-10, default: 10)",
                    "default": 10,
                },
                "wait_time_seconds": {
                    "type": "integer",
                    "description": "Long polling wait time in seconds (0-20, default: 0)",
                    "default": 0,
                },
            },
            "required": ["queue_url"],
        },
    },
    {
        "name": "sqs_get_queue_url",
        "description": "Get the URL of a queue by its name. Useful when you know the queue name but need the full URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "queue_name": {
                    "type": "string",
                    "description": "Name of the SQS queue",
                },
                "account_id": {
                    "type": "string",
                    "description": "AWS account ID (optional, for cross-account access)",
                },
            },
            "required": ["queue_name"],
        },
    },
]
