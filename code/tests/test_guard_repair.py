"""The lenient parser used by the UNGUARDED arm only."""

from __future__ import annotations

from l1guard.repair import lenient_parse


def test_valid_json_needs_no_repair():
    obj, repairs, err = lenient_parse('{"operations": []}')
    assert obj == {"operations": []}
    assert repairs == [] and err is None


def test_a_code_fence_is_stripped():
    obj, repairs, err = lenient_parse('```json\n{"operations": []}\n```')
    assert obj == {"operations": []}
    assert repairs == ["strip_code_fence"]


def test_a_fence_without_a_language_tag_is_stripped():
    obj, repairs, _ = lenient_parse("```\n{\"operations\": []}\n```")
    assert obj == {"operations": []} and repairs == ["strip_code_fence"]


def test_prose_around_the_object_is_discarded():
    text = 'Sure! Here is the plan:\n{"operations": [{"op": "freeze"}]}\nHope that helps.'
    obj, repairs, _ = lenient_parse(text)
    assert obj == {"operations": [{"op": "freeze"}]}
    assert repairs == ["extract_first_object"]


def test_a_trailing_comma_is_removed():
    obj, repairs, _ = lenient_parse('{"operations": [1, 2,],}')
    assert obj == {"operations": [1, 2]}
    assert repairs == ["extract_first_object", "strip_trailing_commas"]


def test_a_bare_array_is_wrapped_in_the_envelope():
    obj, repairs, _ = lenient_parse('[{"op": "freeze", "order_id": "A"}]')
    assert obj == {"operations": [{"op": "freeze", "order_id": "A"}]}
    assert repairs == ["wrap_bare_array"]


def test_a_fenced_bare_array_is_stripped_then_wrapped():
    obj, repairs, _ = lenient_parse('```json\n[{"op": "freeze", "order_id": "A"}]\n```')
    assert obj == {"operations": [{"op": "freeze", "order_id": "A"}]}
    assert repairs == ["strip_code_fence", "wrap_bare_array"]


def test_a_brace_inside_a_string_does_not_end_the_object():
    obj, _repairs, _ = lenient_parse('noise {"operations": [], "note": "a } brace"} tail')
    assert obj["note"] == "a } brace"


def test_prose_with_no_json_at_all_is_not_repairable():
    obj, repairs, err = lenient_parse("I am sorry, I cannot do that.")
    assert obj is None and repairs == [] and err


def test_bytes_input_is_decoded():
    obj, repairs, _ = lenient_parse(b'{"operations": []}')
    assert obj == {"operations": []} and repairs == []


def test_an_object_passes_through_untouched():
    obj, repairs, err = lenient_parse({"operations": []})
    assert obj == {"operations": []} and repairs == [] and err is None


def test_the_repair_list_is_ordered_by_application():
    _obj, repairs, _ = lenient_parse('```json\n{"operations": [1,],}\n```')
    assert repairs == ["strip_code_fence", "extract_first_object", "strip_trailing_commas"]
