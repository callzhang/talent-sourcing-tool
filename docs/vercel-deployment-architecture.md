# Talent Sourcing Tool Vercel 部署架构说明

日期：Thursday, July 30, 2026

## 当前部署结构

当前正式环境采用的是一个保守、已验证可运行的结构：

1. 前端用 Vite 构建到 `frontend/dist`
2. Vercel 把 `frontend/dist` 作为静态输出目录
3. `api/index.py` 作为 Python 入口
4. `vercel.json` 把 `/api/*` 请求改写到 Python 入口
5. `api/index.py` 同时：
   - 提供 FastAPI 接口
   - 提供 SPA 静态文件与前端回退路由

对应文件：

- `vercel.json`
- `api/index.py`
- `backend/app/main.py`

## 为什么当前不继续拆架构

当前最重要的目标不是“把部署形态做得最时髦”，而是“把正式交付边界做稳，并把真实阻塞收敛到外部配置”。

在 Thursday, July 30, 2026 的当前状态下，下面这些事情已经被真实验证过：

- 正式域名可访问
- production smoke 可通过
- 本地完整 HR flow E2E 可通过
- deploy hygiene gate 已加入
- production guardrail 行为可验证

因此，当前架构虽然不算最优雅，但它满足一个更重要的标准：

- **已经能被真实验证**

这比“切到一套更漂亮但未验证的新结构”更重要。

## 当前结构的好处

### 1. 变更面小

前端、后端、静态资源、Vercel 路由都还在同一个项目内。
这让部署、回滚、复验路径都更短。

### 2. 验证链路直接

当前生产验收只需要看三层：

1. deploy hygiene
2. production readiness
3. production smoke

不需要再额外排查多服务之间的路由、服务发现或跨 service 配置偏差。

### 3. 当前真实阻塞不在架构层

当前不能进入“真正可写、可交付”的原因，不是 Vercel 的部署形态，而是：

1. `DATABASE_URL` / `TALENT_DATABASE_URL`
2. `TALENT_OPENAI_API_KEY`

在这两个阻塞未解除之前，继续大改部署结构，对交付帮助不大。

## 当前结构的已知代价

### 1. `api/index.py` 兼顾 API 和静态资源

这意味着入口文件职责偏多，不是最干净的服务边界。

### 2. `/api` rewrite 存在平台警告

当前 Vercel build 日志会提示 rewritten backend path 行为。
这说明平台在演进，这层兼容未来可能还要再看。

### 3. 不是最终的服务拆分形态

如果未来要把前端和后端彻底拆开，当前结构不会是终态。

## 什么情况下值得再拆

只有在下面条件满足后，才值得考虑继续做更大的部署架构调整：

1. 正式环境已经补齐持久化数据库
2. 正式环境已经补齐 OpenAI review key
3. `./scripts/verify_production.sh` 在正式域名上完整通过
4. Mina 或 owner 已确认当前功能可用

在这些条件成立之前，更推荐继续保持当前结构，把精力集中在：

- 外部配置补齐
- 线上真实验收
- HR 使用反馈

## 下一阶段可考虑的方向

当正式环境已经进入真正可交付状态后，可以再评估是否做下面这些演进：

1. 前后端更明确的服务分离
2. 减少 `api/index.py` 的双重职责
3. 评估是否迁到 Vercel Services 或其它更明确的多服务结构
4. 把 review 执行从当前轮询触发进一步拆到独立 worker / queue

这些都属于“交付后优化”，不应和当前生产阻塞混在一起。

## 当前结论

在 Thursday, July 30, 2026 的当前版本里，继续保持现有 Vercel 部署结构是更稳的选择。
下一步的优先级仍然是：

1. 补齐 `DATABASE_URL` / `TALENT_DATABASE_URL`
2. 补齐 `TALENT_OPENAI_API_KEY`
3. 重新部署
4. 跑最终正式验收
