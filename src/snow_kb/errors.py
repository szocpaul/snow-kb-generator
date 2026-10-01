"""errors.py — Egyedi hibaosztályok a pipeline számára."""


class MissingAssignmentGroupError(Exception):
    """Akkor dobódik, ha a Story-n nincs kitöltve az assignment_group mező."""

    pass


class VerificationBlocked(Exception):
    """A verification gate behavior=block miatt blokkolta a KB-írást.

    Spec 014-ben a pipeline.py-ban élt; spec 015 (US3) a gate-tel együtt az
    írást végző komponensbe (servicenow_client) költözött — a hívási útaktól
    függetlenül ugyanez a kivétel jelzi a blokkot.
    """

    pass
