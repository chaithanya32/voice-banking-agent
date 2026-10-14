
import pytest

from app.services.payee_matcher import match_payee


def test_match_payee_ignores_case_and_extra_spaces():
    payee = match_payee("  ravi   kumar ")

    assert payee.payee_id == "P001"
    assert payee.name == "Ravi Kumar"


def test_match_payee_is_case_insensitive():
    assert match_payee("PRIYA SHARMA").payee_id == "P002"


@pytest.mark.parametrize("name", ["", "Unknown Person", "Ravi"])
def test_reject_unknown_or_incomplete_payee(name):
    with pytest.raises(ValueError):
        match_payee(name)
