"""Optional provider adapters; importing them never makes a network request."""
from .base import IntegrationError, JsonApiClient
from .github import GitHubClient
from .graph import MicrosoftGraphClient
from .jira import JiraClient
from .servicenow import ServiceNowClient
from .snipeit import SnipeITClient
from .workday import WorkdayClient

__all__ = ["IntegrationError", "JsonApiClient", "GitHubClient",
           "MicrosoftGraphClient", "JiraClient", "ServiceNowClient",
           "SnipeITClient", "WorkdayClient"]
