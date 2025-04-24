class ToolError(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self, message):
        self.message = message


class HeyFunsError(Exception):
    """Base exception for all HeyFuns errors"""


class TokenLimitExceeded(HeyFunsError):
    """Exception raised when the token limit is exceeded"""
