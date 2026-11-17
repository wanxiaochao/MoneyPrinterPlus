import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from services.topics.automation import run_generation, text_digest
from services.topics.hot_topics import fingerprint
from services.topics.preferences import load_preferences, normalize_preferences, save_preferences, record_video, recent_videos
from services.topics.workflow import parse_script_result


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "mock-video.mp4"
        self.config = {"llm": {"provider": "DeepSeek", "DeepSeek": {"api_key": "user-key"}},
                       "resource": {"provider": "pexels", "pexels": {"api_key": "user-material"}},
                       "audio": {"provider": "Azure", "Azure": {"speech_key": "user-audio", "service_region": "eastasia"}}}
        self.state = {"topic_mode": "手动输入", "video_subject": "厨房收纳怎么做", "topic_category": "美食家居",
                      "topic_angle": "实用建议", "video_content": "", "video_keyword": ""}
        def script():
            self.state.update(video_content="测试口播", video_keyword="kitchen")
        def keywords():
            self.state["video_keyword"] = "storage"
        def video():
            self.output.write_bytes(b"mock video result for unit testing")
            self.state["result_video_file"] = str(self.output)
        self.script, self.keywords, self.video = Mock(side_effect=script), Mock(side_effect=keywords), Mock(side_effect=video)

    def run_workflow(self, mode="video"):
        return run_generation(self.state, self.config, {}, lambda: {"items": []}, self.script, self.keywords, self.video, mode)

    def adopt_draft(self):
        self.state["video_content"] = "我自己修改过的口播"
        self.state["topic_script_fingerprint"] = fingerprint(self.state["video_subject"], "美食家居", "实用建议")

    def test_one_click_generates_script_and_video(self):
        self.assertEqual(self.run_workflow(), str(self.output.resolve()))
        self.script.assert_called_once()
        self.video.assert_called_once()
        self.keywords.assert_not_called()

    def test_media_preflight_happens_before_paid_model_request(self):
        self.config["resource"]["pexels"]["api_key"] = ""
        with self.assertRaisesRegex(ValueError, "素材"):
            self.run_workflow()
        self.script.assert_not_called()
        self.video.assert_not_called()

    def test_draft_generation_does_not_require_material_or_audio(self):
        self.config["resource"]["pexels"]["api_key"] = ""
        self.assertIsNone(self.run_workflow("draft"))
        self.script.assert_called_once()
        self.video.assert_not_called()

    def test_user_edited_draft_is_kept_and_keywords_are_updated(self):
        self.adopt_draft()
        self.run_workflow()
        self.assertEqual(self.state["video_content"], "我自己修改过的口播")
        self.script.assert_not_called()
        self.keywords.assert_called_once()

    def test_prepared_draft_avoids_model_requests(self):
        self.adopt_draft()
        self.state["video_keyword"] = "storage"
        self.state["topic_keywords_digest"] = text_digest(self.state["video_content"])
        self.config["llm"]["DeepSeek"]["api_key"] = ""
        self.run_workflow()
        self.script.assert_not_called()
        self.keywords.assert_not_called()

    def test_changed_angle_regenerates_old_draft(self):
        self.adopt_draft()
        self.state["topic_angle"] = "知识科普"
        self.run_workflow()
        self.script.assert_called_once()

    def test_missing_hot_selection_never_uses_previous_subject(self):
        self.state["topic_mode"] = "选择热点"
        with self.assertRaisesRegex(ValueError, "热点"):
            self.run_workflow()
        self.script.assert_not_called()

    def test_failed_video_cannot_display_old_artifact_as_success(self):
        self.state["result_video_file"] = "/old/video.mp4"
        self.state["return_videos"] = ["/old/material.mp4"]
        self.video.side_effect = None
        with self.assertRaisesRegex(RuntimeError, "未产生有效视频"):
            self.run_workflow()
        self.assertNotIn("result_video_file", self.state)
        self.assertNotIn("return_videos", self.state)

    def test_invalid_model_json_is_rejected(self):
        for raw in ("普通文字", "{}", '{"narration":"","keywords":["gym"]}',
                    '{"narration":"测试","keywords":["中文"]}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_script_result(raw)
        self.assertEqual(parse_script_result('```json\n{"narration":"测试","keywords":["gym", "running"]}\n```'), ("测试", "gym, running"))

    def test_preferences_only_store_creative_settings(self):
        path = Path(self.directory.name) / "preferences.json"
        state = {"video_length": "120", "DeepSeek_api_key": "never-save-me", "video_content": "private-draft"}
        save_preferences(state, path)
        self.assertEqual(json.loads(path.read_text()), {"video_length": "120"})
        loaded = {}
        load_preferences(loaded, path)
        self.assertEqual(loaded["video_length"], "120")

    def test_corrupt_and_unsupported_preferences_use_valid_defaults(self):
        path = Path(self.directory.name) / "preferences.json"
        path.write_text("corrupt")
        state = {}
        load_preferences(state, path)
        state.update(video_fps=900, subtitle_font="unknown", subtitle_color="invalid", subtitle_position=10)
        normalize_preferences(state)
        self.assertEqual(state["video_fps"], 25)
        self.assertEqual(state["subtitle_position"], 2)
        self.assertEqual(state["subtitle_color"], "#FFFFFF")

    def test_history_records_only_successful_existing_outputs(self):
        path = Path(self.directory.name) / "history.json"
        self.output.write_bytes(b"mock")
        self.state["DeepSeek_api_key"] = "never-save-me"
        record_video(self.state, str(self.output), path)
        record_video(self.state, str(self.output), path)
        self.assertEqual(len(recent_videos(path)), 1)
        self.assertNotIn("never-save-me", path.read_text())


if __name__ == "__main__":
    unittest.main()
