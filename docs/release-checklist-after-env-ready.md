# Talent Sourcing Tool Release Checklist

日期：Thursday, July 30, 2026

适用前提：

- 已拿到 `TALENT_DATABASE_URL`
- 已拿到 `TALENT_OPENAI_API_KEY`

这份清单只服务一个场景：

- **owner 已补齐正式环境变量后，谁来执行最后一轮发布和验收。**

## 角色分工

### 1. 配置 owner

负责：

- 提供 `TALENT_DATABASE_URL`
- 提供 `TALENT_OPENAI_API_KEY`
- 确认变量已写入 Vercel production

### 2. 发布执行人

负责：

- 跑本地 strict 检查
- 重新部署正式站点
- 跑正式环境验收
- 把结果同步到 HR 群

## 执行顺序

### Step 1. 本地 strict 检查

```bash
python3 scripts/prepare_vercel_env.py --strict
```

通过标准：

- 不再报缺 `TALENT_DATABASE_URL`
- 不再报缺 `TALENT_OPENAI_API_KEY`

### Step 2. 如需要，把本地变量写到 Vercel

```bash
python3 scripts/prepare_vercel_env.py --environment production --apply
```

通过标准：

- 不再报 partial apply
- 不再报缺失必填变量

### Step 3. 重新发布正式站点

```bash
vercel --prod --yes
```

通过标准：

- 正式别名仍指向：
  - `https://talent-sourcing-tool-zeta.vercel.app`

### Step 4. 跑正式环境最终验收

```bash
./scripts/verify_production.sh
```

通过标准：

- deploy hygiene 通过
- `deployment_ready = true`
- `./scripts/verify_production.sh` 以零退出码结束
- production smoke E2E 通过

### Step 5. 如需要，再跑一次本地完整 HR 流程

```bash
./scripts/hr_e2e.sh
```

通过标准：

- 完整 HR flow 再次通过

## 页面侧最终检查

正式站点上至少再看一遍：

- `New Job` 不再被 guardrail 禁用
- `Create search run` 不再被 guardrail 禁用
- `Start AI review` 不再因为缺生产 review 配置而禁用
- 写接口不再返回 `503`

## 完成判定

下面条件同时成立，才能把这条任务判定为真正完成：

1. `./scripts/verify_production.sh` 通过
2. 正式站点可写链路恢复
3. 如有补跑，`./scripts/hr_e2e.sh` 通过
4. Mina 明确确认功能完善可用

## 发布后同步内容

发到 HR 群时，至少包含：

1. 正式站点地址
2. `verify_production.sh` 结果
3. 是否还能看到任何 `hard_blockers`
4. 是否还剩外部阻塞
5. 是否等待 Mina 最终确认
