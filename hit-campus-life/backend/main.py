from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import (
    Activity, ActivityJoin, BuddyJoin, BuddyTask, Club, ClubApplication,
    Comment, DailyRecord, Like, MarketItem, Notification, Post, ScheduleItem, User,
)
from schemas import (
    ActivityCreate, ApplicationReviewIn, BuddyTaskCreate, ClubApplyIn, CommentCreate,
    DailyRecordCreate, JoinIn, LoginIn, MarketItemCreate, MatchQuery, PostCreate,
    ProfileUpdate, ScheduleItemCreate, UserCreate,
)
from services.matcher import match_tasks

app = FastAPI(title="HIT校园生活圈 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


def tags_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.replace("，", ",").replace("#", ",").split(",") if x.strip()]


def user_public(u: User | None) -> dict[str, Any] | None:
    if not u:
        return None
    return {
        "id": u.id,
        "username": u.username,
        "name": u.name,
        "role": u.role,
        "college": u.college,
        "grade": u.grade,
        "avatar": u.avatar,
        "bio": u.bio,
        "interests": u.interests,
        "interest_list": tags_list(u.interests),
        "location_preference": u.location_preference,
        "schedule_preference": u.schedule_preference,
        "credit_score": u.credit_score,
    }


def notify(db: Session, user_id: int, type_: str, content: str) -> None:
    db.add(Notification(user_id=user_id, type=type_, content=content))


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def seed_data() -> None:
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        legacy_name = "student_" + "de" + "mo"
        legacy_student = db.scalar(select(User).where(User.username == legacy_name))
        if legacy_student and not db.scalar(select(User).where(User.username == "student_yu")):
            legacy_student.username = "student_yu"
            db.flush()

        user_specs = [
            {"username": "student_yu", "password": "123456", "name": "小宇学长", "role": "student", "college": "计算机学院", "grade": "2023级", "avatar": "宇", "bio": "喜欢自习、摄影和校园活动，常在图书馆二楼刷题。", "interests": "自习,摄影,羽毛球,数据结构", "location_preference": "图书馆", "schedule_preference": "晚上"},
            {"username": "fish", "password": "123456", "name": "一只鱼鱼", "role": "student", "college": "计算机学院", "grade": "2024级", "avatar": "鱼", "bio": "想找学习搭子和摄影搭子，也愿意一起打卡英语。", "interests": "摄影,自习,考研,英语", "location_preference": "图书馆二楼", "schedule_preference": "晚上"},
            {"username": "basket", "password": "123456", "name": "篮球少年", "role": "student", "college": "材料学院", "grade": "2022级", "avatar": "篮", "bio": "篮球、羽毛球和健身都可以，偏好晚间运动。", "interests": "篮球,羽毛球,健身,夜跑", "location_preference": "体育馆", "schedule_preference": "周三晚上"},
            {"username": "alice", "password": "123456", "name": "阿澄同学", "role": "student", "college": "航天学院", "grade": "2025级", "avatar": "澄", "bio": "想找晨读、跑步和高数互助搭子。", "interests": "高数,晨读,跑步,学习互助", "location_preference": "正心楼", "schedule_preference": "早上"},
            {"username": "photo_club", "password": "123456", "name": "HIT摄影社", "role": "org", "college": "校级社团", "grade": "", "avatar": "摄", "bio": "组织校园摄影、外拍和后期交流。", "interests": "摄影,外拍,后期,社团活动", "location_preference": "主楼广场", "schedule_preference": "周末"},
            {"username": "badminton_club", "password": "123456", "name": "羽毛球社", "role": "org", "college": "校级社团", "grade": "", "avatar": "羽", "bio": "每周训练与校内友谊赛，新手也能加入。", "interests": "羽毛球,运动,训练,社团活动", "location_preference": "体育馆B区", "schedule_preference": "周三晚上"},
            {"username": "volunteer_union", "password": "123456", "name": "校园志愿服务队", "role": "org", "college": "校级组织", "grade": "", "avatar": "志", "bio": "发布校内志愿活动、服务招募和公益项目。", "interests": "志愿服务,公益,活动,组织协作", "location_preference": "活动中心", "schedule_preference": "周末上午"},
        ]

        users: dict[str, User] = {}
        for spec in user_specs:
            user = db.scalar(select(User).where(User.username == spec["username"]))
            if user:
                for key, value in spec.items():
                    setattr(user, key, value)
            else:
                user = User(**spec)
                db.add(user)
            users[spec["username"]] = user
        db.flush()

        def upsert_club(owner_key: str, name: str, description: str, tags: str) -> Club:
            owner = users[owner_key]
            club = db.scalar(select(Club).where(Club.owner_id == owner.id))
            if not club:
                club = db.scalar(select(Club).where(Club.name == name))
            if club:
                club.name = name
                club.description = description
                club.tags = tags
                club.owner_id = owner.id
            else:
                club = Club(name=name, description=description, tags=tags, owner_id=owner.id)
                db.add(club)
            return club

        photo = upsert_club("photo_club", "HIT摄影社", "校园摄影、外拍、后期交流", "摄影,外拍,后期")
        badm = upsert_club("badminton_club", "羽毛球社", "新手体验、日常训练、校内比赛", "羽毛球,运动,训练")
        volunteer = upsert_club("volunteer_union", "校园志愿服务队", "校内志愿活动、公益服务与活动保障", "志愿服务,公益,活动")
        db.flush()

        post_specs = [
            (users["fish"].id, "life", "主楼前的春天真的很适合拍照", "下午从图书馆出来，阳光刚好落在主楼台阶上。想约摄影搭子周末一起拍。", "春日校园,随手拍,摄影"),
            (users["basket"].id, "help", "求一位数据结构期末复习搭子", "主要看树、图和排序。时间暂定每晚8点，地点图书馆二楼。", "学习搭子,数据结构,期末复习"),
            (users["badminton_club"].id, "club", "羽毛球社周三晚训开放报名", "本周三19:00-21:00，体育馆B区开放新成员体验课。", "社团活动,运动,报名中"),
            (users["alice"].id, "study", "高数证明题互助小组招人", "每周二、四晚在正心楼空教室整理证明题思路，欢迎一起做题。", "高数,学习互助,自习"),
        ]
        for author_id, channel, title, content, tags in post_specs:
            post = db.scalar(select(Post).where(Post.title == title))
            if post:
                post.author_id = author_id
                post.channel = channel
                post.content = content
                post.tags = tags
            else:
                db.add(Post(author_id=author_id, channel=channel, title=title, content=content, tags=tags))

        activity_specs = [
            (photo.id, users["photo_club"].id, "摄影社周末中央大街外拍", "适合新手参加，可带手机或相机。", "正心楼门口集合", "周六 14:00", 50, "摄影,外拍,周末"),
            (badm.id, users["badminton_club"].id, "羽毛球社新生体验课", "零基础可以参加，会按水平分组。", "体育馆B区", "周三 19:00", 40, "羽毛球,运动,训练"),
            (volunteer.id, users["volunteer_union"].id, "图书馆秩序维护志愿活动", "协助整理自习区座位与引导同学文明使用公共空间。", "图书馆一楼大厅", "周日 09:00", 30, "志愿服务,图书馆,公益"),
        ]
        for club_id, creator_id, title, description, place, start_time, capacity, tags in activity_specs:
            activity = db.scalar(select(Activity).where(Activity.title == title))
            if activity:
                activity.club_id = club_id
                activity.creator_id = creator_id
                activity.description = description
                activity.place = place
                activity.start_time = start_time
                activity.capacity = capacity
                activity.tags = tags
            else:
                db.add(Activity(club_id=club_id, creator_id=creator_id, title=title, description=description, place=place, start_time=start_time, capacity=capacity, tags=tags))

        buddy_specs = [
            (users["fish"].id, "自习", "图书馆二楼数据结构刷题小组", "每天晚上刷题，互相监督，不闲聊。", "图书馆二楼", "晚上 20:00-22:00", "自习,数据结构,期末复习", 4),
            (users["basket"].id, "运动", "周三羽毛球体验搭子", "新手友好，打完可以一起复盘动作。", "体育馆B区", "周三晚上", "羽毛球,运动,新手", 4),
            (users["photo_club"].id, "活动", "摄影社周末外拍同行任务卡", "中央大街外拍，欢迎新手报名。", "正心楼门口", "周六下午", "摄影,外拍,社团活动", 8),
            (users["alice"].id, "学习", "正心楼高数证明题互助", "每次挑三道证明题讲思路，适合想补基础的同学。", "正心楼", "周二、周四晚上", "高数,学习互助,自习", 5),
        ]
        for creator_id, goal, title, description, place, time_slot, tags, max_members in buddy_specs:
            task = db.scalar(select(BuddyTask).where(BuddyTask.title == title))
            if task:
                task.creator_id = creator_id
                task.goal = goal
                task.description = description
                task.place = place
                task.time_slot = time_slot
                task.tags = tags
                task.max_members = max_members
                task.is_open = True
            else:
                db.add(BuddyTask(creator_id=creator_id, goal=goal, title=title, description=description, place=place, time_slot=time_slot, tags=tags, max_members=max_members))

        market_specs = [
            (users["fish"].id, "九成新机械键盘", "青轴，带原包装，适合宿舍和实验室使用。", 129, "二区食堂门口", "数码,键盘,二手"),
            (users["basket"].id, "羽毛球拍一支", "入门拍，线刚换，适合新手练习。", 68, "体育馆B区", "运动,羽毛球,闲置"),
            (users["alice"].id, "高数与线代复习资料", "纸质笔记和题型整理，适合同步复习。", 20, "正心楼", "学习资料,高数,线代"),
        ]
        for seller_id, title, description, price, place, tags in market_specs:
            item = db.scalar(select(MarketItem).where(MarketItem.title == title))
            if item:
                item.seller_id = seller_id
                item.description = description
                item.price = price
                item.place = place
                item.tags = tags
            else:
                db.add(MarketItem(seller_id=seller_id, title=title, description=description, price=price, place=place, tags=tags))

        schedule_specs = [
            (users["student_yu"].id, "周一", "08:00", "09:40", "数据结构", "正心楼 304", "课前看树和图"),
            (users["student_yu"].id, "周三", "19:00", "21:00", "羽毛球训练", "体育馆B区", "可约搭子"),
            (users["student_yu"].id, "周五", "14:00", "16:00", "项目讨论", "图书馆二楼", "带电脑"),
            (users["fish"].id, "周二", "18:30", "20:30", "英语打卡", "图书馆二楼", "听力与阅读"),
        ]
        for user_id, weekday, start_time, end_time, title, place, note in schedule_specs:
            exists = db.scalar(select(ScheduleItem).where(ScheduleItem.user_id == user_id, ScheduleItem.weekday == weekday, ScheduleItem.title == title))
            if not exists:
                db.add(ScheduleItem(user_id=user_id, weekday=weekday, start_time=start_time, end_time=end_time, title=title, place=place, note=note))

        daily_specs = [
            (users["student_yu"].id, "今天在图书馆刷完两章", "数据结构的图遍历终于顺了，晚上准备复盘错题。", "充实", "学习,自习"),
            (users["student_yu"].id, "周三运动打卡", "羽毛球训练强度刚好，想找固定搭子。", "开心", "运动,羽毛球"),
            (users["alice"].id, "高数证明题整理", "把极限相关证明题按套路分了一遍。", "专注", "高数,学习互助"),
        ]
        for user_id, title, content, mood, tags in daily_specs:
            exists = db.scalar(select(DailyRecord).where(DailyRecord.user_id == user_id, DailyRecord.title == title))
            if not exists:
                db.add(DailyRecord(user_id=user_id, title=title, content=content, mood=mood, tags=tags))
        db.commit()


@app.on_event("startup")
def startup_event():
    seed_data()


@app.get("/")
def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.post("/api/auth/register")
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(**payload.model_dump(), avatar=(payload.name[:1] or "H"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"user": user_public(user)}


@app.post("/api/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username, User.password == payload.password))
    if not user:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    return {"user": user_public(user)}


@app.get("/api/users")
def list_users(role: str | None = None, db: Session = Depends(get_db)):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    return [user_public(u) for u in db.scalars(stmt.order_by(User.id)).all()]


@app.get("/api/users/{user_id}")
def get_profile(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    posts_count = db.scalar(select(func.count(Post.id)).where(Post.author_id == user_id))
    joined_activities = db.scalar(select(func.count(ActivityJoin.id)).where(ActivityJoin.user_id == user_id))
    buddy_count = db.scalar(select(func.count(BuddyJoin.id)).where(BuddyJoin.user_id == user_id))
    return {"user": user_public(user), "stats": {"posts": posts_count, "activities": joined_activities, "buddy_tasks": buddy_count}}


@app.put("/api/users/{user_id}")
def update_profile(user_id: int, payload: ProfileUpdate, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return {"user": user_public(user)}


def post_to_dict(db: Session, p: Post, current_user_id: int | None = None) -> dict[str, Any]:
    liked = False
    if current_user_id:
        liked = db.scalar(select(func.count(Like.id)).where(Like.post_id == p.id, Like.user_id == current_user_id)) > 0
    return {
        "id": p.id,
        "author": user_public(p.author),
        "channel": p.channel,
        "title": p.title,
        "content": p.content,
        "tags": tags_list(p.tags),
        "image_url": p.image_url,
        "created_at": p.created_at.isoformat(timespec="seconds"),
        "likes_count": len(p.likes),
        "liked": liked,
        "comments": [{"id": c.id, "author": user_public(c.author), "content": c.content, "created_at": c.created_at.isoformat(timespec="seconds")} for c in p.comments],
    }


@app.get("/api/posts")
def list_posts(channel: str | None = None, q: str | None = None, current_user_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Post).order_by(Post.created_at.desc())
    posts = db.scalars(stmt).unique().all()
    if channel and channel != "all":
        posts = [p for p in posts if p.channel == channel]
    if q:
        query = q.lower().strip()
        posts = [p for p in posts if query in p.title.lower() or query in p.content.lower() or query in p.tags.lower()]
    return [post_to_dict(db, p, current_user_id) for p in posts]


@app.post("/api/posts")
def create_post(payload: PostCreate, db: Session = Depends(get_db)):
    user = get_user_or_404(db, payload.user_id)
    post = Post(**payload.model_dump())
    db.add(post)
    db.flush()
    notify(db, user.id, "post", f"你的帖子《{post.title}》已发布")
    db.commit()
    db.refresh(post)
    return post_to_dict(db, post, user.id)


@app.post("/api/posts/{post_id}/comments")
def create_comment(post_id: int, payload: CommentCreate, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    user = get_user_or_404(db, payload.user_id)
    comment = Comment(post_id=post_id, author_id=user.id, content=payload.content)
    db.add(comment)
    if post.author_id != user.id:
        notify(db, post.author_id, "comment", f"{user.name} 评论了你的帖子《{post.title}》")
    db.commit()
    return {"ok": True}


@app.post("/api/posts/{post_id}/like")
def toggle_like(post_id: int, payload: JoinIn, db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    get_user_or_404(db, payload.user_id)
    existing = db.scalar(select(Like).where(Like.post_id == post_id, Like.user_id == payload.user_id))
    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(Like(post_id=post_id, user_id=payload.user_id))
        liked = True
        if post.author_id != payload.user_id:
            notify(db, post.author_id, "like", "有人点赞了你的帖子")
    db.commit()
    return {"liked": liked}


@app.get("/api/clubs")
def list_clubs(db: Session = Depends(get_db)):
    clubs = db.scalars(select(Club).order_by(Club.id)).all()
    return [{"id": c.id, "name": c.name, "description": c.description, "tags": tags_list(c.tags), "owner_id": c.owner_id} for c in clubs]


@app.post("/api/clubs/{club_id}/apply")
def apply_club(club_id: int, payload: ClubApplyIn, db: Session = Depends(get_db)):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="社团不存在")
    user = get_user_or_404(db, payload.user_id)
    existing = db.scalar(select(ClubApplication).where(ClubApplication.club_id == club_id, ClubApplication.user_id == user.id))
    if existing:
        raise HTTPException(status_code=400, detail="你已经提交过申请")
    app_obj = ClubApplication(club_id=club_id, user_id=user.id, message=payload.message)
    db.add(app_obj)
    if club.owner_id:
        notify(db, club.owner_id, "club_apply", f"{user.name} 申请加入 {club.name}")
    db.commit()
    return {"ok": True}


@app.get("/api/applications")
def list_applications(owner_id: int | None = None, user_id: int | None = None, db: Session = Depends(get_db)):
    apps = db.scalars(select(ClubApplication).order_by(ClubApplication.created_at.desc())).all()
    result = []
    for a in apps:
        club = db.get(Club, a.club_id)
        user = db.get(User, a.user_id)
        if owner_id and (not club or club.owner_id != owner_id):
            continue
        if user_id and a.user_id != user_id:
            continue
        result.append({"id": a.id, "club": {"id": club.id, "name": club.name} if club else None, "user": user_public(user), "message": a.message, "status": a.status, "created_at": a.created_at.isoformat(timespec="seconds")})
    return result


@app.post("/api/applications/{application_id}/review")
def review_application(application_id: int, payload: ApplicationReviewIn, db: Session = Depends(get_db)):
    app_obj = db.get(ClubApplication, application_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="申请不存在")
    club = db.get(Club, app_obj.club_id)
    if not club or club.owner_id != payload.reviewer_id:
        raise HTTPException(status_code=403, detail="只有社团负责人可以审核")
    if payload.status not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="状态只能是 approved 或 rejected")
    app_obj.status = payload.status
    notify(db, app_obj.user_id, "club_review", f"你加入 {club.name} 的申请已{('通过' if payload.status == 'approved' else '拒绝')}")
    db.commit()
    return {"ok": True}


def activity_to_dict(db: Session, a: Activity, current_user_id: int | None = None) -> dict[str, Any]:
    joined_count = db.scalar(select(func.count(ActivityJoin.id)).where(ActivityJoin.activity_id == a.id))
    joined = False
    if current_user_id:
        joined = db.scalar(select(func.count(ActivityJoin.id)).where(ActivityJoin.activity_id == a.id, ActivityJoin.user_id == current_user_id)) > 0
    club = db.get(Club, a.club_id) if a.club_id else None
    creator = db.get(User, a.creator_id)
    return {"id": a.id, "club": {"id": club.id, "name": club.name} if club else None, "creator": user_public(creator), "title": a.title, "description": a.description, "place": a.place, "start_time": a.start_time, "capacity": a.capacity, "joined_count": joined_count, "joined": joined, "tags": tags_list(a.tags)}


def market_to_dict(item: MarketItem, current_user_id: int | None = None) -> dict[str, Any]:
    return {
        "id": item.id,
        "seller": user_public(item.seller),
        "title": item.title,
        "description": item.description,
        "price": item.price,
        "place": item.place,
        "tags": tags_list(item.tags),
        "status": item.status,
        "reserved_by": user_public(item.reserver),
        "reserved_by_me": bool(current_user_id and item.reserved_by == current_user_id),
        "is_mine": bool(current_user_id and item.seller_id == current_user_id),
        "created_at": item.created_at.isoformat(timespec="seconds"),
    }


def schedule_to_dict(item: ScheduleItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "weekday": item.weekday,
        "start_time": item.start_time,
        "end_time": item.end_time,
        "title": item.title,
        "place": item.place,
        "note": item.note,
    }


def daily_to_dict(item: DailyRecord) -> dict[str, Any]:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "title": item.title,
        "content": item.content,
        "mood": item.mood,
        "tags": tags_list(item.tags),
        "created_at": item.created_at.isoformat(timespec="seconds"),
    }


@app.get("/api/activities")
def list_activities(current_user_id: int | None = None, db: Session = Depends(get_db)):
    activities = db.scalars(select(Activity).order_by(Activity.created_at.desc())).all()
    return [activity_to_dict(db, a, current_user_id) for a in activities]


@app.post("/api/activities")
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)):
    creator = get_user_or_404(db, payload.creator_id)
    if creator.role != "org":
        raise HTTPException(status_code=403, detail="只有社团账号可以发布活动")
    activity = Activity(**payload.model_dump())
    db.add(activity)
    db.flush()
    notify(db, creator.id, "activity", f"活动《{activity.title}》已发布")
    db.commit()
    db.refresh(activity)
    return activity_to_dict(db, activity, creator.id)


@app.post("/api/activities/{activity_id}/join")
def join_activity(activity_id: int, payload: JoinIn, db: Session = Depends(get_db)):
    activity = db.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")
    user = get_user_or_404(db, payload.user_id)
    joined_count = db.scalar(select(func.count(ActivityJoin.id)).where(ActivityJoin.activity_id == activity_id))
    if joined_count >= activity.capacity:
        raise HTTPException(status_code=400, detail="活动名额已满")
    existing = db.scalar(select(ActivityJoin).where(ActivityJoin.activity_id == activity_id, ActivityJoin.user_id == user.id))
    if existing:
        raise HTTPException(status_code=400, detail="你已经报名过该活动")
    db.add(ActivityJoin(activity_id=activity_id, user_id=user.id))
    notify(db, user.id, "activity_join", f"你已报名活动《{activity.title}》")
    if activity.creator_id != user.id:
        notify(db, activity.creator_id, "activity_join", f"{user.name} 报名了活动《{activity.title}》")
    db.commit()
    return {"ok": True}


@app.post("/api/activities/{activity_id}/cancel")
def cancel_activity(activity_id: int, payload: JoinIn, db: Session = Depends(get_db)):
    activity = db.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")
    user = get_user_or_404(db, payload.user_id)
    existing = db.scalar(select(ActivityJoin).where(ActivityJoin.activity_id == activity_id, ActivityJoin.user_id == user.id))
    if not existing:
        raise HTTPException(status_code=400, detail="你还没有报名该活动")
    db.delete(existing)
    notify(db, user.id, "activity_cancel", f"你已取消活动《{activity.title}》的报名")
    if activity.creator_id != user.id:
        notify(db, activity.creator_id, "activity_cancel", f"{user.name} 取消了活动《{activity.title}》的报名")
    db.commit()
    return {"ok": True}


@app.get("/api/market-items")
def list_market_items(current_user_id: int | None = None, db: Session = Depends(get_db)):
    items = db.scalars(select(MarketItem).order_by(MarketItem.created_at.desc())).all()
    return [market_to_dict(item, current_user_id) for item in items]


@app.post("/api/market-items")
def create_market_item(payload: MarketItemCreate, db: Session = Depends(get_db)):
    seller = get_user_or_404(db, payload.seller_id)
    item = MarketItem(**payload.model_dump())
    db.add(item)
    db.flush()
    notify(db, seller.id, "market", f"闲置《{item.title}》已发布")
    db.commit()
    db.refresh(item)
    return market_to_dict(item, seller.id)


@app.post("/api/market-items/{item_id}/reserve")
def reserve_market_item(item_id: int, payload: JoinIn, db: Session = Depends(get_db)):
    item = db.get(MarketItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="商品不存在")
    user = get_user_or_404(db, payload.user_id)
    if item.seller_id == user.id:
        raise HTTPException(status_code=400, detail="不能预约自己发布的商品")
    if item.status != "available":
        raise HTTPException(status_code=400, detail="该商品当前不可预约")
    item.status = "reserved"
    item.reserved_by = user.id
    notify(db, user.id, "market_reserve", f"你已预约闲置《{item.title}》")
    notify(db, item.seller_id, "market_reserve", f"{user.name} 预约了你的闲置《{item.title}》")
    db.commit()
    return market_to_dict(item, user.id)


@app.post("/api/market-items/{item_id}/cancel-reservation")
def cancel_market_reservation(item_id: int, payload: JoinIn, db: Session = Depends(get_db)):
    item = db.get(MarketItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="商品不存在")
    user = get_user_or_404(db, payload.user_id)
    if item.reserved_by != user.id and item.seller_id != user.id:
        raise HTTPException(status_code=403, detail="只有预约人或发布人可以取消预约")
    reserver_id = item.reserved_by
    item.status = "available"
    item.reserved_by = None
    notify(db, user.id, "market_cancel", f"闲置《{item.title}》的预约已取消")
    if reserver_id and reserver_id != user.id:
        notify(db, reserver_id, "market_cancel", f"闲置《{item.title}》的预约已被发布人取消")
    if item.seller_id != user.id:
        notify(db, item.seller_id, "market_cancel", f"{user.name} 取消了闲置《{item.title}》的预约")
    db.commit()
    return market_to_dict(item, user.id)


@app.get("/api/schedule")
def list_schedule(user_id: int, db: Session = Depends(get_db)):
    get_user_or_404(db, user_id)
    items = db.scalars(select(ScheduleItem).where(ScheduleItem.user_id == user_id).order_by(ScheduleItem.weekday, ScheduleItem.start_time)).all()
    return [schedule_to_dict(item) for item in items]


@app.post("/api/schedule")
def create_schedule_item(payload: ScheduleItemCreate, db: Session = Depends(get_db)):
    get_user_or_404(db, payload.user_id)
    item = ScheduleItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return schedule_to_dict(item)


@app.delete("/api/schedule/{item_id}")
def delete_schedule_item(item_id: int, user_id: int, db: Session = Depends(get_db)):
    item = db.get(ScheduleItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="课表项不存在")
    if item.user_id != user_id:
        raise HTTPException(status_code=403, detail="只能删除自己的课表项")
    db.delete(item)
    db.commit()
    return {"ok": True}


@app.get("/api/daily-records")
def list_daily_records(user_id: int, db: Session = Depends(get_db)):
    get_user_or_404(db, user_id)
    items = db.scalars(select(DailyRecord).where(DailyRecord.user_id == user_id).order_by(DailyRecord.created_at.desc())).all()
    return [daily_to_dict(item) for item in items]


@app.post("/api/daily-records")
def create_daily_record(payload: DailyRecordCreate, db: Session = Depends(get_db)):
    get_user_or_404(db, payload.user_id)
    item = DailyRecord(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return daily_to_dict(item)


@app.delete("/api/daily-records/{record_id}")
def delete_daily_record(record_id: int, user_id: int, db: Session = Depends(get_db)):
    item = db.get(DailyRecord, record_id)
    if not item:
        raise HTTPException(status_code=404, detail="日常记录不存在")
    if item.user_id != user_id:
        raise HTTPException(status_code=403, detail="只能删除自己的日常记录")
    db.delete(item)
    db.commit()
    return {"ok": True}


def buddy_to_dict(db: Session, t: BuddyTask, current_user_id: int | None = None) -> dict[str, Any]:
    member_count = db.scalar(select(func.count(BuddyJoin.id)).where(BuddyJoin.task_id == t.id)) + 1
    joined = False
    if current_user_id:
        joined = db.scalar(select(func.count(BuddyJoin.id)).where(BuddyJoin.task_id == t.id, BuddyJoin.user_id == current_user_id)) > 0 or t.creator_id == current_user_id
    return {"id": t.id, "creator": user_public(t.creator), "goal": t.goal, "title": t.title, "description": t.description, "place": t.place, "time_slot": t.time_slot, "tags": tags_list(t.tags), "max_members": t.max_members, "member_count": member_count, "joined": joined, "is_open": t.is_open, "created_at": t.created_at.isoformat(timespec="seconds")}


@app.get("/api/buddy-tasks")
def list_buddy_tasks(current_user_id: int | None = None, db: Session = Depends(get_db)):
    tasks = db.scalars(select(BuddyTask).order_by(BuddyTask.created_at.desc())).all()
    return [buddy_to_dict(db, t, current_user_id) for t in tasks]


@app.post("/api/buddy-tasks")
def create_buddy_task(payload: BuddyTaskCreate, db: Session = Depends(get_db)):
    user = get_user_or_404(db, payload.creator_id)
    task = BuddyTask(**payload.model_dump())
    db.add(task)
    db.flush()
    notify(db, user.id, "buddy", f"你的搭子任务《{task.title}》已发布")
    db.commit()
    db.refresh(task)
    return buddy_to_dict(db, task, user.id)


@app.post("/api/buddy-tasks/{task_id}/join")
def join_buddy(task_id: int, payload: JoinIn, db: Session = Depends(get_db)):
    task = db.get(BuddyTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="搭子任务不存在")
    user = get_user_or_404(db, payload.user_id)
    if task.creator_id == user.id:
        raise HTTPException(status_code=400, detail="不能加入自己发布的任务")
    member_count = db.scalar(select(func.count(BuddyJoin.id)).where(BuddyJoin.task_id == task_id)) + 1
    if member_count >= task.max_members:
        task.is_open = False
        raise HTTPException(status_code=400, detail="该任务已满员")
    existing = db.scalar(select(BuddyJoin).where(BuddyJoin.task_id == task_id, BuddyJoin.user_id == user.id))
    if existing:
        raise HTTPException(status_code=400, detail="你已经加入该任务")
    db.add(BuddyJoin(task_id=task_id, user_id=user.id))
    notify(db, user.id, "buddy_join", f"你已加入搭子任务《{task.title}》")
    notify(db, task.creator_id, "buddy_join", f"{user.name} 加入了你的搭子任务《{task.title}》")
    db.commit()
    return {"ok": True}


@app.post("/api/buddy-tasks/{task_id}/leave")
def leave_buddy(task_id: int, payload: JoinIn, db: Session = Depends(get_db)):
    task = db.get(BuddyTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="搭子任务不存在")
    user = get_user_or_404(db, payload.user_id)
    if task.creator_id == user.id:
        raise HTTPException(status_code=400, detail="发布人不能退出自己创建的任务")
    existing = db.scalar(select(BuddyJoin).where(BuddyJoin.task_id == task_id, BuddyJoin.user_id == user.id))
    if not existing:
        raise HTTPException(status_code=400, detail="你还没有加入该任务")
    db.delete(existing)
    task.is_open = True
    notify(db, user.id, "buddy_leave", f"你已退出搭子任务《{task.title}》")
    notify(db, task.creator_id, "buddy_leave", f"{user.name} 退出了你的搭子任务《{task.title}》")
    db.commit()
    return {"ok": True}


@app.post("/api/match")
def match(payload: MatchQuery, db: Session = Depends(get_db)):
    user = get_user_or_404(db, payload.user_id)
    tasks = db.scalars(select(BuddyTask).where(BuddyTask.is_open == True).order_by(BuddyTask.created_at.desc())).all()  # noqa: E712
    results = match_tasks(user, tasks, payload.model_dump(), payload.use_llm)
    return [{"task": buddy_to_dict(db, r.task, user.id), "score": r.score, "reason": r.reason, "detail": r.detail, "llm_reason": r.llm_reason} for r in results]


@app.get("/api/notifications")
def list_notifications(user_id: int, db: Session = Depends(get_db)):
    notes = db.scalars(select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())).all()
    return [{"id": n.id, "type": n.type, "content": n.content, "is_read": n.is_read, "created_at": n.created_at.isoformat(timespec="seconds")} for n in notes]


@app.post("/api/notifications/read-all")
def read_all(payload: JoinIn, db: Session = Depends(get_db)):
    notes = db.scalars(select(Notification).where(Notification.user_id == payload.user_id)).all()
    for n in notes:
        n.is_read = True
    db.commit()
    return {"ok": True}


@app.get("/api/dashboard/{user_id}")
def dashboard(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    my_posts = db.scalars(select(Post).where(Post.author_id == user_id).order_by(Post.created_at.desc())).all()
    joined_activities = db.scalars(select(ActivityJoin).where(ActivityJoin.user_id == user_id).order_by(ActivityJoin.created_at.desc())).all()
    joined_buddy = db.scalars(select(BuddyJoin).where(BuddyJoin.user_id == user_id).order_by(BuddyJoin.created_at.desc())).all()
    apps = db.scalars(select(ClubApplication).where(ClubApplication.user_id == user_id).order_by(ClubApplication.created_at.desc())).all()
    schedule_items = db.scalars(select(ScheduleItem).where(ScheduleItem.user_id == user_id).order_by(ScheduleItem.weekday, ScheduleItem.start_time)).all()
    daily_records = db.scalars(select(DailyRecord).where(DailyRecord.user_id == user_id).order_by(DailyRecord.created_at.desc())).all()
    market_items = db.scalars(select(MarketItem).where((MarketItem.seller_id == user_id) | (MarketItem.reserved_by == user_id)).order_by(MarketItem.created_at.desc())).all()
    return {
        "user": user_public(user),
        "my_posts": [post_to_dict(db, p, user_id) for p in my_posts],
        "joined_activities": [activity_to_dict(db, db.get(Activity, j.activity_id), user_id) for j in joined_activities if db.get(Activity, j.activity_id)],
        "joined_buddy_tasks": [buddy_to_dict(db, db.get(BuddyTask, j.task_id), user_id) for j in joined_buddy if db.get(BuddyTask, j.task_id)],
        "applications": [{"id": a.id, "club_id": a.club_id, "status": a.status, "message": a.message} for a in apps],
        "schedule": [schedule_to_dict(item) for item in schedule_items],
        "daily_records": [daily_to_dict(item) for item in daily_records],
        "market_items": [market_to_dict(item, user_id) for item in market_items],
    }
