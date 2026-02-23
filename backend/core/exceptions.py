"""Application-level exceptions."""


class PolicySystemError(Exception):
    """Base exception for all policy system errors."""


class AuthenticationError(PolicySystemError):
    """Raised when authentication fails (bad credentials, expired token)."""


class AuthorizationError(PolicySystemError):
    """Raised when a user attempts an action they are not permitted to do."""


class DocumentNotFoundError(PolicySystemError):
    """Raised when a requested document does not exist in the database."""


class UserNotFoundError(PolicySystemError):
    """Raised when a requested user does not exist."""


class RoleNotFoundError(PolicySystemError):
    """Raised when a requested role does not exist."""


class IngestError(PolicySystemError):
    """Raised when document parsing or chunking fails."""


class RAGProviderError(PolicySystemError):
    """Raised when the vector store operation fails."""


class LLMProviderError(PolicySystemError):
    """Raised when the LLM service is unavailable or returns an error."""


class ValidationError(PolicySystemError):
    """Raised when input validation fails at the service layer."""


class FeedbackError(PolicySystemError):
    """Raised when feedback submission is invalid (e.g., thumbs-down without comment)."""
