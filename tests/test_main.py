from datetime import datetime
import unittest

from src.main import ForecastError, build_view_model, render_page


FORECAST_PAYLOAD = [
    {
        "publishingOffice": "横浜地方気象台",
        "reportDatetime": "2026-03-27T11:00:00+09:00",
        "timeSeries": [
            {
                "timeDefines": [
                    "2026-03-27T00:00:00+09:00",
                    "2026-03-28T00:00:00+09:00",
                    "2026-03-29T00:00:00+09:00",
                ],
                "areas": [
                    {
                        "area": {"name": "東部", "code": "140010"},
                        "weatherCodes": ["112", "201", "101"],
                        "weathers": [
                            "晴れ のち くもり 夜遅く 雨",
                            "くもり 昼前から夕方 晴れ",
                            "晴れ 時々 くもり",
                        ],
                    },
                    {
                        "area": {"name": "西部", "code": "140020"},
                        "weatherCodes": ["114", "201", "101"],
                        "weathers": [
                            "晴れ のち くもり 夜 雨",
                            "くもり 昼前から夕方 晴れ",
                            "晴れ 時々 くもり",
                        ],
                    },
                ],
            },
            {
                "timeDefines": [
                    "2026-03-27T12:00:00+09:00",
                    "2026-03-27T18:00:00+09:00",
                    "2026-03-28T00:00:00+09:00",
                    "2026-03-28T06:00:00+09:00",
                    "2026-03-28T12:00:00+09:00",
                    "2026-03-28T18:00:00+09:00",
                ],
                "areas": [
                    {
                        "area": {"name": "東部", "code": "140010"},
                        "pops": ["10", "50", "30", "10", "10", "10"],
                    },
                    {
                        "area": {"name": "西部", "code": "140020"},
                        "pops": ["20", "50", "30", "10", "10", "10"],
                    },
                ],
            },
            {
                "timeDefines": [
                    "2026-03-27T09:00:00+09:00",
                    "2026-03-27T00:00:00+09:00",
                    "2026-03-28T00:00:00+09:00",
                    "2026-03-28T09:00:00+09:00",
                ],
                "areas": [
                    {
                        "area": {"name": "横浜", "code": "46106"},
                        "temps": ["18", "18", "12", "19"],
                    },
                    {
                        "area": {"name": "小田原", "code": "46166"},
                        "temps": ["19", "19", "10", "19"],
                    },
                ],
            },
        ],
    },
    {
        "publishingOffice": "横浜地方気象台",
        "reportDatetime": "2026-03-27T11:00:00+09:00",
        "timeSeries": [
            {
                "timeDefines": [
                    "2026-03-28T00:00:00+09:00",
                    "2026-03-29T00:00:00+09:00",
                    "2026-03-30T00:00:00+09:00",
                ],
                "areas": [
                    {
                        "area": {"name": "神奈川県", "code": "140000"},
                        "weatherCodes": ["201", "101", "200"],
                        "pops": ["", "20", "40"],
                        "reliabilities": ["", "", "B"],
                    }
                ],
            },
            {
                "timeDefines": [
                    "2026-03-28T00:00:00+09:00",
                    "2026-03-29T00:00:00+09:00",
                    "2026-03-30T00:00:00+09:00",
                ],
                "areas": [
                    {
                        "area": {"name": "横浜", "code": "46106"},
                        "tempsMin": ["", "11", "12"],
                        "tempsMax": ["", "20", "20"],
                    }
                ],
            },
        ],
    },
]

OVERVIEW_PAYLOAD = {
    "text": "晴れベースで推移。\n<script>alert('xss')</script>",
}


class BuildViewModelTests(unittest.TestCase):
    def test_build_view_model_extracts_weekly_rows(self) -> None:
        view_model = build_view_model(FORECAST_PAYLOAD, OVERVIEW_PAYLOAD)

        self.assertEqual(view_model["publishing_office"], "横浜地方気象台")
        self.assertEqual(len(view_model["weekly_rows"]), 3)
        self.assertEqual(view_model["weekly_rows"][0]["summary"], "くもり 昼前から夕方 晴れ")
        self.assertEqual(view_model["weekly_rows"][1]["summary"], "晴れ 時々 くもり")
        self.assertEqual(view_model["weekly_rows"][2]["summary"], "Cloudy")
        self.assertEqual(view_model["weekly_rows"][2]["reliability"], "B")

    def test_render_page_escapes_remote_text(self) -> None:
        view_model = build_view_model(FORECAST_PAYLOAD, OVERVIEW_PAYLOAD)

        html = render_page(view_model)

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert('xss')&lt;/script&gt;", html)
        self.assertIn(
            f"Copyright {datetime.now().year} Kanagawa Weekly Weather Viewer",
            html,
        )

    def test_build_view_model_rejects_invalid_payload(self) -> None:
        with self.assertRaises(ForecastError):
            build_view_model([{"timeSeries": []}], OVERVIEW_PAYLOAD)


if __name__ == "__main__":
    unittest.main()
