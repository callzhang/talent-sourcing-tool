# 人才搜索与评估工具

这是一个给招聘团队使用的本地招聘工作台，目标不是做完整 ATS，而是把一条关键链路跑通：

**写岗位 -> 搜候选人 -> 看证据 -> AI 初评 -> 人工决定淘汰 / 推进**

如果你是 HR，可以把它理解成一个“面向重点岗位的搜索与判断系统”。
它不负责发 offer，也不负责自动发消息；它负责的是把岗位定义、搜索证据、候选人判断，放到一个连续流程里。

## 这套工具解决什么问题

传统招聘里最容易断开的地方有三个：

1. 岗位写了，但搜索条件没有真正跟岗位绑定。
2. 找到候选人了，但为什么找这个人、证据在哪里，说不清。
3. 看过候选人后，团队只留下“过 / 不过”，却没有沉淀出可复用的判断标准。

这个工具的设计就是为了把这三件事连起来。

## 适合谁用

主要面向：

- HR / Recruiter
- Founder 亲自招关键岗位
- 早期团队的人才负责人
- 需要高密度做定向搜人的招聘团队

特别适合这些岗位：

- Product Marketing / PMM
- AI Product Engineer
- Founding Product / GTM / Research 类岗位
- 需要“先定义画像，再定向搜索”的岗位

## 核心功能

### 1. Job 管理

每个岗位都不是一个简单标题，而是一整套招聘输入：

- `Job title`：岗位名称
- `Description`：岗位职责
- `Region`：区域要求，比如 `San Francisco, CA`
- `Target profile`：理想候选人画像
- `Red flags`：明显不匹配信号
- `Search notes`：搜索关键词和搜索思路
- `Search channels`：允许使用的搜索渠道

这意味着系统不是“先搜人再想标准”，而是“先定义标准，再按标准搜人”。

界面、评分标准、AI 评审结论和岗位优化建议均使用中文。候选人的姓名、公司、公开简介、作品标题和外部来源链接保留原文，避免对事实资料进行机器翻译。

### 2. 搜索任务

每一次搜索都会形成一条独立的 `search run`，系统会保存：

- 搜的是哪个岗位
- 用的是什么 query
- 用了哪些渠道
- 区域限制是什么
- 当前状态、执行渠道与已完成的渠道数
- 每个渠道的失败原因（如有）
- 找到了哪些候选人

这样做的意义很直接：
你以后回看某个候选人时，可以知道他是怎么被找到的，而不是只看到一个名字。

### 3. 候选人队列

候选人页面会显示当前岗位下已经搜到的人，并且展示：

- 基本资料
- 来源链接
- 搜索证据
- 搜索排序

现在候选人的主身份已经不是“只能是 LinkedIn”，而是通用的：

- `profile_url`
- `profile_source`

也就是说，候选人可以来自 GitHub、OpenReview、arXiv、LinkedIn 等不同渠道。

### 4. AI 初评

你可以对候选人发起 AI 初评。
系统会把下面这些输入交给评估流程：

- 岗位定义
- 候选人资料
- 搜索证据
- 岗位 rubric

然后返回：

- 总结
- 证据
- 推进建议
- 评分

当前这条链路已经不是“点一下就同步等结果”，而是：

- 点击“开始 AI 评审”先创建一个 `review_job`
- 前端继续轮询这个 `review_job`
- 如果用户中途离开候选人详情页，再回来时，系统会恢复最近一次 review job 并继续跟进状态

它的作用不是替代 HR，而是先做一轮结构化整理，让人工判断更快、更一致。

### 5. 人工决定

最终决定仍然由人来做。当前支持两种：

- `proceed`：进入下一步
- `pass`：不继续推进

如果选择 `pass`，系统鼓励写清楚原因。
这些原因后面可以反过来帮助你优化：

- 搜索 query
- 候选人画像
- 岗位标准

这才是闭环。

## HR 视角下的完整使用流程

### 第一步：新建岗位

在“岗位”页面点击“新建岗位”，填写右侧表单。

建议至少写清楚：

- 岗位 title
- 核心职责
- 区域
- 理想画像
- 明确不考虑的人
- 搜索关键词
- 搜索渠道

如果这里写得很空，后面的搜索质量通常也会很差。
因为系统的搜索不是凭空找人，而是从这里出发。

### 第二步：创建搜索

到“搜索”页面后：

- “搜索条件”会自动从岗位配置里带出
- “搜索渠道”会自动从岗位配置里带出
- “工作地区”也会跟随岗位带出

你可以直接创建搜索，也可以在这一步微调 query 和渠道。
点击创建后，右侧会立即出现这条搜索历史。系统由一个执行器按渠道逐一处理，并显示 `Worker 1`、当前渠道和完成进度；候选人会随着真实搜索结果写入历史记录。

单个渠道的上游服务、授权或解析失败，不会中断其他渠道；历史会保留该渠道的错误。只有配置的全部渠道都无法执行时，整条搜索任务才会标记为失败。

### 第三步：查看搜索结果

每条 `search run` 都会保留历史记录。
你可以看到：

- 这次搜索用了哪些渠道
- 找到了多少候选人
- 候选人列表

点击候选人后，可以跳到候选人详情继续判断。

### 第四步：人工看候选人

在 `Candidates` 页面里，你会看到左右双栏：

- 左侧：候选人队列
- 右侧：候选人详情

右侧重点看三件事：

- 这个人从哪里来的
- 系统记录了哪些证据
- 他和岗位定义是否真的匹配

### 第五步：发起 AI 初评

如果候选人值得进一步看，可以发起 AI review。
AI 会先做一轮结构化分析，帮助你快速判断：

- 匹配点是什么
- 风险点是什么
- 推荐继续还是停止

### 第六步：人工做最终决定

最后由 HR 或 hiring manager 做：

- `proceed`
- `pass`

这一步不是简单点按钮。
真正重要的是：把判断原因留在系统里。
这样下一次搜索时，系统和团队才能越来越准。

每次保存 `pass` 后，`Refinements` 页面都会按该条 HR 原因生成一条待审阅建议。
建议会同时指向岗位 rubric 和搜索 query，但不会自动改写岗位内容，仍由 HR 或 hiring manager 决定是否采用。

## 页面说明

### Jobs

作用：定义岗位。

当前是左右双栏：

- 左边：岗位列表
- 右边：岗位详情 / 新建岗位表单

`New Job` 会打开空白表单，保存后进入岗位列表。

### Search

作用：基于岗位发起搜索。

页面会显示：

- 当前岗位
- 自动填充的 query
- 当前搜索渠道
- 区域限制
- 历史 search runs
- 每条 run 的状态、渠道进度和候选人数量

### Candidates

作用：查看候选人和进入评估流程。

页面会显示：

- 左边：候选人队列
- 右边：当前候选人的详情、来源、signals、risks

### Candidate Detail

作用：对单个候选人做深看和决策。

这里可以：

- 看 AI review
- 写 decision notes
- 提交 `pass` / `proceed`

## 当前支持的搜索渠道

现在系统支持的渠道有：

- `linkedin`
- `github`
- `openreview`
- `arxiv`
- `exa`
- `brightdata_discover`

其中要区分两类：

### 不依赖私有 key 的公开渠道

- `github`
- `openreview`
- `arxiv`

这些可以直接真实运行。

### 依赖外部服务配置的渠道

- `linkedin`
- `exa`
- `brightdata_discover`

这些不是 mock 了，但必须有正确配置才能真实运行。
如果没配好，系统会明确报错，而不是返回假数据。

## 现在系统“真实运行”到什么程度

目前搜索链路已经不再走 mock connector。

也就是说：

- 系统不会再返回固定 fixture 来冒充候选人
- 候选人来源已经改成真实 `profile_url + profile_source`
- 搜索失败时会明确告诉你是渠道配置问题，还是执行问题

例如：

- GitHub 搜索现在会真的请求 GitHub API
- OpenReview 会真的请求 OpenReview API
- arXiv 会真的请求 arXiv API

## 使用时要注意的现实限制

### 1. 这不是完整 ATS

当前不包含：

- 外呼自动化
- 邮件自动发送
- 面试排期
- offer 管理
- 多角色权限

它更像一个“重点岗位搜索与判断台”。

### 2. LinkedIn 不是无条件可搜

LinkedIn 搜索需要依赖：

- Exa
或
- Bright Data SERP

所以如果这些 key 没有配好，LinkedIn 渠道不会工作。

### 3. AI review 只是辅助

AI review 的价值是整理和加速，不是替代判断。
如果岗位定义写得很差，AI review 也会跟着偏。

## 给 HR 的最佳实践

如果你希望这个系统真的有用，建议遵循这几个原则：

### 1. 先把岗位写具体

不要只写：

- “找一个 PMM”
- “找一个产品工程师”

要写清楚：

- 这个岗位解决什么问题
- 为什么是现在需要
- 什么背景是强信号
- 什么背景看起来像相关，但其实不合适

### 2. 搜索渠道按岗位来定

例如：

- PMM / GTM：优先 `linkedin + exa + brightdata_discover`
- 技术 / 产品 / 工程：优先 `github + linkedin + exa`
- 研究 / 算法：优先 `openreview + arxiv + github`

### 3. pass 要写原因

如果只点 `pass`，系统学不到东西。
如果写清楚：

- 为什么不合适
- 是画像不对，还是 query 不对
- 是区域不对，还是经历不对

下次搜索效率会高很多。

在 `Refinements` 页面查看系统保留的建议时，先确认建议引用的 pass 原因和岗位场景一致，再人工更新 JD 或下一次 search run。单条 pass 也会产生建议；多个相同原因会合并为同一条待审阅建议，避免重复噪音。

## 本地启动方式

如果你是使用者而不是开发者，通常不需要关心这一节。
如果本地服务停了，可以把这段发给负责维护的人。

### Backend

```bash
cd backend
python -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/python -m app.db.init_db
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

默认地址：

- 前端：[http://localhost:5173](http://localhost:5173)
- 后端：[http://localhost:8000](http://localhost:8000)

如果想直接一条命令起本地前后端，也可以用：

```bash
./scripts/dev.sh
```

在 Thursday, July 30, 2026 的当前版本里，这条脚本会在默认路径下自动补齐：

- `backend/.venv` 不存在时，自动创建虚拟环境并安装 backend 依赖
- `frontend/node_modules` 不存在时，自动执行 `npm ci`

这里对 backend Python 的要求仍然是 `3.12+`。如果系统里找不到兼容版本，
脚本会直接报错，而不是用错误版本继续创建虚拟环境。

如果你显式传了自定义 `BACKEND_PYTHON`，脚本不会往那个解释器里自动安装依赖；
它会先检查版本和依赖是否齐全，不满足时直接给出安装命令。

## 自动化校验入口

仓库现在有三层自动化校验入口：

1. 本地 HR 全链路：

```bash
./scripts/hr_e2e.sh
```

2. 正式站点统一验收：

```bash
./scripts/verify_production.sh
```

3. GitHub Actions：

- 文件：`.github/workflows/validate.yml`
- `push main` / `pull_request`：跑 backend tests、frontend tests、frontend type check、frontend build
- 如果仓库配置了 `TALENT_OPENAI_API_KEY` secret，会额外跑一轮本地 HR flow E2E
- `workflow_dispatch`：允许手动触发正式站点 deploy hygiene + readiness + smoke 验收

## 环境变量

后端配置写在 `backend/.env`，也会读取仓库根目录 `.env`。

如果要给整个仓库共用一组搜索类凭据，可以从根目录示例开始：

```bash
cp .env.example .env
```

主要字段：

- `TALENT_DATABASE_URL`
- `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN`（Turso 远程数据库二选一配置）
- `TALENT_CODEX_BINARY`
- `TALENT_REVIEW_WORKSPACE_ROOT`
- `TALENT_SOURCING_PROVIDER`
- `TALENT_EXA_API_KEY`
- `TALENT_BRIGHTDATA_API_KEY`
- `TALENT_BRIGHTDATA_ZONE`

根目录 `.env.example` 里提供的是共享别名写法：

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `REVIEW_PROVIDER`
- `REVIEW_MODEL`
- `EXA_API_KEY`
- `BRIGHTDATA_API_KEY`
- `BRIGHTDATA_ZONE`

前端可选配置：

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Vercel 部署架构

截至 Thursday, July 30, 2026，项目已经调整成可部署到同一个 Vercel 项目里的结构：

- `api/index.py` 作为根 Python 入口
- `frontend/dist` 作为前端静态产物
- 同一个根应用同时负责：
  - `GET /` 返回前端页面
  - `GET /assets/*` 返回前端静态资源
  - `GET/POST /api/*` 返回后端接口

这意味着部署后不再需要前后端两个独立域名，也不需要前端写死 `localhost:8000`。

### Vercel 必须配置的环境变量

如果只是让页面能打开，当前代码可以在 Vercel 上启动。
如果要让系统真正可用，至少还要补齐下面两类硬阻塞配置，并按需要补充一类可选渠道配置：

#### 1. 持久化数据库

推荐直接配置：

```bash
DATABASE_URL=postgresql://...
```

也支持 Turso 远程数据库，适用于 Vercel 这类无持久本地磁盘的运行环境：

```bash
TURSO_DATABASE_URL=libsql://<database>.turso.io
TURSO_AUTH_TOKEN=...
```

应用会将该 URL 通过 `sqlalchemy-libsql` 连接到 Turso；不要同时设置
`DATABASE_URL` / `TALENT_DATABASE_URL`，避免存储来源不明确。

原因很直接：

- Vercel Function 本地文件系统不是持久化数据库
- 即使临时把 SQLite 放到 `/tmp`，不同请求也可能落到不同实例
- 招聘系统是强状态系统，Job、Search Run、Candidate、Review、Decision 都必须持久化

所以 **线上正式环境不应该依赖 SQLite**。
在 Thursday, July 30, 2026 这次线上核验里，`/api/system/status` 已明确返回：

- `persistent_storage_configured=false`
- warning: `Production is using temporary SQLite storage on /tmp. Configure DATABASE_URL for durable state.`

#### 2. AI review provider

部署到 Vercel 后，本地 `codex exec` 子进程路线不再适用。
线上需要配置：

```bash
TALENT_OPENAI_API_KEY=...
TALENT_REVIEW_MODEL=gpt-4.1-mini
```

如果不配这一组里的 key，搜索链路可以工作，但 `AI review` 无法真实跑通。
在 Thursday, July 30, 2026 的当前代码里，Vercel 上的 `review provider` 会自动解析为 `openai`；
显式设置 `TALENT_REVIEW_PROVIDER=openai` 只是可选的显式写法，不是硬要求。

#### 3. 扩展搜索渠道（可选）

如果希望线上把 `Bright Data Discover` 这条独立渠道也启用，再补齐：

```bash
TALENT_EXA_API_KEY=...
TALENT_BRIGHTDATA_API_KEY=...
TALENT_BRIGHTDATA_ZONE=...
```

不配置时：

- `github`
- `openreview`
- `arxiv`

仍然可以真实运行；但：

- `brightdata_discover`

会在界面中被标记为 unavailable。

### 已验证的部署事实

在 Thursday, July 30, 2026 的这轮验证里，已经确认：

- Vercel 可以成功构建这个项目
- 根页面可以返回前端 HTML
- `/api/jobs` 在生产阻塞态下会返回 `503`
- `/api/system/status` 已经能返回生产环境诊断信息
- 需要额外配置持久化数据库（`DATABASE_URL` 或 Turso 的两项配置）和 `TALENT_OPENAI_API_KEY`，才能让线上进入真正可交付状态
- `Bright Data Discover` 当前是可选生产渠道，不再阻塞整体 readiness

当前生产域名：

- [https://talent-sourcing-tool-zeta.vercel.app](https://talent-sourcing-tool-zeta.vercel.app)

当前生产公开站点已部署到最新代码。
如果要看正式环境当前的 live 状态，优先重新执行 readiness 与 smoke 校验命令，而不是只依赖下面这组示例状态：

- `Exa = ok`
- `Bright Data = expired_key`
- `deployment_ready = false`
- `create_job = 503`
- `create_search = 503`
- `create_decision = 503`
- `start_review = 503`

## 测试与验证

### Backend

```bash
cd backend
./.venv/bin/python -m pytest -q
./.venv/bin/python -m ruff check app tests
```

### Frontend

```bash
cd frontend
npm run test
npm run build
npm run lint
```

### HR 端到端自动化

这次已经补了一条真实的 HR 流程 E2E 脚本：

```bash
./scripts/hr_e2e.sh
```

这条脚本会：

1. 启动隔离的本地 backend + frontend
2. 使用独立 SQLite 和独立 review workspace
3. 通过 Playwright 按 HR 流程跑完整链路：
   - 新建 Job
   - 创建 Search Run
   - 打开 Candidate Queue
   - 进入 Candidate Detail
   - 发起 AI review
   - 提交 pass decision

如果当前机器还没有装前端依赖或 Playwright Chromium，脚本会先自动补齐再执行。

相关文件：

- `scripts/hr_e2e.sh`
- `frontend/playwright.config.ts`
- `frontend/e2e/hr-flow.spec.ts`

### 正式站点 smoke 校验

除了本地 HR 全链路，现在还补了一条直接打正式站点的 smoke E2E：

```bash
PLAYWRIGHT_BASE_URL=https://talent-sourcing-tool-zeta.vercel.app \
  npm --prefix frontend run test:e2e -- --grep "Production smoke"
```

如果你要把 readiness 检查和 live smoke 一起跑，直接用：

```bash
./scripts/verify_production.sh
```

它校验的是正式环境当前应有的 guardrail，而不是本地完整业务流。
当前覆盖：

- HR 首屏不展示 `Deployment readiness` 或 `Delivery handoff` 运维面板
- `New Job` 在 production 上按预期禁用
- `Search` 页里 `LinkedIn` / `Exa` 可用，`Bright Data Discover` 禁用
- `Create search run` 在缺持久化存储时保持禁用
- `Candidates` 页会明确提示 production 为空的原因

这里的 production guardrail 现在已经不是只有前端按钮禁用。
在 Thursday, July 30, 2026 的当前版本里，后端写接口也会直接拒绝：

- 没有持久化数据库时，production 上不能直接创建 Job / Search / Decision
- 没有 OpenAI review 配置时，production 上不能直接启动 AI review

相关文件：

- `frontend/e2e/production-smoke.spec.ts`

### 生产 readiness 校验

除了页面里的 readiness 面板，现在还补了一个命令行校验脚本：

```bash
python3 scripts/check_production_readiness.py --strict
```

如果你想把 readiness 检查和 live smoke 一起串起来，优先用：

```bash
./scripts/verify_production.sh
```

它会做两层事：

1. 先跑 deploy hygiene gate，检查可疑本地脏文件是否都被 `.vercelignore` 覆盖
2. 读取线上 `/api/system/status`
3. 读取线上 `/api/system/provider-checks`
4. 自动安装 Playwright 所需的 Chromium 浏览器，再跑正式站点 smoke

如果当前机器还没有装前端依赖，脚本也会先自动执行一次 `npm --prefix frontend ci`。

当前会明确输出：

- deploy hygiene 是否通过
- 线上是否 `deployment_ready`
- `hard_blockers` 和 `optional_degradations`
- 还缺哪些生产环境变量
- 这些变量在本地是否已经存在
- 正式环境里的 Exa / Bright Data 当前真实状态

如果 deploy hygiene 本身没通过，这条命令会在访问线上之前直接失败。
例如仓库里如果多出新的 `* 2.py`、`__pycache__` 或 `.pyc`，但 `.vercelignore`
没有把它们挡住，这里会先报出来。

如果 readiness 本身不达标，这条命令会在 production smoke 之前直接失败，不会继续把 smoke 结果误读成“整体可交付”。
当前脚本也会明确输出：`Production readiness failed; skipping production smoke E2E.`

如果你想先理解当前正式环境为什么仍然保持“单 Python 入口 + 静态前端 + `/api` rewrite”
这套保守结构，而没有继续做更激进的服务拆分，可以看：

- `docs/vercel-deployment-architecture.md`

如果你想快速判断“当前到底哪些已经完成，哪些还没完成”，可以直接看：

- `docs/delivery-completion-audit-2026-07-30.md`

如果 owner 已经补齐正式环境变量，想直接照着最后一轮发布顺序执行，可以直接看：

- `docs/release-checklist-after-env-ready.md`

如果你只想看静态缺口，不跑 provider 活性检查：

```bash
python3 scripts/check_production_readiness.py --skip-provider-checks
```

如果你只想输出报告，不把未就绪状态当作失败，也可以不用 `--strict`。

如果你要把本地已有的变量映射成 Vercel 的 canonical 变量名，也可以直接先跑 dry run：

```bash
python3 scripts/prepare_vercel_env.py
```

如果你希望把它当成门禁检查，而不是只看展示结果：

```bash
python3 scripts/prepare_vercel_env.py --strict
```

它会自动识别这类映射关系：

- `REVIEW_PROVIDER` -> `TALENT_REVIEW_PROVIDER`
- `REVIEW_MODEL` -> `TALENT_REVIEW_MODEL`
- `EXA_API_KEY` -> `TALENT_EXA_API_KEY`
- `BRIGHTDATA_API_KEY` -> `TALENT_BRIGHTDATA_API_KEY`
- `OPENAI_API_KEY` -> `TALENT_OPENAI_API_KEY`

如果确认要写入某个 Vercel 环境，再显式执行：

```bash
python3 scripts/prepare_vercel_env.py --environment production --apply
```

默认不会改线上配置，只有加 `--apply` 才会真正调用 `vercel env add`.

在 Thursday, July 30, 2026 的当前版本里，这条脚本还有两个明确行为：

- 如果本机 `PATH` 里没有 `vercel` CLI，会直接报错退出，不会抛 Python 栈
- 如果本地仍缺少必填变量，它会直接拒绝做部分写入，并以非零退出码明确提示还缺什么
- 如果使用 `--strict`，即使只是 dry run，也会在缺少必填变量时以非零退出码失败

### 本次真实验证范围

本地这条 E2E 已经真实跑通过。
当前已覆盖的范围包括：

- Job 创建
- Search 真实请求 OpenReview
- Candidate 入队
- AI review 完成
- Human decision 落库

同时，本轮还额外验证了：

- 前端关键回归已通过
- 后端关键测试已通过
- 生产域名可访问：[https://talent-sourcing-tool-zeta.vercel.app](https://talent-sourcing-tool-zeta.vercel.app)

## 还需要继续优化的地方

虽然现在已经能本地跑通，也已经完成 Vercel 部署，但从这轮真实验证里还能看到四个明确优化点：

### 1. 线上必须切到持久化数据库

这是当前最重要的剩余项。
没有持久化数据库（`DATABASE_URL`，或 `TURSO_DATABASE_URL` 与
`TURSO_AUTH_TOKEN`），生产环境即使能启动，也不能保证状态一致性。

### 2. 线上必须具备 OpenAI review 能力

本地可以用 `codex` 子进程完成 review，线上 Vercel 不适合走这条路线。
所以正式环境必须补齐：

- `TALENT_OPENAI_API_KEY`

如果团队希望把配置写得更显式，也可以额外设置：

- `TALENT_REVIEW_PROVIDER=openai`

### 3. Bright Data Discover 仍然是可选增强渠道

如果还希望把 `Bright Data Discover` 这条独立渠道也启用，当前还需要：

- `TALENT_EXA_API_KEY`
- `TALENT_BRIGHTDATA_API_KEY`
- `TALENT_BRIGHTDATA_ZONE`

不补这组配置不会再阻塞整体 readiness，但会让这条补充渠道继续保持 unavailable。

在 Thursday, July 30, 2026 的当前校验里，`scripts/check_production_readiness.py`
已经额外确认：本地可用的 Bright Data key 返回 `401 Token expired`。
这意味着 Bright Data 这条链路现在不只是缺 `zone`，还需要换成有效的 key。

### 4. AI review 已经改成 deferred flow，但还不是独立 worker

在 Thursday, July 30, 2026 的当前版本里：

- `start review` 已经只负责创建 `review_job`
- 前端会轮询 review job
- 候选人详情页重新进入时，会恢复最近一次 pending / running review job

这解决了首个线上结构问题：
`start review` 不再把整段 review 执行时间压在第一次点击请求里。

但它还不是最终形态。当前 review 执行仍然发生在 review job 轮询请求里，
所以更彻底的下一步仍然应该是：

- 独立 worker / queue
- 明确的 job lease / retry 机制
- 前端只订阅状态，不承担触发执行职责

## 总结

这套工具的核心不是“帮你多存几个候选人”，而是把招聘过程里的三个关键动作真正连起来：

1. 定义岗位标准
2. 按标准搜索候选人
3. 把判断沉淀成可复用的招聘逻辑

如果岗位定义清楚、搜索证据真实、人工判断有记录，这个系统就会越来越有价值。
