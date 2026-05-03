# 架构与核心逻辑

## 整体结构

项目采用前后端同仓结构：

```text
hit-campus-life/
  backend/
    main.py              FastAPI 路由与业务逻辑
    models.py            SQLAlchemy 数据模型
    schemas.py           Pydantic 请求模型
    database.py          SQLite 连接
    services/
      matcher.py         搭子匹配算法
      llm_client.py      可选 LLM 调用
    frontend/index.html  后端默认返回的页面
  frontend/index.html    前端文件副本
  docs/                  文档
```

后端启动后，`GET /` 会返回 `backend/frontend/index.html`。前端通过 `fetch` 调用同源 API。

## 数据模型

核心数据表包括：

- `users`：学生、社团等账号资料。
- `posts`、`comments`、`likes`：信息流、评论和点赞。
- `clubs`、`club_applications`：社团与成员申请。
- `activities`、`activity_joins`：活动与报名关系。
- `buddy_tasks`、`buddy_joins`：搭子任务和加入关系。
- `market_items`：二手市场商品、预约状态和预约人。
- `schedule_items`：个人课表。
- `daily_records`：个人日常记录。
- `notifications`：通知中心。

## 主要 API

- `POST /api/auth/login`
- `GET /api/posts`
- `POST /api/posts`
- `POST /api/posts/{post_id}/comments`
- `POST /api/posts/{post_id}/like`
- `GET /api/activities`
- `POST /api/activities`
- `POST /api/activities/{activity_id}/join`
- `POST /api/activities/{activity_id}/cancel`
- `GET /api/buddy-tasks`
- `POST /api/buddy-tasks`
- `POST /api/buddy-tasks/{task_id}/join`
- `POST /api/buddy-tasks/{task_id}/leave`
- `POST /api/match`
- `GET /api/market-items`
- `POST /api/market-items`
- `POST /api/market-items/{item_id}/reserve`
- `POST /api/market-items/{item_id}/cancel-reservation`
- `GET /api/schedule`
- `POST /api/schedule`
- `DELETE /api/schedule/{item_id}`
- `GET /api/daily-records`
- `POST /api/daily-records`
- `DELETE /api/daily-records/{record_id}`
- `GET /api/notifications`
- `POST /api/notifications/read-all`

## 匹配算法

搭子匹配位于 `backend/services/matcher.py`。

每个开放任务先进入候选池，然后按以下维度加分：

- 基础可沟通：所有开放任务都有基础分。
- 兴趣标签：用户资料中的兴趣与任务标签重合。
- 本次需求：用户本次输入的标签与任务标签重合。
- 关键词语义：目标、描述、标题、标签之间存在相近关键词。
- 地点偏好：用户输入或资料中的地点与任务地点接近。
- 时间偏好：用户输入或资料中的时间与任务时间接近。

接口返回总分、文字理由和 `detail` 分项明细，前端会逐项展示。

## 本地数据

首次启动时，`seed_data()` 会自动创建表并写入内置账号、社团、活动、搭子任务、二手商品、课表和日常记录。

本地 SQLite 数据库不会提交到 GitHub。其他人克隆仓库后首次运行，会自动生成自己的本地数据库。
