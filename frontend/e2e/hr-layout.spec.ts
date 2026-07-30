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

const jobWithRubric = {
  job,
  rubric: {
    id: "rubric_1",
    job_id: job.id,
    version: 1,
    source_hash: "layout-test",
    rubric: { dimensions: [] },
    created_at: job.created_at,
    updated_at: job.updated_at
  }
};

const systemStatus = {
  environment: "local",
  deployment_ready: true,
  warnings: [],
  capabilities: {
    persistent_storage_configured: true,
    review_provider: "codex",
    review_configured: true,
    linkedin_configured: true,
    exa_configured: true,
    brightdata_configured: true,
    public_channels: ["github", "openreview", "arxiv"],
    required_channels: ["linkedin", "github", "openreview", "arxiv", "exa"],
    optional_channels: ["brightdata_discover"],
    channel_availability: {
      linkedin: true,
      github: true,
      openreview: true,
      arxiv: true,
      exa: true,
      brightdata_discover: true
    },
    missing_env_vars: {
      storage: [],
      review: [],
      channels: {}
    }
  }
};

const providerChecks = {
  providers: {
    exa: { status: "ok", detail: "Available" },
    brightdata: { status: "ok", detail: "Available" }
  }
};

test("HR layout: Search channel controls stay aligned at desktop and mobile widths", async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const body =
      pathname === "/api/jobs"
        ? [job]
        : pathname === `/api/jobs/${job.id}`
          ? jobWithRubric
        : pathname === "/api/system/status"
          ? systemStatus
          : pathname === "/api/system/provider-checks"
            ? providerChecks
            : [];
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
}, 30_000);
