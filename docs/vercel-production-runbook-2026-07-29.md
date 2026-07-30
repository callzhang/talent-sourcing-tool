# Talent Sourcing Tool Vercel Production Runbook

日期：Thursday, July 30, 2026

正式站点：

- https://talent-sourcing-tool-zeta.vercel.app

## 当前事实

代码、测试和线上 guardrail 已经收口到可验证状态：

- 本地 HR 全链路 E2E 已通过
- 正式站点 Playwright smoke 已通过
- `/api/system/status` 已返回结构化 readiness
- `/api/system/provider-checks` 已返回 provider 真实状态
- 正式站点已经在 Thursday, July 30, 2026 重发到最新代码
- 正式站点写接口已通过 live 503 guard probe 校验

当前线上已确认：

- `Exa = ok`
- `Bright Data = expired_key`
- `deployment_ready = false`
- `create_job = 503`
- `create_search = 503`
- `create_decision = 503`
- `start_review = 503`

## 剩余阻塞

要让正式环境进入真正可交付状态，当前还缺下面两项硬阻塞：

1. 持久化数据库
   - `DATABASE_URL` 或 `TALENT_DATABASE_URL`

2. AI review key
   - `TALENT_OPENAI_API_KEY`

Bright Data Discover 现在保留为可选生产渠道，不再阻塞整体 readiness。
但如果要让这条渠道也变成可用，仍然需要：

- `TALENT_BRIGHTDATA_API_KEY`
- `TALENT_BRIGHTDATA_ZONE`

## 当前本地可直接复用的变量

下面两项当前本地已有来源，但仍需要确认是否适合生产：

- `EXA_API_KEY -> TALENT_EXA_API_KEY`
- `BRIGHTDATA_API_KEY -> TALENT_BRIGHTDATA_API_KEY`

注意：

- Bright Data 当前这把 key 已经通过 live check 确认是 `expired_key`
- 所以不能直接把现有本地 Bright Data key 当作生产可用凭证

如果要先把本地共享别名补齐到仓库根目录，可以从：

```bash
cp .env.example .env
```

开始，再把下面这些 shared aliases 填进去：

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `REVIEW_PROVIDER`
- `REVIEW_MODEL`
- `EXA_API_KEY`
- `BRIGHTDATA_API_KEY`
- `BRIGHTDATA_ZONE`

## 建议 owner

这两项硬阻塞最好明确到人：

1. 数据库 owner
   - 提供生产 PostgreSQL URL

2. OpenAI owner
   - 提供 `TALENT_OPENAI_API_KEY`

3. Bright Data owner（可选渠道）
   - 提供一把有效的 `TALENT_BRIGHTDATA_API_KEY`
   - 提供与之匹配的 `TALENT_BRIGHTDATA_ZONE`

## 配置步骤

### 1. 先看本地映射情况

```bash
python3 scripts/prepare_vercel_env.py
```

### 2. 先跑本地 strict 门禁

```bash
python3 scripts/prepare_vercel_env.py --strict
```

只要本地还缺少正式环境必填变量，这条命令就会直接以非零退出码失败。
在 Thursday, July 30, 2026 的当前状态下，这里预期仍然会失败，因为还缺：

- `TALENT_DATABASE_URL`
- `TALENT_OPENAI_API_KEY`

### 3. 如需把本地已有变量写到 Vercel

```bash
python3 scripts/prepare_vercel_env.py --environment production --apply
```

这里的 `--apply` 现在是原子语义：

- 如果本机 `PATH` 里没有 `vercel` CLI，会直接失败
- 如果本地仍缺少必填变量，会直接拒绝做部分写入
- 不会出现“只写进去一半”的线上半配置状态

### 4. 对于本地没有的变量，直接在 Vercel 项目补

项目：

- `talent-sourcing-tool`

硬阻塞必须补的 canonical 变量：

```bash
TALENT_DATABASE_URL
TALENT_OPENAI_API_KEY
```

如果要同时启用 Bright Data Discover，再额外补：

```bash
TALENT_BRIGHTDATA_API_KEY
TALENT_BRIGHTDATA_ZONE
```

### 5. 补完变量后重新部署

```bash
vercel --prod --yes
```

## 验收命令

统一使用这条：

```bash
./scripts/verify_production.sh
```

这条命令现在会先执行严格模式的 readiness 校验。只要出现下面任意一种情况，
脚本就会直接以非零退出码失败：

- `deployment_ready != true`
- 任一生产写保护探针没有返回预期的 `503`

它会顺序做三件事：

1. 先跑 deploy hygiene gate，检查可疑本地脏文件是否都被 `.vercelignore` 覆盖
2. 跑 readiness 检查
3. 只有 readiness 通过时，才继续跑正式站点 smoke E2E

当前 readiness 脚本会直接读取正式站点自己的 `/api/system/provider-checks`，
并对正式站点真实发起写保护探针，所以 Exa / Bright Data / production guardrail
的判断来源都已经是 live production，而不是本地变量推断。

脚本输出也已经和页面状态接口对齐，会直接打印：

- deploy hygiene 摘要
- `hard_blockers`
- `optional_degradations`
- `missing_env_vars`

如果 deploy hygiene 本身不通过，这条命令会在访问线上之前直接失败。
例如仓库里如果多出新的 `* 2.py`、`__pycache__` 或 `.pyc`，但 `.vercelignore`
没有把它们挡住，这里会先报出来。

## 通过标准

下面这些条件同时成立，才算正式站点进入可交付状态：

1. `deployment_ready = true`
2. `/api/system/provider-checks` 返回：
   - `exa.status = ok`
3. `./scripts/verify_production.sh` 全部通过
4. 正式站点上：
   - `New Job` 不再被 production storage guardrail 禁用
   - `Create search run` 不再因为 storage 缺失而禁用
   - 后端写接口不再因为 production guardrail 返回 503

如果还要把 Bright Data Discover 一并纳入正式渠道覆盖，再额外要求：

- `brightdata.status = ok`
- `Bright Data Discover` 不再显示 unavailable

## 当前建议

下一步不是继续改功能，而是先把 owner 确定下来，把两项硬阻塞变量补齐。
变量补齐后，再跑一轮：

1. `vercel --prod --yes`
2. `./scripts/verify_production.sh`
3. 如有必要，再跑一次本地 `./scripts/hr_e2e.sh`
