#  Copyright © [2024] 程序那些事
#
#  All rights reserved. This software and associated documentation files (the "Software") are provided for personal and educational use only. Commercial use of the Software is strictly prohibited unless explicit permission is obtained from the author.
#
#  Permission is hereby granted to any person to use, copy, and modify the Software for non-commercial purposes, provided that the following conditions are met:
#
#  1. The original copyright notice and this permission notice must be included in all copies or substantial portions of the Software.
#  2. Modifications, if any, must retain the original copyright information and must not imply that the modified version is an official version of the Software.
#  3. Any distribution of the Software or its modifications must retain the original copyright notice and include this permission notice.
#
#  For commercial use, including but not limited to selling, distributing, or using the Software as part of any commercial product or service, you must obtain explicit authorization from the author.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHOR OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#  Author: 程序那些事
#  email: flydean@163.com
#  Website: [www.flydean.com](http://www.flydean.com)
#  GitHub: [https://github.com/ddean2009/MoneyPrinterPlus](https://github.com/ddean2009/MoneyPrinterPlus)
#
#  All rights reserved.
#
#

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from config.config import my_config, config_example_file, languages, audio_languages, transition_types, fade_list
from main import main_generate_video_content, main_generate_video_keywords, main_generate_ai_video, main_try_test_audio, get_audio_voices
from pages.common import common_ui, page_header
from services.topics.automation import run_generation, text_digest
from services.topics.hot_topics import get_snapshot
from services.topics.preferences import PRESETS, load_preferences, normalize_preferences, save_preferences, record_video, recent_videos
from services.topics.workbench import render_topic_picker
from services.topics.workflow import script_configuration_error, media_configuration_error, audio_configuration_error, safe_error
from tools.file_utils import read_yaml
from tools.utils import get_file_map_from_dir

example_config = read_yaml(config_example_file)
common_ui()
load_preferences(st.session_state)
normalize_preferences(st.session_state)
page_header("热点短视频工作台")
st.caption("选一个主题，自动完成文案、素材关键词、配音、字幕和视频。")


def request_generation(mode):
    st.session_state["workbench_request"] = mode


def accept_draft():
    state = st.session_state
    if state.get("video_content", "").strip():
        state["topic_script_fingerprint"] = state.get("topic_input_fingerprint")
        state["topic_script_options"] = {key: state.get(key) for key in ("video_language", "video_length")}
    else:
        state.pop("topic_script_fingerprint", None)
    state.pop("topic_keywords_digest", None)


def accept_keywords():
    st.session_state["topic_keywords_digest"] = text_digest(st.session_state.get("video_content"))


def apply_preset():
    st.session_state.update(PRESETS[st.session_state["output_preset"]])


def sync_language():
    st.session_state["audio_language"] = "en-US" if st.session_state["video_language"] == "en" else "zh-CN"
    st.session_state.pop("audio_voice", None)


def try_audio():
    try:
        error = audio_configuration_error(my_config, example_config)
        if error:
            raise ValueError(error)
        main_try_test_audio()
    except Exception as exc:
        st.session_state["topic_script_error"] = safe_error(exc, my_config)


request = st.session_state.pop("workbench_request", None)
if request:
    with st.status("正在制作" if request == "video" else "正在生成文案", expanded=True) as status:
        try:
            result = run_generation(st.session_state, my_config, example_config, get_snapshot,
                                    main_generate_video_content, main_generate_video_keywords,
                                    lambda: main_generate_ai_video(st.container()), mode=request,
                                    notify=st.write)
            if result:
                try:
                    record_video(st.session_state, result)
                except OSError:
                    st.caption("视频已生成，本次未能写入历史记录。")
            st.session_state.pop("topic_script_error", None)
            status.update(label="视频已生成" if result else "文案已生成", state="complete", expanded=False)
        except Exception as exc:
            st.session_state["topic_script_error"] = safe_error(exc, my_config)
            status.update(label="需要处理后重试", state="error", expanded=False)

errors = [e for e in (script_configuration_error(my_config, example_config),
                      media_configuration_error(my_config, example_config)) if e]
with st.container(border=True):
    st.caption(f"文案 {my_config['llm']['provider']}  ·  素材 {my_config['resource']['provider'].title()}  ·  配音 {my_config['audio']['provider']}")
    if errors:
        with st.expander("首次使用：完成云端服务配置", expanded=False):
            for error in errors:
                st.write(error)
            st.page_link("pages/00_settings.py", label="打开模型与服务设置", icon="⚙️")
    else:
        st.caption("服务信息已填写，可开始制作；实际可用性以生成结果为准。")

if st.session_state.get("topic_script_error"):
    st.error(st.session_state["topic_script_error"])

creative, options = st.columns([1.65, 1], gap="large")
with creative:
    render_topic_picker()

with options:
    with st.container(border=True):
        st.subheader("2 成片设置")
        if st.session_state.get("output_preset") not in PRESETS:
            st.session_state["output_preset"] = "竖屏口播"
        st.selectbox("视频预设", tuple(PRESETS), key="output_preset", on_change=apply_preset)
        st.selectbox("文案语言", tuple(languages), format_func=languages.get,
                     key="video_language", on_change=sync_language)
        lengths = {"60": "约 15 秒 · 60 字", "120": "约 30 秒 · 120 字", "300": "约 1 分钟 · 300 字", "600": "长解读 · 600 字"}
        st.selectbox("口播长度", tuple(lengths), format_func=lengths.get, key="video_length")
        st.caption("时长为估算，实际以配音和正文长度为准。")
        st.session_state["audio_type"] = "remote"
        st.session_state["recognition_audio_type"] = "remote"
        voices = (get_audio_voices() or {}).get(st.session_state["audio_language"], {})
        if st.session_state.get("audio_voice") not in voices:
            st.session_state["audio_voice"] = next(iter(voices), None)
        st.selectbox("配音声音", tuple(voices), format_func=voices.get, key="audio_voice")
        subtitle, music = st.columns(2)
        with subtitle:
            st.checkbox("自动字幕", key="enable_subtitles")
        with music:
            st.checkbox("背景音乐", key="enable_background_music")
        st.caption("设置会自动记住，下次打开无需重复填写。")

    with st.expander("高级设置", expanded=False):
        voice_tab, video_tab, subtitle_tab, music_tab = st.tabs(["配音", "画面", "字幕", "音乐"])
        with voice_tab:
            st.selectbox("配音语言", tuple(audio_languages), format_func=audio_languages.get, key="audio_language")
            st.selectbox("配音语速", ("normal", "fast", "faster", "fastest", "slow", "slower", "slowest"), key="audio_speed")
            st.button("试听声音", on_click=try_audio, use_container_width=True)
        with video_tab:
            layouts = {"portrait": "竖屏", "landscape": "横屏", "square": "方形"}
            st.selectbox("画面比例", tuple(layouts), format_func=layouts.get, key="video_layout")
            sizes = {"portrait": {"720x1280": "720p", "1080x1920": "1080p"},
                     "landscape": {"1280x720": "720p", "1920x1080": "1080p"},
                     "square": {"720x720": "720p", "1080x1080": "1080p"}}[st.session_state["video_layout"]]
            if st.session_state.get("video_size") not in sizes:
                st.session_state["video_size"] = next(iter(sizes))
            st.selectbox("清晰度", tuple(sizes), format_func=sizes.get, key="video_size")
            st.selectbox("帧率", (20, 25, 30), key="video_fps")
            st.slider("素材片段最短秒数", 5, 10, key="video_segment_min_length")
            st.slider("素材片段最长秒数", 10, 30, key="video_segment_max_length")
            st.checkbox("启用转场", key="enable_video_transition_effect")
            st.selectbox("转场方式", transition_types, key="video_transition_effect_type")
            st.selectbox("转场效果", fade_list, key="video_transition_effect_value")
            st.selectbox("转场秒数", ("1", "2"), key="video_transition_effect_duration")
        with subtitle_tab:
            st.selectbox("字幕字体", ("PingFang SC Semibold", "PingFang SC Regular", "Songti SC Bold", "STSong"), key="subtitle_font")
            st.selectbox("字幕字号", (6, 8, 10, 12, 14, 16, 18, 20, 24), key="subtitle_font_size")
            st.selectbox("字幕行数", (1, 2), key="captioning_lines")
            positions = {2: "下方居中", 5: "画面中心", 8: "上方居中"}
            st.selectbox("字幕位置", tuple(positions), format_func=positions.get, key="subtitle_position")
            st.color_picker("文字颜色", key="subtitle_color")
            st.color_picker("描边颜色", key="subtitle_border_color")
            st.slider("描边宽度", 0, 4, key="subtitle_border_width")
        with music_tab:
            st.text_input("音乐目录", key="background_music_dir")
            music_files = get_file_map_from_dir(st.session_state["background_music_dir"], ".mp3,.wav")
            if st.session_state.get("background_music") not in music_files:
                st.session_state["background_music"] = next(iter(music_files), None)
            st.selectbox("音乐文件", tuple(music_files), format_func=music_files.get, key="background_music")
            st.slider("背景音乐音量", 0.0, 1.0, step=0.1, key="background_music_volume")

with st.container(border=True):
    st.subheader("3 开始制作")
    st.caption("一键生成会沿用你修改过的文案，并自动补齐素材关键词。")
    primary, secondary = st.columns([1.25, 1])
    with primary:
        st.button("一键生成视频", key="generate_video", type="primary", use_container_width=True,
                  disabled=not st.session_state.get("topic_selection_valid"),
                  on_click=request_generation, args=("video",))
    with secondary:
        st.button("生成视频文案", key="generate_draft", use_container_width=True,
                  disabled=not st.session_state.get("topic_selection_valid"),
                  on_click=request_generation, args=("draft",))
    with st.expander("查看或修改文案", expanded=bool(st.session_state.get("video_content"))):
        st.text_area("口播文案", key="video_content", height=180, on_change=accept_draft,
                     placeholder="可先生成文案检查，也可以直接一键制作。")
        st.text_input("英文素材关键词（自动生成，可修改）", key="video_keyword", on_change=accept_keywords)
        st.caption("重新点击“生成视频文案”会重写正文；一键生成会保留当前正文。")

result = st.session_state.get("result_video_file")
if result and Path(result).is_file():
    with st.container(border=True):
        st.subheader("成片预览")
        st.video(result)
        st.download_button("下载视频", Path(result).read_bytes(), file_name=Path(result).name,
                           mime="video/mp4", use_container_width=True)
        st.caption(str(Path(result).resolve()))
records = recent_videos()
if records:
    with st.expander(f"最近成片 · {len(records)} 条", expanded=False):
        labels = {r["path"]: f"{datetime.fromtimestamp(r['created_at'], ZoneInfo('Asia/Shanghai')).strftime('%m-%d %H:%M')}  {r['subject']}" for r in records}
        chosen = st.selectbox("历史视频", tuple(labels), format_func=labels.get, key="history_video")
        if chosen != result:
            st.video(chosen)
        st.caption(chosen)


try:
    save_preferences(st.session_state)
except OSError:
    st.caption("当前设置可用，本次未能保存到磁盘。")
