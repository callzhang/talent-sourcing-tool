import { expect, test, type Page } from "@playwright/test";

test("HR flow: create job, search candidate, review, and submit decision", async ({ page }) => {
  const jobTitle = `E2E HR Flow ${Date.now()}`;

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Job listings" })).toBeVisible();
  await expect(page.getByRole("button", { name: "AI Product Engineer", exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Founding PMM / PMF Discovery Lead", exact: true })
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "L5 技术总监", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "New Job", exact: true }).click();
  await page.getByLabel("JD title").fill(jobTitle);
  await page.getByLabel("JD description").fill(
    "Validate the end-to-end HR workflow for a sourcing specialist role."
  );
  await page.getByLabel("Target profile").fill(
    "Candidate with enough public evidence to test sourcing, review, and decision capture."
  );
  await page.getByLabel("Red flags").fill("Insufficient public evidence for role fit.");
  await page.getByLabel("Search notes").fill("llm agent");

  await setChannel(page, "LinkedIn", false);
  await setChannel(page, "GitHub", false);
  await setChannel(page, "Exa", false);
  await setChannel(page, "Bright Data Discover", false);
  await setChannel(page, "OpenReview", true);

  await page.getByRole("button", { name: "Save Job", exact: true }).click();
  await expect(page.getByRole("heading", { name: jobTitle })).toBeVisible();
  await expect(page.getByText("OpenReview")).toBeVisible();

  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByLabel("Search query")).toHaveValue("llm agent");
  await expect(page.getByText("Searching Channels")).toBeVisible();
  await expect(page.getByText("OpenReview", { exact: true }).first()).toBeVisible();
  await page.getByLabel("Candidate limit").fill("1");
  await page.getByRole("button", { name: "Create search run", exact: true }).click();

  await expect(page.getByText(/Search completed with \d+ candidates\./)).toBeVisible();
  await expect(page.getByRole("button", { name: "Candidates", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Candidates", exact: true }).click();
  await page.getByRole("combobox", { name: "Review queue JD" }).selectOption({ label: jobTitle });
  await expect(page.getByRole("button", { name: "Review AI Agent", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Review AI Agent", exact: true }).click();

  await expect(page.getByRole("heading", { name: "AI Agent" })).toBeVisible();
  const readyStatus = page.getByText("Ready for AI review.");
  const queuedStatus = page.getByText("AI review queued...");
  const runningStatus = page.getByText("AI review running...");
  const reviewStatusPanel = page.getByLabel("Review status");
  const reviewCompletedBadge = reviewStatusPanel.getByText("Completed", { exact: true });
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
    await page.getByRole("button", { name: "Start AI review", exact: true }).click();
    await reviewResponse;
  }

  const recommendationHeading = page.getByRole("heading", {
    level: 3,
    name: /pass|proceed|borderline|strong_proceed/
  });

  const reviewVisibleNow =
    (await recommendationHeading.isVisible().catch(() => false)) ||
    (await reviewCompletedBadge.isVisible().catch(() => false));

  if (!reviewVisibleNow) {
    await page.getByRole("button", { name: "Back to candidates" }).click();
    await page.getByRole("combobox", { name: "Review queue JD" }).selectOption({ label: jobTitle });
    await expect(page.getByRole("button", { name: "Review AI Agent", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Review AI Agent", exact: true }).click();
  }

  await expect(reviewCompletedBadge).toBeVisible({ timeout: 180_000 });
  await expect(recommendationHeading).toBeVisible({ timeout: 30_000 });

  await page
    .getByRole("textbox")
    .nth(0)
    .fill("Playwright HR flow validation on July 30, 2026: candidate lacks role-level evidence.");
  await page
    .getByRole("textbox")
    .nth(1)
    .fill("Public evidence is too thin for a proceed decision in this validation workflow.");
  await page.getByRole("button", { name: "Submit pass", exact: true }).click();

  await expect(page.getByText("Saved pass decision.")).toBeVisible();
});

async function setChannel(page: Page, label: string, checked: boolean) {
  const checkbox = page.getByRole("checkbox", { name: label, exact: true });
  if ((await checkbox.isChecked()) !== checked) {
    await checkbox.click();
  }
}
