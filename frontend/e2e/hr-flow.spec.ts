import { expect, test, type Page } from "@playwright/test";

test("HR flow: create job, search candidate, review, and submit decision", async ({ page }) => {
  const jobTitle = `E2E HR Flow ${Date.now()}`;
  let jobId: string | undefined;

  try {
    await runHrFlow(page, jobTitle, (createdJobId) => {
      jobId = createdJobId;
    });
  } finally {
    if (jobId) {
      const cleanupResponse = await page.request.delete(`/api/jobs/${encodeURIComponent(jobId)}`);
      expect(cleanupResponse.status()).toBe(204);
      const jobsResponse = await page.request.get("/api/jobs");
      expect(jobsResponse.status()).toBe(200);
      const remainingJobs = (await jobsResponse.json()) as Array<{ id: string }>;
      expect(remainingJobs.some((job) => job.id === jobId)).toBe(false);
    }
  }
});

async function runHrFlow(
  page: Page,
  jobTitle: string,
  onJobCreated: (jobId: string) => void
) {

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "岗位列表" })).toBeVisible();
  await expect(page.getByRole("button", { name: "AI 产品工程师", exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "美国市场产品营销与 PMF 探索负责人", exact: true })
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "L5 技术总监", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "新建岗位", exact: true }).click();
  await page.getByLabel("岗位名称").fill(jobTitle);
  await page.getByLabel("职位描述").fill(
    "验证人才搜索专员岗位的端到端 HR 流程。"
  );
  await page.getByLabel("目标画像").fill(
    "具备足够公开证据，可验证搜索、评审和决定记录流程的候选人。"
  );
  await page.getByLabel("排除条件").fill("缺少岗位匹配的公开证据。");
  await page.getByLabel("搜索要点").fill("llm agent");

  await setChannel(page, "LinkedIn", false);
  await setChannel(page, "GitHub", false);
  await setChannel(page, "Exa", false);
  await setChannel(page, "Bright Data Discover", false);
  await setChannel(page, "OpenReview", true);

  const createJobResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/api/jobs") &&
      response.request().method() === "POST" &&
      response.ok()
  );
  await page.getByRole("button", { name: "保存岗位", exact: true }).click();
  const createdJob = await createJobResponse;
  const createdJobBody = await createdJob.json();
  onJobCreated(createdJobBody.job.id);
  await expect(page.getByRole("heading", { name: jobTitle })).toBeVisible();
  await expect(page.getByText("OpenReview")).toBeVisible();

  await page.getByRole("button", { name: "搜索", exact: true }).click();
  await expect(page.getByLabel("搜索条件")).toHaveValue("llm agent");
  await expect(page.getByText("搜索渠道").last()).toBeVisible();
  await expect(page.getByText("OpenReview", { exact: true }).first()).toBeVisible();
  await page.getByLabel("候选人数量").fill("1");
  await page.getByRole("button", { name: "创建搜索任务", exact: true }).click();

  await expect(page.getByText(/搜索完成，找到 \d+ 位候选人。/)).toBeVisible();
  await expect(page.getByRole("button", { name: "候选人", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "候选人", exact: true }).click();
  await page.getByRole("combobox", { name: "评审岗位" }).selectOption({ label: jobTitle });
  await expect(page.getByRole("button", { name: "评审 AI Agent", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "评审 AI Agent", exact: true }).click();

  await expect(page.getByRole("heading", { name: "AI Agent" })).toBeVisible();
  const readyStatus = page.getByText("已准备好进行 AI 评审。");
  const queuedStatus = page.getByText("AI 评审排队中...");
  const runningStatus = page.getByText("AI 评审进行中...");
  const reviewStatusPanel = page.getByLabel("评审状态");
  const reviewCompletedBadge = reviewStatusPanel.getByText("已完成", { exact: true });
  let reviewGateState = "waiting";
  await expect
    .poll(
      async () => {
        if (await readyStatus.isVisible().catch(() => false)) {
          reviewGateState = "ready";
          return reviewGateState;
        }
        if (await queuedStatus.isVisible().catch(() => false)) {
          reviewGateState = "queued";
          return reviewGateState;
        }
        if (await runningStatus.isVisible().catch(() => false)) {
          reviewGateState = "running";
          return reviewGateState;
        }
        if (await reviewCompletedBadge.isVisible().catch(() => false)) {
          reviewGateState = "completed";
          return reviewGateState;
        }
        reviewGateState = "waiting";
        return reviewGateState;
      },
      { timeout: 30_000 }
    )
    .not.toBe("waiting");

  if (reviewGateState === "ready") {
    const reviewResponse = page.waitForResponse(
      (response) => response.url().includes("/api/reviews/start") && response.ok(),
      { timeout: 180_000 }
    );
    await page.getByRole("button", { name: "开始 AI 评审", exact: true }).click();
    await reviewResponse;
  }

  const recommendationHeading = page.getByRole("heading", {
    level: 3,
    name: /不建议推进|建议推进|边界匹配|强烈建议推进/
  });

  const reviewVisibleNow =
    (await recommendationHeading.isVisible().catch(() => false)) ||
    (await reviewCompletedBadge.isVisible().catch(() => false));

  if (!reviewVisibleNow) {
    await page.getByRole("button", { name: "返回候选人" }).click();
    await page.getByRole("combobox", { name: "评审岗位" }).selectOption({ label: jobTitle });
    await expect(page.getByRole("button", { name: "评审 AI Agent", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "评审 AI Agent", exact: true }).click();
  }

  await expect(reviewCompletedBadge).toBeVisible({ timeout: 180_000 });
  await expect(recommendationHeading).toBeVisible({ timeout: 30_000 });

  await page
    .getByRole("textbox")
    .nth(0)
    .fill("Playwright HR 流程验证：候选人缺少岗位层面的证据。");
  await page
    .getByRole("textbox")
    .nth(1)
    .fill("该验证流程中，公开证据不足以支持推进决定。");
  await page.getByRole("button", { name: "确认淘汰", exact: true }).click();

  await expect(page.getByText("已保存淘汰决定。")).toBeVisible();
  await page.getByRole("button", { name: "岗位优化", exact: true }).click();
  await expect(page.getByRole("heading", { name: "岗位优化建议" })).toBeVisible();
  await expect(page.getByText("已根据淘汰原因生成优化建议。")).toBeVisible();
}

async function setChannel(page: Page, label: string, checked: boolean) {
  const checkbox = page.getByRole("checkbox", { name: label, exact: true });
  if ((await checkbox.isChecked()) !== checked) {
    await checkbox.click();
  }
}
