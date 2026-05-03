# HIT校园生活圈

HIT校园生活圈是一个面向校园日常协作的全栈 Web 应用，支持学生账号和社团账号共同使用。你可以在里面发布动态、寻找搭子、报名活动、管理社团申请、使用二手市场、维护个人课表并记录日常。

## 功能

- 学生账号 / 社团账号登录
- 用户资料与个人中心
- 首页动态发布、评论、点赞
- 智能搭子匹配，展示分项评分和匹配理由
- 搭子任务发布、加入、退出
- 校园活动发布、报名、取消报名
- 社团列表、成员申请、负责人审核
- 二手市场发布闲置、预约、取消预约
- 个人课表新增、展示、删除
- 日常记录新增、展示、删除
- 通知中心
- SQLite 数据持久化

## 技术栈

- 前端：HTML + CSS + JavaScript
- 后端：FastAPI
- 数据库：SQLite
- ORM：SQLAlchemy
- 匹配逻辑：本地规则评分，可选接入 OpenAI-compatible API 生成解释

## 快速运行

```bash
cd hit-campus-life/backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000
```

## 可用账号

所有内置账号密码均为 `123456`。

| 类型 | 用户名 | 说明 |
|---|---|---|
| 学生 | student_yu | 自习、摄影、羽毛球、数据结构 |
| 学生 | fish | 摄影、自习、英语 |
| 学生 | basket | 篮球、羽毛球、健身 |
| 学生 | alice | 高数、晨读、跑步 |
| 社团 | photo_club | HIT摄影社 |
| 社团 | badminton_club | 羽毛球社 |
| 社团 | volunteer_union | 校园志愿服务队 |

## LLM API 配置

系统默认不依赖 LLM API。未配置 API 时，匹配功能会使用本地规则算法。

如需接入兼容 OpenAI `/chat/completions` 格式的模型服务，可设置：

```powershell
$env:LLM_API_KEY="你的API_KEY"
$env:LLM_BASE_URL="https://api.example.com/v1"
$env:LLM_MODEL="你的模型名称"
uvicorn main:app --reload
```

也可以参考 `backend/.env.example`。

## 目录结构

```text
hit-campus-life/
  backend/          FastAPI 后端
  frontend/         前端入口文件副本
  docs/             项目文档
```

## 公开发布前注意

仓库已配置 `.gitignore`，会忽略虚拟环境、本地数据库、缓存和环境变量文件。请不要把真实密钥、真实个人信息或本地数据库文件提交到仓库。
