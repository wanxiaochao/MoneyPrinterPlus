"""Only save approved creative options, never the entire Streamlit session."""
import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFERENCES = ROOT / "config/workbench-preferences.json"
HISTORY = ROOT / "config/workbench-history.json"
PRESETS = {
    "竖屏口播": {"video_layout": "portrait", "video_size": "720x1280", "video_fps": 25,
                 "video_segment_min_length": 5, "video_segment_max_length": 10},
    "横屏解读": {"video_layout": "landscape", "video_size": "1280x720", "video_fps": 25,
                 "video_segment_min_length": 6, "video_segment_max_length": 12},
    "方形分享": {"video_layout": "square", "video_size": "720x720", "video_fps": 25,
                 "video_segment_min_length": 5, "video_segment_max_length": 10},
}
DEFAULTS = {"output_preset": "竖屏口播", "video_language": "zh-CN", "video_length": "120",
            "audio_type": "remote", "recognition_audio_type": "remote", "audio_language": "zh-CN",
            "audio_speed": "normal", "enable_background_music": True, "background_music_volume": 0.2,
            "background_music_dir": str(ROOT / "bgmusic"), "enable_video_transition_effect": False,
            "video_transition_effect_type": "xfade", "video_transition_effect_value": "fade",
            "video_transition_effect_duration": "1", "enable_subtitles": True,
            "subtitle_font": "PingFang SC Semibold", "subtitle_font_size": 16, "captioning_lines": 2,
            "subtitle_position": 2, "subtitle_color": "#FFFFFF", "subtitle_border_color": "#000000",
            "subtitle_border_width": 1, **PRESETS["竖屏口播"]}
ALLOWED = set(DEFAULTS) | {"audio_voice", "background_music"}


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def write_json(path, value):
    path = Path(path)
    data = json.dumps(value, ensure_ascii=False, indent=2)
    if path.exists() and path.read_text() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(data)
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def load_preferences(state, path=PREFERENCES):
    if state.get("workbench_preferences_loaded"):
        return
    values = read_json(path, {})
    if not isinstance(values, dict):
        values = {}
    for key, value in DEFAULTS.items():
        state.setdefault(key, value)
    for key, value in values.items():
        if key in ALLOWED and isinstance(value, (str, int, float, bool)):
            state[key] = value
    state["workbench_preferences_loaded"] = True


def normalize_preferences(state):
    choices = {"output_preset": tuple(PRESETS), "video_language": ("zh-CN", "zh-TW", "en"),
               "video_length": ("60", "120", "300", "600"), "audio_language": ("zh-CN", "en-US"),
               "audio_speed": ("normal", "fast", "faster", "fastest", "slow", "slower", "slowest"),
               "video_layout": ("portrait", "landscape", "square"), "video_fps": (20, 25, 30),
               "subtitle_font": ("PingFang SC Semibold", "PingFang SC Regular", "Songti SC Bold", "STSong"),
               "subtitle_font_size": (6, 8, 10, 12, 14, 16, 18, 20, 24), "captioning_lines": (1, 2),
               "subtitle_position": (2, 5, 8), "video_transition_effect_duration": ("1", "2")}
    for key, options in choices.items():
        if state.get(key) not in options:
            state[key] = DEFAULTS[key]
    for key, value in DEFAULTS.items():
        if isinstance(value, bool) and not isinstance(state.get(key), bool):
            state[key] = value
    for key in ("subtitle_color", "subtitle_border_color"):
        if not isinstance(state.get(key), str) or not re.fullmatch(r"#[a-fA-F0-9]{6}", state[key]):
            state[key] = DEFAULTS[key]
    if not isinstance(state.get("background_music_dir"), str):
        state["background_music_dir"] = DEFAULTS["background_music_dir"]
    for key, low, high, kind in (("video_segment_min_length", 5, 10, int),
                                ("video_segment_max_length", 10, 30, int),
                                ("subtitle_border_width", 0, 4, int),
                                ("background_music_volume", 0., 1., float)):
        try:
            state[key] = kind(min(high, max(low, kind(state[key]))))
        except (KeyError, TypeError, ValueError):
            state[key] = DEFAULTS[key]


def save_preferences(state, path=PREFERENCES):
    write_json(path, {key: state[key] for key in ALLOWED if key in state})


def record_video(state, video, path=HISTORY):
    records = recent_videos(path)
    row = {"subject": state.get("video_subject", ""), "category": state.get("topic_category", ""),
           "angle": state.get("topic_angle", ""), "path": video, "created_at": time.time()}
    write_json(path, [row, *[r for r in records if r["path"] != video]][:20])


def recent_videos(path=HISTORY):
    values = read_json(path, [])
    return [r for r in values if isinstance(r, dict) and isinstance(r.get("path"), str)
            and Path(r["path"]).is_file()] if isinstance(values, list) else []
