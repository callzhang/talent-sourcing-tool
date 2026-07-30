import { expect, test } from "@playwright/test";

const job = {
  id: "job_1",
  title: "Founding PMM",
  description: "Own positioning and customer evidence.",
  region: "San Francisco, CA",
  target_profile_text: "",
  red_flags_text: "",
  search_notes: "Find founding product marketers.",
  search_channels: ["linkedin", "github", "exa", "brightdata_discover"],
  created_at: "2026-07-31T00:00:00Z",
  updated_at: "2026-07-31T00:00:00Z"
};

test("Search channel controls stay aligned at desktop and mobile widths", async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const body = pathname === "/api/jobs" ? [job] : [];
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(body)
    });
  });

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");
  await page.getByRole("button", { name: "Search", exact: true }).click();

  const channels = page.locator(".channel-option-list");
  await expect(channels).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "Bright Data Discover" })).toBeVisible();

  const desktop = await channels.evaluate((element) => {
    const option = element.querySelector("label");
    const checkbox = option?.querySelector("input");
    return {
      columnCount: getComputedStyle(element).gridTemplateColumns.split(" ").length,
      optionColumnCount: option ? getComputedStyle(option).gridTemplateColumns.split(" ").length : 0,
      checkboxWidth: checkbox ? getComputedStyle(checkbox).width : ""
    };
  });
  expect(desktop).toEqual({ columnCount: 2, optionColumnCount: 2, checkboxWidth: "18px" });

  await page.setViewportSize({ width: 390, height: 844 });
  const mobile = await channels.evaluate((element) => ({
    columnCount: getComputedStyle(element).gridTemplateColumns.split(" ").length,
    hasOverflow: Array.from(element.children).some(
      (child) => child.getBoundingClientRect().right > document.documentElement.clientWidth
    )
  }));
  expect(mobile).toEqual({ columnCount: 1, hasOverflow: false });
});
