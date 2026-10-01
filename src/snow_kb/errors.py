"""errors.py — Custom exception classes for the pipeline."""


class MissingAssignmentGroupError(Exception):
    """Raised when the assignment_group field is not filled in on the Story."""

    pass


class VerificationBlocked(Exception):
    """The verification gate with behavior=block prevented the KB write.

    In spec 014 it lived in pipeline.py; in spec 015 (US3) it moved together with
    the gate into the component that performs the write (servicenow_client) — this
    same exception signals the block regardless of the call path.
    """

    pass
