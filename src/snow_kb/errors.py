"""errors.py — Custom exception classes for the pipeline."""


class MissingAssignmentGroupError(Exception):
    """Raised when the assignment_group field is not filled in on the Story."""

    pass
