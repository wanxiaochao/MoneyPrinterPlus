"""Public hot lists, broad topic categories, and a short shared cache."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import html
import json
import re
import threading
import time
from urllib.parse import urlsplit

import httpx

ALL_CATEGORY = "全部热点"
CATEGORY_KEYWORDS = {
    "社会民生": ("社会", "民生", "警方", "法院", "案件", "居民", "公共", "救援", "事故", "暴雨", "地震", "洪水", "社区", "消防", "老人", "新闻", "政策", "失踪", "女子", "男子"),
    "科技数码": ("科技", "数码", "ai", "人工智能", "手机", "iphone", "芯片", "机器人", "互联网", "软件", "电脑", "华为", "小米", "模型", "航天", "卫星", "智能", "编程"),
    "财经消费": ("财经", "经济", "商业", "消费", "价格", "公司", "股市", "a股", "股票", "房价", "楼市", "银行", "金融", "降价", "涨价", "电商", "购物", "财报", "创业", "黄金", "投资", "品牌", "销售"),
    "健康运动": ("健康", "健身", "运动", "跑步", "马拉松", "睡眠", "饮食", "减脂", "医院", "医生", "感染", "营养", "足球", "篮球", "体育", "比赛", "奥运", "世界杯", "乒乓", "羽毛球", "骑行"),
    "职场教育": ("职场", "工作", "就业", "学习", "教育", "学校", "大学", "考试", "高考", "考研", "教师", "学生", "招聘", "面试", "工资", "打工", "毕业", "专业", "培训", "效率"),
    "文娱文化": ("影视", "电影", "电视剧", "综艺", "文化", "娱乐", "演唱会", "演员", "明星", "票房", "音乐", "动漫", "动画", "游戏", "文学", "博物馆", "非遗", "短剧", "导演", "歌手", "相声", "戏曲"),
    "旅行城市": ("旅行", "旅游", "城市", "出行", "交通", "高铁", "机场", "地铁", "景区", "景点", "酒店", "游客", "自驾", "露营", "机票", "航班", "文旅", "铁路", "公路"),
    "美食家居": ("美食", "烹饪", "做饭", "菜谱", "火锅", "餐厅", "小吃", "厨师", "厨房", "居家", "家居", "装修", "家电", "清洁", "收纳", "生活技巧", "咖啡", "烧烤", "水果", "美味", "食材"),
}
CATEGORIES = (ALL_CATEGORY, *CATEGORY_KEYWORDS)
ANGLE_RULES = {
    "快速解读": "先说明热点是什么，再用简洁口语解释值得关注的变化。",
    "知识科普": "围绕热点解释一个相关知识点，区分已知事实与待核实的信息。",
    "观点分析": "给出有理由的分析，明确区分事实、推测与个人观点。",
    "实用建议": "围绕热点给出具体可执行的日常建议，不夸大效果。",
}
BAIDU_URL = "https://top.baidu.com/board?tab=realtime"
BILIBILI_URL = "https://api.bilibili.com/x/web-interface/popular?ps=50&pn=1"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"


def classify(title: str, source_tag: str = "") -> list[str]:
    text = f"{title} {source_tag}".lower()
    matches = []
    for category, words in CATEGORY_KEYWORDS.items():
        if any((bool(re.search(r"(?<![a-z])ai(?![a-z])", text)) if word == "ai" else word in text) for word in words):
            matches.append(category)
    return matches


def _item(platform, title, url, rank, metrics, at, tag=""):
    title = html.unescape(str(title)).strip()
    url = str(url or "").strip()
    if url and urlsplit(url).scheme not in ("http", "https"):
        url = ""
    identity = hashlib.sha256(f"{platform}\0{title}\0{url}".encode()).hexdigest()[:20]
    return {"id": identity, "platform": platform, "title": title, "url": url,
            "rank": rank, "metrics": metrics, "collected_at": at,
            "categories": classify(title, tag)}


def parse_baidu(page: str, at: float) -> list[dict]:
    match = re.search(r"<!--s-data:\s*(.*?)\s*-->", page, re.S)
    if not match:
        raise ValueError("页面未返回可解析的热搜榜单数据")
    data = json.loads(match.group(1))
    data = data.get("data") or data
    items, position = [], 0
    for card in data.get("cards") or []:
        for row in card.get("content") or []:
            if not isinstance(row, dict):
                continue
            title = str(row.get("word") or row.get("query") or "").strip()
            if not title:
                continue
            if not row.get("isTop"):
                position += 1
            metrics = {"hotScore": row["hotScore"]} if row.get("hotScore") is not None else {}
            items.append(_item("百度热搜", title, row.get("rawUrl") or row.get("url"),
                               None if row.get("isTop") else position, metrics, at))
    return items


def parse_bilibili(body: dict, at: float) -> list[dict]:
    if body.get("code") != 0:
        raise ValueError(f"业务错误 code={body.get('code')} {body.get('message', '')}")
    items = []
    for position, row in enumerate((body.get("data") or {}).get("list") or [], 1):
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        bvid = row.get("bvid")
        stat = row.get("stat") or {}
        metrics = {k: stat[k] for k in ("view", "like", "danmaku", "coin", "favorite", "share") if k in stat}
        items.append(_item("B站热门视频", title, f"https://www.bilibili.com/video/{bvid}" if bvid else "",
                           position, metrics, at, str(row.get("tname") or "")))
    return items


def _fetch_source(name, url, parser):
    result = {"platform": name, "ok": False, "items": [], "http_status": None, "error": "", "fetched_at": None}
    try:
        r = httpx.get(url, headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/" if "bilibili" in url else BAIDU_URL,
                                   "Cache-Control": "no-cache"}, timeout=10, follow_redirects=True)
        result["http_status"] = r.status_code
        if r.status_code != 200:
            result["error"] = f"HTTP {r.status_code}"
            return result
        result["fetched_at"] = time.time()
        result["items"] = parser(r.json() if "bilibili" in url else r.text, result["fetched_at"])
        result["ok"] = bool(result["items"])
        if not result["ok"]:
            result["error"] = "来源返回 0 条有效内容"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def collect() -> dict:
    sources = [("百度热搜", BAIDU_URL, parse_baidu), ("B站热门视频", BILIBILI_URL, parse_bilibili)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda args: _fetch_source(*args), sources))
    items, seen = [], set()
    for result in results:
        for item in result["items"]:
            if item["id"] not in seen:
                items.append(item)
                seen.add(item["id"])
    return {"items": items, "sources": [{k: v for k, v in r.items() if k != "items"} for r in results],
            "collected_at": max((i["collected_at"] for i in items), default=time.time()), "stale": False}


_lock = threading.Lock()
_cache: dict = {}
_version = 0


def get_snapshot(force: bool = False) -> dict:
    global _cache, _version
    observed = _version
    if not force and _cache and time.time() - _cache["at"] < 60:
        return copy.deepcopy(_cache["snapshot"])
    with _lock:
        if _cache and (observed != _version or (not force and time.time() - _cache["at"] < 60)):
            return copy.deepcopy(_cache["snapshot"])
        fresh = collect()
        if not fresh["items"] and _cache and _cache["snapshot"]["items"]:
            fresh["items"] = _cache["snapshot"]["items"]
            fresh["collected_at"] = _cache["snapshot"]["collected_at"]
            fresh["stale"] = True
        _cache = {"snapshot": fresh, "at": time.time()}
        _version += 1
        return copy.deepcopy(fresh)


def filter_topics(items: list[dict], category: str) -> list[dict]:
    if category not in CATEGORIES:
        raise ValueError("未知内容大类")
    return list(items) if category == ALL_CATEGORY else [i for i in items if category in i["categories"]]


def fingerprint(subject: str, category: str, angle: str, source: dict | None = None) -> str:
    payload = {"subject": subject.strip(), "category": category, "angle": angle,
               "source_id": source.get("id") if source else None}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def resolve_selection(state: dict, items: list[dict] | None = None):
    category = state.get("topic_category", ALL_CATEGORY)
    angle = state.get("topic_angle", "快速解读")
    if category not in CATEGORIES or angle not in ANGLE_RULES:
        raise ValueError("请重新选择内容大类与表达角度。")
    if state.get("topic_mode") == "手动输入":
        subject = str(state.get("video_subject") or "").strip()
        if not subject:
            raise ValueError("请先填写视频主题。")
        source = None
    else:
        selected = state.get("topic_hot_choice")
        source = next((i for i in filter_topics(items or [], category) if i["id"] == selected), None)
        if source is None:
            raise ValueError("请先选择一个当前大类的热点；列表更新后可能需要重新选择。")
        subject = source["title"]
    return subject, source, fingerprint(subject, category, angle, source)
