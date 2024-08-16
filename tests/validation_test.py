import pytest

from launchflow.validation import validate_environment_name


def test_environment_name_to_short():
    with pytest.raises(ValueError):
        validate_environment_name("")


def test_environment_name_to_long():
    with pytest.raises(ValueError):
        validate_environment_name("a" * 16)


def test_environment_name_invalid_characters():
    with pytest.raises(ValueError):
        validate_environment_name("invalid_environment_name!")


def test_environment_name_reserved():
    with pytest.raises(ValueError):
        validate_environment_name("local")
