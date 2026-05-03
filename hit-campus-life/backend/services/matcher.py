from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from models import BuddyTask, User
from services.llm_client import call_openai_compatible_chat


def normalize(value: str | None) -> str:
    return (value or "").strip().lower().replace("，", ",").replace("#", ",")


def split_tags(value: str | None) -> set[str]:
    text = normalize(value)
    if not text:
        return set()
    return {item.strip() for item in re.split(r"[,、\s]+", text) if item.strip()}


def keywords(*values: str | None) -> set[str]:
    result: set[str] = set()
    for value in values:
        text = normalize(value)
        result |= split_tags(text)
        result |= {item for item in re.split(r"[^\w\u4e00-\u9fff]+", text) if len(item) >= 2}
    return result


def fuzzy_overlap(left: set[str], right_text: str | None) -> set[str]:
    text = normalize(right_text)
    if not text:
        return set()
    right = keywords(text)
    matched: set[str] = set()
    for token in left:
        if token in right or token in text:
            matched.add(token)
            continue
        if any(token in other or other in token for other in right if len(other) >= 2):
            matched.add(token)
    return matched


def field_score(query_value: str | None, task_value: str | None, points: int) -> tuple[int, bool]:
    query_tokens = keywords(query_value)
    if not query_tokens:
        return 0, False
    matched = fuzzy_overlap(query_tokens, task_value)
    if matched:
        return points, True
    return 0, False


@dataclass
class MatchResult:
    task: BuddyTask
    score: int
    reason: str
    detail: list[dict[str, int | str]]
    llm_reason: str | None = None


def rule_match(user: User, task: BuddyTask, query: dict) -> MatchResult:
    user_tags = split_tags(user.interests)
    query_tags = split_tags(query.get("tags", ""))
    task_tags = split_tags(task.tags)
    query_words = keywords(query.get("goal"), query.get("description"), query.get("tags"))
    task_text = " ".join([task.goal or "", task.title or "", task.description or "", task.tags or ""])

    score = 20
    reasons: list[str] = []
    detail: list[dict[str, int | str]] = [{"name": "基础可沟通", "points": 20, "text": "所有开放任务都先进入候选池"}]

    common_user_task = user_tags & task_tags
    if common_user_task:
        pts = min(24, 8 * len(common_user_task))
        score += pts
        reasons.append(f"兴趣重合：{'、'.join(sorted(common_user_task))}")
        detail.append({"name": "兴趣标签", "points": pts, "text": f"与你的资料标签重合：{'、'.join(sorted(common_user_task))}"})

    common_query_task = query_tags & task_tags
    if common_query_task:
        pts = min(30, 10 * len(common_query_task))
        score += pts
        reasons.append(f"需求标签命中：{'、'.join(sorted(common_query_task))}")
        detail.append({"name": "本次需求", "points": pts, "text": f"和你输入的标签重合：{'、'.join(sorted(common_query_task))}"})

    keyword_hits = fuzzy_overlap(query_words, task_text)
    if keyword_hits:
        hits = sorted(keyword_hits)[:4]
        pts = min(24, 6 * len(keyword_hits))
        score += pts
        reasons.append(f"关键词接近：{'、'.join(hits)}")
        detail.append({"name": "关键词语义", "points": pts, "text": f"目标、描述或标题中命中：{'、'.join(hits)}"})

    place_pts, place_hit = field_score(query.get("place") or user.location_preference, task.place, 10)
    time_pts, time_hit = field_score(query.get("time_slot") or user.schedule_preference, task.time_slot, 10)
    score += place_pts + time_pts
    if place_hit:
        reasons.append("地点偏好接近")
        detail.append({"name": "地点偏好", "points": place_pts, "text": f"你偏好的地点接近 {task.place}"})
    if time_hit:
        reasons.append("时间段接近")
        detail.append({"name": "时间偏好", "points": time_pts, "text": f"你偏好的时间接近 {task.time_slot}"})

    if task.creator_id == user.id:
        score -= 35
        reasons.append("这是你自己发布的任务，仅作为参考")
        detail.append({"name": "自己发布", "points": -35, "text": "自己发布的任务会降低排序"})

    score = max(0, min(99, score))
    if not reasons:
        reasons.append("基础信息可沟通，建议查看任务详情后确认")
    return MatchResult(task=task, score=score, reason="；".join(reasons), detail=detail)


def match_tasks(user: User, tasks: Iterable[BuddyTask], query: dict, use_llm: bool = True) -> list[MatchResult]:
    candidates = [
        rule_match(user, task, query)
        for task in tasks
        if task.is_open and task.creator_id != user.id
    ]
    candidates.sort(key=lambda item: item.score, reverse=True)
    top = candidates[:8]

    if use_llm and top:
        compact = [
            {
                "id": item.task.id,
                "title": item.task.title,
                "goal": item.task.goal,
                "place": item.task.place,
                "time": item.task.time_slot,
                "tags": item.task.tags,
                "rule_score": item.score,
            }
            for item in top[:5]
        ]
        prompt = (
            "请根据用户需求和候选任务给出匹配建议。要求：不编造信息；"
            "每个候选任务最多一句理由；指出最适合的前2个。\n"
            f"用户信息：姓名={user.name}，兴趣={user.interests}，地点偏好={user.location_preference}，时间偏好={user.schedule_preference}\n"
            f"用户本次需求：{query}\n候选任务：{compact}"
        )
        explanation = call_openai_compatible_chat(prompt)
        if explanation:
            top[0].llm_reason = explanation

    return top
