"""Run the cloud workflow, preserving edited drafts and avoiding stale media."""
import hashlib
from pathlib import Path

from services.topics.hot_topics import resolve_selection
from services.topics.workflow import media_configuration_error, script_configuration_error


def text_digest(text):
    return hashlib.sha256(str(text or "").strip().encode()).hexdigest()


def run_generation(state, config, example, snapshot, make_script, make_keywords, make_video,
                   mode="video", notify=lambda message: None):
    if mode not in ("video", "draft"):
        raise ValueError("未知生成操作")
    items = snapshot()["items"] if state.get("topic_mode") == "选择热点" else []
    subject, source, current = resolve_selection(state, items)
    state["video_subject"] = subject
    state["hot_topic_context"] = source
    state["topic_input_fingerprint"] = current
    # Check every required service before generating a paid script for a video.
    if mode == "video":
        error = media_configuration_error(config, example)
        if error:
            raise ValueError(error)
    script_options = {key: state.get(key) for key in ("video_language", "video_length")}
    reuse = (mode == "video" and state.get("topic_script_fingerprint") == current
             and state.get("topic_script_options", script_options) == script_options
             and str(state.get("video_content") or "").strip())
    needs_keywords = (state.get("topic_keywords_digest") != text_digest(state.get("video_content"))
                      or not str(state.get("video_keyword") or "").strip())
    if not reuse or needs_keywords:
        error = script_configuration_error(config, example)
        if error:
            raise ValueError(error)
    if not reuse:
        notify("生成口播文案和素材关键词")
        make_script()
    elif needs_keywords or not str(state.get("video_keyword") or "").strip():
        notify("保留已修改文案，更新素材关键词")
        make_keywords()
    else:
        notify("沿用当前文案和素材关键词")
    if not str(state.get("video_content") or "").strip():
        raise ValueError("文案服务返回了空内容，请重新生成。")
    if not str(state.get("video_keyword") or "").strip():
        raise ValueError("素材关键词为空，请重新生成文案或填写英文关键词。")
    state["topic_script_fingerprint"] = current
    state["topic_script_options"] = script_options
    state["topic_keywords_digest"] = text_digest(state["video_content"])
    if mode == "draft":
        return None
    for key in ("audio_output_file", "captioning_output", "return_videos", "result_video_file"):
        state.pop(key, None)
    notify("自动配音、字幕、素材匹配和视频合成")
    make_video()
    result = state.get("result_video_file")
    if not result or not Path(result).is_file() or not Path(result).stat().st_size:
        state.pop("result_video_file", None)
        raise RuntimeError("这次生成未产生有效视频，请查看生成步骤中的错误后重试。")
    return str(Path(result).resolve())
