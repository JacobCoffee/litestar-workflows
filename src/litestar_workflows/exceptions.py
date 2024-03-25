"""Internal exceptions to be checked against internally or raised by the user."""


class WorkflowsError(Exception):
    """Base exception class to be raised by the user or internally for ``litestar-workflows`` errors.

    .. note:: This class should not be raised directly, but should be subclassed.
    """
