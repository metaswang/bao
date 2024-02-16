class RagRetrieverException(Exception):
    """Base class for exceptions related to the Rag Retriever."""

    def __init__(self, message: str):
        """Initializes the exception with a message.

        Args:
          message: A human-readable description of the error.
        """
        super().__init__(message)


class RagRetrieverConnectionError(RagRetrieverException):
    """Exception raised when there is an error connecting to the Rag Retriever service."""

    def __init__(self, message: str):
        super().__init__(f"Connection error: {message}")


class RagRetrieverQueryError(RagRetrieverException):
    """Exception raised when there is an error with the query submitted to the Rag Retriever service."""

    def __init__(self, message: str):
        super().__init__(f"Query error: {message}")


class RagRetrieverResponseError(RagRetrieverException):
    """Exception raised when there is an error with the response received from the Rag Retriever service."""

    def __init__(self, message: str):
        super().__init__(f"Response error: {message}")
