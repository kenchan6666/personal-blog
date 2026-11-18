"""Locale migration: fill gaps and fix wrong-script text, never clobber."""

from app.scripts.fill_locales import fix_field, plan_document


def test_simplified_in_hant_is_converted_and_hans_filled():
    out, notes = fix_field({"zh-Hant": "面积计算项目", "en": "Area"}, None, None)
    assert out == {"zh-Hant": "面積計算項目", "zh-Hans": "面积计算项目", "en": "Area"}
    assert "script-fix:zh-Hant" in notes and "fill:zh-Hans" in notes


def test_correct_text_and_existing_english_untouched():
    field = {"zh-Hant": "使用websocket爲主", "zh-Hans": "使用websocket为主", "en": "Mainly websocket"}
    out, notes = fix_field(field, "IGNORED", None)
    assert out == field and notes == []


def test_known_segmentation_error_is_patched():
    out, _ = fix_field({"zh-Hans": "房间的长宽和面积"}, None, None)
    assert out["zh-Hant"] == "房間的長寬和面積"


def test_plan_document_walks_nested_labels():
    doc = {"_id": 1, "links": [{"label": {"zh-Hant": "GitHub"}, "url": "x"}]}
    new, changes = plan_document("site_profile", doc)
    assert new["links"][0]["label"]["zh-Hans"] == "GitHub"
    assert new["_id"] == 1 and changes
