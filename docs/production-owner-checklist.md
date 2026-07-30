# Talent Sourcing Tool 生产 Owner Checklist

日期：Thursday, July 30, 2026

## 访问地址

- 正式站点：https://talent-sourcing-tool-zeta.vercel.app
- 当前本地前端：http://127.0.0.1:5173

## 当前状态

当前代码、测试和线上只读校验都已经通过，但正式环境还没有进入可写、可交付状态。

已确认事实：

- 正式站点可访问
- 本地 HR 全链路 E2E 已通过
- 正式站点 smoke 已通过
- `/api/system/status` 已对外返回结构化 readiness
- 生产写接口目前仍被 guardrail 拦住，属于预期保护

## 硬阻塞

正式环境当前还缺两项必填配置：

1. 数据库
   - 需要：`TALENT_DATABASE_URL` / `DATABASE_URL`，或 Turso 的
     `TURSO_DATABASE_URL` 与 `TURSO_AUTH_TOKEN`
   - 等价别名：`DATABASE_URL`
   - 作用：让 job、search run、candidate、review、decision 持久化

2. AI review key
   - 需要：`TALENT_OPENAI_API_KEY`
   - 等价别名：`OPENAI_API_KEY`
   - 作用：让 candidate review 真正在线执行

可选渠道，不阻塞上线：

- `TALENT_BRIGHTDATA_API_KEY`
- `TALENT_BRIGHTDATA_ZONE`

## Owner 需要确认什么

1. 数据库 owner
   - 谁负责提供 production PostgreSQL URL
   - 谁负责确认该库允许 Vercel 访问

2. OpenAI owner
   - 谁负责提供 `TALENT_OPENAI_API_KEY`
   - 谁负责确认额度、模型权限和组织归属可用于正式环境

3. Bright Data owner（可选）
   - 如果要启用 Discover 渠道，谁负责提供有效 key 和 zone

## 补齐后的操作顺序

1. 检查本地变量映射

```bash
python3 scripts/prepare_vercel_env.py --strict
```

2. 把变量写到 Vercel

```bash
python3 scripts/prepare_vercel_env.py --environment production --apply
```

3. 重新发正式站点

```bash
vercel --prod --yes
```

4. 跑正式环境验收

```bash
./scripts/verify_production.sh
```

如果已经拿到正式环境变量，想直接按最后一轮发布顺序执行，可以看：

- `docs/release-checklist-after-env-ready.md`

## 验收通过标准

下面条件同时成立，才算正式环境可交付：

- `deployment_ready = true`
- `create_job` 不再返回 `503`
- `create_search` 不再返回 `503`
- `start_review` 不再返回 `503`
- `create_decision` 不再返回 `503`
- `./scripts/verify_production.sh` 全部通过

## 当前要的反馈

请直接回复两件事：

1. `TALENT_DATABASE_URL` 由谁提供
2. `TALENT_OPENAI_API_KEY` 由谁提供
