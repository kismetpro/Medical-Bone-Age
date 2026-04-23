import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "backend" / "app" / "utils" / "rus_chn.py"
)
SPEC = importlib.util.spec_from_file_location("rus_chn", MODULE_PATH)
rus_chn = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(rus_chn)


class TestRUSScoring(unittest.TestCase):
    def test_joint_specific_stage_mapping_is_preserved(self):
        self.assertEqual(rus_chn.normalize_rus_stage(11, "DIPThird", "male"), 11)
        self.assertEqual(rus_chn.normalize_rus_stage(12, "Ulna", "female"), 12)
        self.assertEqual(rus_chn.normalize_rus_stage(14, "Radius", "male"), 14)

    def test_stage_mapping_is_clamped_without_global_rescaling(self):
        self.assertEqual(rus_chn.normalize_rus_stage(14, "DIPThird", "male"), 11)
        self.assertEqual(rus_chn.normalize_rus_stage(-3, "MCPThird", "female"), 0)
        self.assertEqual(rus_chn.normalize_rus_stage(None, "Radius", "female"), 0)

    def test_calc_rus_score_uses_direct_joint_stage_lookup(self):
        aligned = {
            joint: {
                "grade_raw": 0,
                "score": 0.0,
                "imputed": False,
                "source_joint": joint,
            }
            for joint in rus_chn.RUS_13
        }
        aligned["DIPThird"]["grade_raw"] = 11

        total_score, details = rus_chn.calc_rus_score(aligned, "male")
        dip_third = next(item for item in details if item["joint"] == "DIPThird")

        self.assertEqual(dip_third["stage"], 11)
        self.assertEqual(dip_third["score"], 49)
        self.assertEqual(total_score, 49)


if __name__ == "__main__":
    unittest.main()
