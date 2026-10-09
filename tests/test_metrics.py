import pytest
from ledger_htr.metrics import edit_distance, normalize, score


def ref(id="line-1", text="Cash 300 20", **kwargs):
    return {"id": id, "page_id": "page-1", "split": "test", "kind": "amount", "text": text,
            "reviewed": True, "reviewer": "test-fixture", **kwargs}


@pytest.mark.parametrize("a,b,expected", [("kitten", "sitting", 3), ("", "abc", 3), ("abc", "", 3),
                                         ("1844", "1844", 0), ("300 20", "300 28", 1)])
def test_known_edit_distances(a, b, expected):
    assert edit_distance(a, b) == expected


def test_micro_average_and_missing_predictions():
    result = score([ref(text="abc"), ref("line-2", "abcdefghij")], [{"id": "line-1", "text": "abx"}])
    assert result["overall"]["character_errors"] == 11
    assert result["overall"]["reference_characters"] == 13
    assert result["overall"]["cer"] == pytest.approx(11 / 13)
    assert result["overall"]["coverage"] == .5
    assert result["details"][1]["missing"] is True


def test_insertions_can_exceed_one_hundred_percent():
    assert score([ref(text="a")], [{"id": "line-1", "text": "abcde"}])["overall"]["cer"] == 4


def test_normalization_preserves_financial_notation_and_case():
    assert normalize("  Cash\n 300  20 ") == "Cash 300 20"
    assert normalize('300 "') != normalize("300 00")
    assert normalize("Cash") != normalize("cash")
    assert normalize("300.20") != normalize("30020")
    assert normalize("e\u0301") == "é"


def test_unreviewed_labels_cannot_silently_be_ground_truth():
    references = [ref(reviewed=False, reviewer=None)]
    with pytest.raises(ValueError, match="No eligible"):
        score(references, [])
    result = score(references, [], include_unreviewed=True)
    assert result["scope"] == "exploratory-unreviewed"


def test_uncertain_reference_is_excluded_even_in_exploratory_mode():
    result = score([ref(), ref("line-2", uncertain=True)], [], include_unreviewed=True)
    assert result["excluded_reference_count"] == 1
    assert result["overall"]["count"] == 1


def test_page_level_leakage_fails():
    with pytest.raises(ValueError, match="Page leakage"):
        score([ref(), ref("line-2", split="dev")], [])


@pytest.mark.parametrize("predictions", [[{"id": "unknown", "text": "x"}],
                                        [{"id": "line-1", "text": "x"}, {"id": "line-1", "text": "x"}]])
def test_unknown_and_duplicate_predictions_fail(predictions):
    with pytest.raises(ValueError):
        score([ref()], predictions)


def test_review_requires_attribution():
    with pytest.raises(ValueError, match="reviewer"):
        score([ref(reviewer=None)], [])


def test_digit_component_metric_does_not_claim_full_amount_correctness():
    result = score([ref(text="300 20"), ref("line-2", '750 "')],
                   [{"id": "line-1", "text": "300.20"}, {"id": "line-2", "text": "75000"}])
    assert result["by_kind"]["amount"]["exact_match"] == 0
    assert result["amount_digit_sequence"]["eligible_count"] == 1
    assert result["amount_digit_sequence"]["rate"] == 1
