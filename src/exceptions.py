class BadDeedError(Exception):
    """
    Base class for all deed validation errors.
    Used to catch all domain-specific failures at the top level.
    """
    pass


class LLMParseError(BadDeedError):
    """
    Raised when the LLM fails to return valid, expected structured data.
    """
    pass


class UnknownCountyError(BadDeedError):
    """
    Raised when a county from the deed cannot be confidently matched
    to reference data.
    """
    pass


class InvalidDateOrderError(BadDeedError):
    """
    Raised when the recorded date is earlier than the signed date.
    """
    def __init__(self, signed_date, recorded_date):
        message = (
            f"Invalid date order: recorded date ({recorded_date}) "
            f"is earlier than signed date ({signed_date})"
        )
        super().__init__(message)


class AmountMismatchError(BadDeedError):
    """
    Raised when numeric and textual monetary amounts do not match.
    """
    def __init__(self, numeric_amount, textual_amount):
        message = (
            f"Amount mismatch: numeric amount ({numeric_amount}) "
            f"does not match textual amount ({textual_amount})"
        )
        super().__init__(message)
