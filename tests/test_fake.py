"""Fake placeholder test."""


def return_three() -> int:
    """Fake placeholder function."""
    return 3


def test_return_three() -> None:
    """The best test you've ever seen."""
    assert return_three() == 3
