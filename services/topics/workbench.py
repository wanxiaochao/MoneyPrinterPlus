"""Category, hotspot, and angle controls shared with the AI video page."""
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from services.topics.hot_topics import ALL_CATEGORY, ANGLE_RULES, CATEGORIES, filter_topics, fingerprint, get_snapshot


def _time(value):
    return datetime.fromtimestamp(value, ZoneInfo("Asia/Shanghai")).strftime("%m-%d %H:%M:%S")


def remember_manual_subject():
    if st.session_state.get("topic_mode") == "手动输入":
        st.session_state["topic_manual_draft"] = st.session_state.get("video_subject", "")


def render_topic_picker():
    state = st.session_state
    state.setdefault("topic_manual_draft", state.get("video_subject", ""))
    with st.container(border=True):
        st.subheader("1 选择内容与热点")
        st.radio("选题方式", ("选择热点", "手动输入"), key="topic_mode", horizontal=True)
        st.selectbox("内容大类", CATEGORIES, key="topic_category")
        source = None
        if state["topic_mode"] == "选择热点":
            refresh = st.button("刷新热点", key="refresh_hot_topics")
            with st.spinner("正在获取热点..."):
                snapshot = get_snapshot(force=refresh)
            items = filter_topics(snapshot["items"], state["topic_category"])
            if snapshot["stale"]:
                st.warning("来源暂时不可用，当前显示上次成功获取的热点；获取时间保持原值。")
            st.caption(f"{state['topic_category']}：{len(items)} 条候选 · 获取时间 {_time(snapshot['collected_at'])}")
            st.caption("大类可能交叉；其他候选可以在“全部热点”中查看。")
            with st.expander("来源状态"):
                for result in snapshot["sources"]:
                    if result["ok"]:
                        st.write(f"{result['platform']}：已获取 · {_time(result['fetched_at'])}")
                    else:
                        st.write(f"{result['platform']}：未获取 · {result['error']}")
            lookup = {i["id"]: i for i in items}
            options = ["", *lookup]
            previous = state.get("topic_hot_choice", state.get("topic_selected_id", ""))
            state["topic_hot_choice"] = previous if previous in lookup else ""
            def label(value):
                if not value:
                    return "请选择一个热点"
                item = lookup[value]
                rank = f" · 榜单第{item['rank']}条" if item["rank"] is not None else " · 置顶"
                return f"{item['platform']}{rank}｜{item['title']}"
            selected = st.selectbox("选择热点", options, index=0, format_func=label,
                                    key="topic_hot_choice", disabled=not items)
            state["topic_selected_id"] = selected
            source = lookup.get(selected)
            if not items:
                st.info("这个大类暂时没有候选。可以切换大类、刷新，或使用手动输入。")
            state["video_subject"] = source["title"] if source else ""
            if source:
                details = [f"来源：{source['platform']}", f"获取时间：{_time(source['collected_at'])}"]
                for metric, title in (("hotScore", "热搜指数"), ("view", "播放"), ("like", "点赞")):
                    if metric in source["metrics"]:
                        details.append(f"{title}：{source['metrics'][metric]}")
                st.caption(" · ".join(details))
                if source["url"]:
                    st.link_button("查看原始热点", source["url"])
        elif state.get("topic_previous_mode") != "手动输入":
            state["video_subject"] = state["topic_manual_draft"]
        state["topic_previous_mode"] = state["topic_mode"]
        st.text_input("视频主题", placeholder="输入想讲的具体主题", key="video_subject",
                      disabled=state["topic_mode"] == "选择热点", on_change=remember_manual_subject)
        st.selectbox("表达角度", tuple(ANGLE_RULES), key="topic_angle")
        st.caption(ANGLE_RULES[state["topic_angle"]])
        state["hot_topic_context"] = source
        state["topic_selection_valid"] = bool(source) if state["topic_mode"] == "选择热点" else bool(state.get("video_subject", "").strip())
        current = fingerprint(state.get("video_subject", ""), state["topic_category"], state["topic_angle"], source)
        if state.get("topic_input_fingerprint") != current:
            state["video_content"] = ""
            state["video_keyword"] = ""
            state.pop("topic_script_fingerprint", None)
            state.pop("result_video_file", None)
            state.pop("topic_script_error", None)
        state["topic_input_fingerprint"] = current
        state["topic_workbench_enabled"] = True
