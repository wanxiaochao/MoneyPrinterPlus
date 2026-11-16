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

import streamlit as st

from config.config import my_config, save_config, languages, audio_languages, transition_types, \
    fade_list, audio_types, load_session_state_from_yaml, save_session_state_to_yaml, app_title, GPT_soVITS_languages, CosyVoice_voice
from main import main_generate_video_content, main_generate_ai_video, main_generate_video_dubbing, \
    main_get_video_resource, main_generate_subtitle, main_try_test_audio, get_audio_voices, main_try_test_local_audio, \
    main_generate_ai_video_from_img
from pages.common import common_ui
from services.topics.workbench import render_topic_picker
from services.topics.hot_topics import get_snapshot, resolve_selection
from services.topics.workflow import audio_configuration_error, media_configuration_error, script_configuration_error, safe_error
from tools.file_utils import read_yaml
from config.config import config_example_file

example_config = read_yaml(config_example_file)
from tools.tr_utils import tr

import os

from tools.utils import get_file_map_from_dir

# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

# print("当前脚本的绝对路径是:", script_path)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)

default_bg_music_dir = os.path.join(script_dir, "../bgmusic")
default_bg_music_dir = os.path.abspath(default_bg_music_dir)

default_chattts_dir = os.path.join(script_dir, "../chattts")
default_chattts_dir = os.path.abspath(default_chattts_dir)

load_session_state_from_yaml('01_first_visit')


def save_to_config(region, key):
    value = st.session_state.get(key)
    if value:
        if not my_config[region]:
            my_config[region] = {}
        my_config[region][key] = value
        save_config()


common_ui()


def get_video_resource():
    main_get_video_resource()


def generate_subtitle():
    main_generate_subtitle()


def prepare_subject():
    items = get_snapshot()["items"] if st.session_state.get("topic_mode") == "选择热点" else []
    subject, source, current = resolve_selection(st.session_state, items)
    st.session_state["video_subject"] = subject
    st.session_state["hot_topic_context"] = source
    st.session_state["topic_input_fingerprint"] = current
    return current


def generate_video_content():
    try:
        prepare_subject()
        error = script_configuration_error(my_config, example_config)
        if error:
            st.session_state["topic_script_error"] = error
            return
        st.session_state.pop("topic_script_fingerprint", None)
        main_generate_video_content()
        st.session_state.pop("topic_script_error", None)
    except Exception as exc:
        st.session_state["topic_script_error"] = "文案生成失败：" + safe_error(exc, my_config)


def generate_video_dubbing():
    main_generate_video_dubbing()


def try_test_audio():
    error = audio_configuration_error(my_config, example_config)
    if error:
        st.error(error)
        return
    try:
        main_try_test_audio()
    except Exception as exc:
        st.error("配音试听失败：" + safe_error(exc, my_config))


def try_test_local_audio():
    main_try_test_local_audio()


def generate_video(video_generator):
    try:
        current = prepare_subject()
        if st.session_state.get("topic_script_fingerprint") != current:
            st.error("当前选题或表达角度已变化，请先生成这条选题的文案。")
            return
        error = media_configuration_error(my_config, example_config)
        if error:
            st.error(error)
            return
        save_session_state_to_yaml()
        main_generate_ai_video(video_generator)
    except Exception as exc:
        st.error("视频生成失败：" + safe_error(exc, my_config))


st.title("热点短视频工作台")
st.caption("选大类与热点 → 云端文案 → 真实素材与云端配音 → 预览导出")
render_topic_picker()

# LLM区域
llm_container = st.container(border=True)
with llm_container:
    st.subheader("2 生成与修改文案")
    st.caption(f"文案引擎：{my_config['llm']['provider']} · 围绕已选主题与表达角度生成")
    error = script_configuration_error(my_config, example_config)
    if error:
        st.warning(error)
        st.page_link("pages/00_settings.py", label="打开模型与服务设置")
    if st.session_state.get("topic_script_error"):
        st.error(st.session_state["topic_script_error"])
    llm_columns = st.columns(3)
    video_length_options = {"60": "60字以内", "120": "120字以内", "300": "300字以内", "600": "600字以内"}
    # video_length_options = {"60": "60字以内", "120": "120字以内", "300": "300字以内"}
    with llm_columns[0]:
        st.selectbox(label=tr("Video content language"), options=languages, format_func=lambda x: languages.get(x),
                     key="video_language")
    with llm_columns[1]:
        st.selectbox(label="口播长度", options=video_length_options,
                     format_func=lambda x: video_length_options.get(x), key="video_length")
        # print(st.session_state.get("video_length"))
    with llm_columns[2]:
        st.button(label=tr("Generate Video Content"), type="primary", on_click=generate_video_content)
    # print(st.session_state.get("video_content"))
    st.text_area(label=tr("Video content"), key="video_content", height=200)
    st.text_input(label=tr("Video content keyword"), key="video_keyword")

# 资源区
resource_container = st.container(border=True)
with resource_container:
    st.subheader(tr("Video Source"))
    resource_name = my_config['resource'].get('provider', '')
    st.text(tr("Using Resource:") + resource_name)
    if resource_name not in ("pexels", "pixabay"):
        st.warning("请选择 Pexels 或 Pixabay 真实素材库。")
        st.page_link("pages/00_settings.py", label="打开素材库设置")

# 配音区域
st.session_state["audio_type"] = "remote"
st.session_state["recognition_audio_type"] = "remote"
captioning_container = st.container(border=True)
with captioning_container:
    # 配音
    st.subheader(tr("Video Captioning"))

    llm_columns = st.columns(4)
    with llm_columns[0]:
        st.selectbox(label=tr("Choose TTS audio type"), options=("remote",), format_func=lambda x: audio_types.get(x),
                     key="audio_type")

    if st.session_state.get("audio_type") == "remote":
        llm_columns = st.columns(4)
        audio_voice = get_audio_voices()
        with llm_columns[0]:
            st.selectbox(label=tr("Audio language"), options=audio_languages,
                         format_func=lambda x: audio_languages.get(x), key="audio_language")
        with llm_columns[1]:
            voice_options = audio_voice.get(st.session_state.get("audio_language"), {})
            st.selectbox(label=tr("Audio voice"),
                         options=voice_options,
                         format_func=voice_options.get,
                         key="audio_voice")
        with llm_columns[2]:
            st.selectbox(label=tr("Audio speed"),
                         options=["normal", "fast", "faster", "fastest", "slow", "slower", "slowest"],
                         key="audio_speed")
        with llm_columns[3]:
            st.button(label=tr("Testing Audio"), type="primary", on_click=try_test_audio)
recognition_container = st.container(border=True)
with recognition_container:
    # 配音
    st.subheader(tr("Audio recognition"))

    llm_columns = st.columns(4)
    with llm_columns[0]:
        st.selectbox(label=tr("Choose recognition type"), options=("remote",), format_func=lambda x: audio_types.get(x),
                     key="recognition_audio_type")

# 背景音乐
bg_music_container = st.container(border=True)
with bg_music_container:
    # 背景音乐
    st.subheader(tr("Video Background Music"))
    llm_columns = st.columns(2)
    with llm_columns[0]:
        st.text_input(label=tr("Background Music Dir"), placeholder=tr("Input Background Music Dir"),
                      value=default_bg_music_dir,
                      key="background_music_dir")

    with llm_columns[1]:
        nest_columns = st.columns(3)
        with nest_columns[0]:
            st.checkbox(label=tr("Enable background music"), key="enable_background_music", value=True)
        with nest_columns[1]:
            bg_music_list = get_file_map_from_dir(st.session_state["background_music_dir"], ".mp3,.wav")
            st.selectbox(label=tr("Background music"), key="background_music",
                         options=bg_music_list, format_func=lambda x: bg_music_list[x])
        with nest_columns[2]:
            st.slider(label=tr("Background music volume"), min_value=0.0, value=0.3, max_value=1.0, step=0.1,
                      key="background_music_volume")

# 视频配置
video_container = st.container(border=True)

with video_container:
    st.subheader(tr("Video Config"))
    llm_columns = st.columns(3)
    with llm_columns[0]:
        layout_options = {"portrait": "竖屏", "landscape": "横屏", "square": "方形"}
        st.selectbox(label=tr("video layout"), key="video_layout", options=layout_options,
                     format_func=lambda x: layout_options[x])
    with llm_columns[1]:
        st.selectbox(label=tr("video fps"), key="video_fps", options=[20, 25, 30])
    with llm_columns[2]:
        if st.session_state.get("video_layout") == "portrait":
            video_size_options = {"1080x1920": "1080p", "720x1280": "720p", "480x960": "480p", "360x720": "360p",
                                  "240x480": "240p"}
        elif st.session_state.get("video_layout") == "landscape":
            video_size_options = {"1920x1080": "1080p", "1280x720": "720p", "960x480": "480p", "720x360": "360p",
                                  "480x240": "240p"}
        else:
            video_size_options = {"1080x1080": "1080p", "720x720": "720p", "480x480": "480p", "360x360": "360p",
                                  "240x240": "240p"}
        st.selectbox(label=tr("video size"), key="video_size", options=video_size_options,
                     format_func=lambda x: video_size_options[x])
    llm_columns = st.columns(2)
    with llm_columns[0]:
        st.slider(label=tr("video segment min length"), min_value=5, value=5, max_value=10, step=1,
                  key="video_segment_min_length")
    with llm_columns[1]:
        st.slider(label=tr("video segment max length"), min_value=10, value=10, max_value=30, step=1,
                  key="video_segment_max_length")
    # 开启本地目录
    # llm_columns = st.columns(2)
    # with llm_columns[0]:
    #     st.checkbox(label=tr("Enable local video dir"), key="enable_local_video_dir", value=False)
    # with llm_columns[1]:
    #     st.text_input(label=tr("local video dir"), key="local_video_dir")
    llm_columns = st.columns(4)
    with llm_columns[0]:
        st.checkbox(label=tr("Enable video Transition effect"), key="enable_video_transition_effect", value=True)
    with llm_columns[1]:
        st.selectbox(label=tr("video Transition effect"), key="video_transition_effect_type", options=transition_types)
    with llm_columns[2]:
        st.selectbox(label=tr("video Transition effect types"), key="video_transition_effect_value", options=fade_list)
    with llm_columns[3]:
        st.selectbox(label=tr("video Transition effect duration"), key="video_transition_effect_duration",
                     options=["1", "2"])

# 字幕
subtitle_container = st.container(border=True)
with subtitle_container:
    st.subheader(tr("Video Subtitles"))
    llm_columns = st.columns(4)
    with llm_columns[0]:
        st.checkbox(label=tr("Enable subtitles"), key="enable_subtitles", value=True)
    with llm_columns[1]:
        st.selectbox(label=tr("subtitle font"), key="subtitle_font",
                     options=["Songti SC Bold",
                              "Songti SC Black",
                              "Songti SC Light",
                              "STSong",
                              "Songti SC Regular",
                              "PingFang SC Regular",
                              "PingFang SC Medium",
                              "PingFang SC Semibold",
                              "PingFang SC Light",
                              "PingFang SC Thin",
                              "PingFang SC Ultralight"], )
    with llm_columns[2]:
        st.selectbox(label=tr("subtitle font size"), key="subtitle_font_size", index=1,
                     options=[4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24])
    with llm_columns[3]:
        st.selectbox(label=tr("subtitle lines"), key="captioning_lines", index=1,
                     options=[1, 2])

    llm_columns = st.columns(4)
    with llm_columns[0]:
        subtitle_position_options = {5: "top left",
                                     6: "top center",
                                     7: "top right",
                                     9: "center left",
                                     10: "center",
                                     11: "center right",
                                     1: "bottom left",
                                     2: "bottom center",
                                     3: "bottom right"}
        st.selectbox(label=tr("subtitle position"), key="subtitle_position", index=7,
                     options=subtitle_position_options, format_func=lambda x: subtitle_position_options[x])
    with llm_columns[1]:
        st.color_picker(label=tr("subtitle color"), key="subtitle_color", value="#FFFFFF")
    with llm_columns[2]:
        st.color_picker(label=tr("subtitle border color"), key="subtitle_border_color", value="#000000")
    with llm_columns[3]:
        st.slider(label=tr("subtitle border width"), min_value=0, value=0, max_value=4, step=1,
                  key="subtitle_border_width")

# 生成视频
video_generator = st.container(border=True)
with video_generator:
    st.button(label=tr("Generate Video Button"), type="primary", on_click=generate_video, args=(video_generator,))
result_video_file = st.session_state.get("result_video_file")
if result_video_file:
    st.video(result_video_file)
