import { expect, test } from "@playwright/test";

test("Production smoke: a ready deployment exposes usable HR controls", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "人才搜索与评估" })).toBeVisible();
  await expect(page.getByText("Operational status")).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Deployment readiness" })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Delivery handoff" })).toHaveCount(0);

  await expect(page.getByRole("button", { name: "新建岗位", exact: true })).toBeEnabled();

  await page.getByRole("button", { name: "搜索", exact: true }).click();
  await expect(page.getByRole("heading", { name: "搜索任务" })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: /LinkedIn/ })).toBeEnabled();
  await expect(page.getByRole("checkbox", { name: /Exa/ })).toBeEnabled();
  await expect(page.getByRole("checkbox", { name: /Bright Data Discover/ })).toBeEnabled();
  await expect(page.getByRole("button", { name: "创建搜索任务" })).toBeEnabled();

  await page.getByRole("button", { name: "候选人", exact: true }).click();
  await expect(page.getByRole("heading", { name: "候选人" })).toBeVisible();
});
