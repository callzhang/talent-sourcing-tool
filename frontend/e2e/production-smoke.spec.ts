import { expect, test } from "@playwright/test";

test("Production smoke: a ready deployment exposes usable HR controls", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Talent Sourcing Tool" })).toBeVisible();
  await expect(page.getByText("Operational status")).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Deployment readiness" })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Delivery handoff" })).toHaveCount(0);

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
