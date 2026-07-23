from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PlayerPlaceholderAdvisoryTests(unittest.TestCase):
    def test_current_placeholder_layout_conventions(self) -> None:
        scene = (ROOT / "scenes/actors/player.tscn").read_text(encoding="utf-8")

        self.assertIn("player_placeholder_directional.png", scene)
        self.assertEqual(scene.count('atlas = ExtResource("2_player_placeholder")'), 16)
        self.assertEqual(scene.count("region = Rect2("), 16)
        self.assertIn("Rect2(0, 0, 18, 26)", scene)
        self.assertIn("Rect2(18, 182, 18, 26)", scene)


if __name__ == "__main__":
    unittest.main()
