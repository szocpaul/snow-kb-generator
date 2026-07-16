"""errors.py — Egyedi hibaosztályok a pipeline számára."""


class MissingAssignmentGroupError(Exception):
    """Akkor dobódik, ha a Story-n nincs kitöltve az assignment_group mező."""

    pass
