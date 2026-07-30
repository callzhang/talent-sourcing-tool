# Talent Sourcing Tool 交付完成度 Audit

日期：Thursday, July 30, 2026

## 目标

这份文档只回答一个问题：

- **在 Thursday, July 30, 2026 的当前版本里，哪些要求已经被真实证据证明完成，哪些还没有。**

它不是计划文档，也不是愿景文档。
它只记录当前可验证状态。

## 当前正式站点

- 正式地址：https://talent-sourcing-tool-zeta.vercel.app

## 完成判定标准

要把这条任务判定为“真正可交付完成”，至少要同时满足下面四层：

1. 代码和本地流程可运行
2. 正式站点 live 行为可验证
3. 生产验收脚本可通过
4. Mina 明确确认功能完善可用

## 已被证实完成的项

### 1. 项目已经能部署到 Vercel

证据：

- 正式地址可访问
- 已多次重新部署正式站点
- 最新正式域名仍为：
  - `https://talent-sourcing-tool-zeta.vercel.app`

结论：

- **已完成**

### 2. 本地完整 HR 流程可跑通

证据：

- `./scripts/hr_e2e.sh`
- 在 Thursday, July 30, 2026 的当前版本里，最近一次完整 HR flow 已通过

覆盖链路：

- 新建 Job
- 创建 Search run
- 候选人入队
- AI review
- Human decision

结论：

- **已完成**

### 3. 前后端关键自动化回归可通过

证据：

- `./backend/.venv/bin/pytest backend/tests -q`
  - `170 passed`
- `npm --prefix frontend test -- --run`
  - `7 files passed`
  - `47 tests passed`

结论：

- **已完成**

### 4. 正式站点 smoke 可跑通

证据：

- `PLAYWRIGHT_BASE_URL=https://talent-sourcing-tool-zeta.vercel.app npm --prefix frontend run test:e2e -- --grep "Production smoke"`
- 在 Thursday, July 30, 2026 的当前版本里，最近一次 live smoke 已通过

结论：

- **已完成**

### 5. deploy hygiene gate 已覆盖交付边界

证据：

- `python3 scripts/check_deploy_hygiene.py`
  - `All suspicious deploy artifacts are covered by .vercelignore. Covered artifacts: 61`
- 已接入：
  - `scripts/verify_production.sh`
  - GitHub Actions `validate.yml`
  - README
  - runbook
  - heartbeat automation

结论：

- **已完成**

### 6. 每小时自动化检查已启用

证据：

- automation id: `talent-sourcing-tool-hr-heartbeat`
- 状态：`ACTIVE`
- 频率：`FREQ=HOURLY;INTERVAL=1`

结论：

- **已完成**

## 尚未完成的项

### 1. 正式环境可写、可持久化

当前证据：

- `./scripts/verify_production.sh` 仍然失败
- `deployment_ready = false`
- `create_job / create_search / create_decision / start_review` 仍按预期被 `503` guardrail 拦住

根因：

- 缺 `DATABASE_URL` 或 `TALENT_DATABASE_URL`

结论：

- **未完成**

### 2. 正式环境 AI review 真正可运行

当前证据：

- `./scripts/verify_production.sh` 仍然失败
- `/api/system/status` 明确返回：
  - `AI review is not configured for deployment. Set TALENT_OPENAI_API_KEY.`

根因：

- 缺 `TALENT_OPENAI_API_KEY`

结论：

- **未完成**

### 3. Mina 明确确认功能完善可用

当前证据：

- 已持续向 HR 群同步进展
- 已有每小时 heartbeat automation
- 但当前没有 Mina 的明确完成确认

结论：

- **未完成**

## 当前剩余阻塞

只剩三类：

1. `DATABASE_URL` / `TALENT_DATABASE_URL`
2. `TALENT_OPENAI_API_KEY`
3. Mina 的最终确认

## 一旦 owner 补齐变量，下一步顺序

1. `python3 scripts/prepare_vercel_env.py --strict`
2. `vercel --prod --yes`
3. `./scripts/verify_production.sh`
4. 如有必要，再跑一次 `./scripts/hr_e2e.sh`
5. 等 Mina 明确确认

## 当前结论

在 Thursday, July 30, 2026 的当前版本里：

- **代码、测试、本地 HR 流程、正式站点 smoke、deploy hygiene，都已经被真实证据证明。**
- **任务还不能被判定为真正完成。**

原因不是代码还没跑通，而是正式环境仍缺少：

1. 持久化数据库配置
2. OpenAI review key
3. Mina 的最终确认

## 生产复验更新（2026-07-30）

以上缺失配置的记录已失效。随后完成的正式环境复验结果如下：

- `/api/system/status` 返回 `deployment_ready = true`，没有 hard blocker 或 optional degradation。
- `/api/system/provider-checks` 显示 Exa 和 Bright Data 均可用；Bright Data 已启用 `mcp_unlocker` zone。
- 使用正式站点的 Product Marketing 岗位，通过 Bright Data Discover 创建真实 search run，状态为 `completed`，并持久化 1 位候选人。
- `./scripts/hr_e2e.sh` 使用隔离数据库和真实 Codex review 跑通 HR 全流程：新建岗位、搜索候选人、查看详情、AI 初评和提交人工 pass decision。
- `PLAYWRIGHT_BASE_URL=https://talent-sourcing-tool-zeta.vercel.app npm --prefix frontend run test:e2e -- --grep 'Production smoke'` 通过。

当前仅剩业务验收：Mina 在 HR 群明确确认功能完善可用。该确认前，系统保持可访问和可复验状态，但交付任务不标记为完成。
