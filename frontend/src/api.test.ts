import { afterEach, expect, it, vi } from "vitest";

import { ApiError, api } from "./api";

afterEach(() => {
  vi.restoreAllMocks();
});

it("uses the default backend base URL for requests", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify([]), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  );

  await api.listJobs();

  expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/jobs", {
    headers: { "Content-Type": "application/json" }
  });
});

it("throws an ApiError with status and backend detail for non-2xx responses", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Job not found" }), {
      status: 404,
      statusText: "Not Found",
      headers: { "Content-Type": "application/json" }
    })
  );

  await expect(api.createSearch({ job_id: "job_missing", query: "ai pmm" })).rejects.toMatchObject(
    {
      name: "ApiError",
      status: 404,
      detail: "Job not found",
      message: "POST /api/search failed with 404: Job not found"
    } satisfies Partial<ApiError>
  );
});
