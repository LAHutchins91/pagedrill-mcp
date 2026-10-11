"""Sample documents against the verified checklists."""

import base64
import unittest
from pathlib import Path

from docx import Document
from io import BytesIO

from pagedrill.engine import dispatch
from pagedrill.errors import PagedrillRefusal
from pagedrill.profiles import require_selectable
from pagedrill.words import assert_apa_body_words

ROOT = Path(__file__).resolve().parents[2]


def load(name: str) -> str:
    return base64.b64encode((ROOT / "samples" / name).read_bytes()).decode("ascii")


class Styles(unittest.TestCase):
    def test_only_verified_styles_are_selectable(self):
        styles = dispatch({"action": "list_styles"})["result"]["styles"]
        selectable = {item["id"] for item in styles if item["selectable"]}
        self.assertEqual(selectable, {"apa7-student", "apa7-professional", "army-ar25-50-memorandum"})
        with self.assertRaises(PagedrillRefusal):
            require_selectable("mla9")

    def test_apa_student_checklist_and_word_equality(self):
        result = dispatch({"action": "format", "style_id": "apa7-student", "data_b64": load("apa_before.docx")})
        self.assertTrue(result["ok"], result.get("error"))
        counts = result["result"]["checklist"]["counts"]
        self.assertEqual(counts["FAIL"], 0)
        self.assertEqual(counts["PASS"], 28)
        flags = [row["id"] for row in result["result"]["checklist"]["rules"] if row["result"] == "FLAG"]
        self.assertEqual(flags, [11, 12, 18, 27, 31])
        self.assertTrue(result["result"]["verification"]["untouched_identical"])
        self.assertEqual(result["result"]["verification"]["added_parts"], [])
        document = Document(BytesIO(base64.b64decode(result["result"]["data_b64"])))
        blob = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertNotIn("doi:", blob.lower())
        self.assertIn("https://doi.org/10.1017/S0144686X20001932", blob)
        self.assertIn("[DATE NEEDED]", blob)
        self.assertNotIn("10.1016/j.chb.2017.02.038", blob)
        self.assertIn("[AFFILIATION NEEDED", blob)

    def test_user_supplied_values_are_used_and_not_invented(self):
        result = dispatch(
            {
                "action": "format",
                "style_id": "apa7-student",
                "data_b64": load("apa_before.docx"),
                "supplied": {
                    "affiliation": "Department of Psychology, Example University",
                    "references": [{"family": "Sanchiz", "doi": "10.1016/j.chb.2017.02.038"}],
                },
            }
        )
        self.assertTrue(result["ok"], result.get("error"))
        document = Document(BytesIO(base64.b64decode(result["result"]["data_b64"])))
        blob = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn("Department of Psychology, Example University", blob)
        self.assertIn("https://doi.org/10.1016/j.chb.2017.02.038", blob)
        self.assertIn("[DATE NEEDED]", blob)

    def test_professional_running_head_is_not_invented(self):
        result = dispatch({"action": "format", "style_id": "apa7-professional", "data_b64": load("apa_before.docx")})
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["result"]["checklist"]["counts"]["FAIL"], 0)
        document = Document(BytesIO(base64.b64decode(result["result"]["data_b64"])))
        header = document.sections[0].header.paragraphs[0].text
        self.assertIn("[RUNNING HEAD NEEDED]", header)
        self.assertNotIn("Running head:", header)
        blob = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertNotIn("PSY 201", blob)
        self.assertIn("[AUTHOR NOTE NEEDED]", blob)
        self.assertIn("Author Note", blob)

    def test_memo_checklist(self):
        result = dispatch({"action": "format", "style_id": "army-ar25-50-memorandum", "data_b64": load("memo_before.docx")})
        self.assertTrue(result["ok"], result.get("error"))
        counts = result["result"]["checklist"]["counts"]
        self.assertEqual(counts, {"PASS": 20, "FAIL": 0, "FLAG": 4})
        self.assertIn("Unclassified", result["result"]["notice"])
        document = Document(BytesIO(base64.b64decode(result["result"]["data_b64"])))
        blob = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertNotIn("Thanks for your help", blob)
        self.assertNotIn("Dear Commander", blob)
        self.assertIn("[ARIMS record no.]", blob)
        self.assertIn("[branch abbrev.: Infantry]", blob)
        self.assertTrue(result["result"]["verification"]["untouched_identical"])
        self.assertNotIn("word/header1.xml", result["result"]["verification"]["changed_parts"])

    def test_messy_check_does_not_modify_and_reports_failures(self):
        original = (ROOT / "samples" / "apa_before.docx").read_bytes()
        result = dispatch({"action": "check", "style_id": "apa7-student", "data_b64": base64.b64encode(original).decode("ascii")})
        self.assertTrue(result["ok"])
        self.assertGreater(result["result"]["checklist"]["counts"]["FAIL"], 0)
        self.assertEqual(len(result["result"]["checklist"]["rules"]), 33)
        self.assertNotIn("data_b64", result["result"])

    def test_word_change_is_refused(self):
        with self.assertRaises(PagedrillRefusal) as caught:
            assert_apa_body_words("The cat sat.", "The dog sat.", set(), set())
        self.assertEqual(caught.exception.code, "word_change")

    def test_unverified_style_is_refused(self):
        result = dispatch({"action": "format", "style_id": "ieee", "data_b64": load("apa_before.docx")})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "style_not_selectable")


if __name__ == "__main__":
    unittest.main()
