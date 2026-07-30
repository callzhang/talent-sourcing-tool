import { expect, test } from "@playwright/test";

test("Production smoke: a ready deployment exposes usable HR controls", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Production sourcing workspace")).toBeVisible();
  const operationalStatus = page.getByRole("group");
  await expect(operationalStatus).not.toHaveAttribute("open", "");
  await page.locator('summary[aria-label="Open operational status"]').click();
  await expect(page.getByRole("region", { name: "Deployment readiness" })).toBeVisible();
  await expect(
    page
      .getByRole("region", { name: "Deployment readiness" })
      .locator(".split-heading")
      .first()
      .getByText("Ready", { exact: true })
  ).toBeVisible();
  await expect(page.getByText("Hard blockers")).toHaveCount(0);
  await expect(page.getByText("Optional degradations")).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Delivery handoff" })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "https://talent-sourcing-tool-zeta.vercel.app" })
  ).toBeVisible();
  await expect(page.getByText("docs/production-owner-checklist.md")).toBeVisible();
  await expect(page.getByText("python3 scripts/prepare_vercel_env.py --strict")).toBeVisible();
  await expect(page.getByText(/Active zones: .*mcp_unlocker/)).toBeVisible();

  await expect(page.getByRole("button", { name: "New Job", exact: true })).toBeEnabled();

  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Search Runs" })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: /LinkedIn/ })).toBeEnabled();
  await expect(page.getByRole("checkbox", { name: /Exa/ })).toBeEnabled();
  await expect(page.getByRole("checkbox", { name: /Bright Data Discover/ })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Create search run" })).toBeEnabled();

  await page.getByRole("button", { name: "Candidates", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Candidates" })).toBeVisible();
});
