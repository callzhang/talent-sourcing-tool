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

it("handles object details, plain text errors, and no-content responses", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: { code: "bad_request" } }), {
        status: 400,
        statusText: "Bad Request",
        headers: { "Content-Type": "application/json" }
      })
    )
    .mockResolvedValueOnce(
      new Response("plain failure", {
        status: 502,
        statusText: "Bad Gateway",
        headers: { "Content-Type": "text/plain" }
      })
    )
    .mockResolvedValueOnce(new Response("", { status: 503, statusText: "Service Unavailable" }))
    .mockResolvedValueOnce(new Response(null, { status: 204 }));

  await expect(api.listJobs()).rejects.toMatchObject({
    status: 400,
    detail: { code: "bad_request" }
  });
  await expect(api.listJobs()).rejects.toMatchObject({
    status: 502,
    detail: "plain failure"
  });
  await expect(api.listJobs()).rejects.toMatchObject({
    status: 503,
    detail: "Service Unavailable"
  });
  await expect(api.listJobs()).resolves.toBeUndefined();
  expect(fetchMock).toHaveBeenCalledTimes(4);
});

it("exposes read endpoints needed by the task pages", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
    Promise.resolve(
      new Response(JSON.stringify(null), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    )
  );

  await api.getJob("job_1");
  await api.listSearchRuns("job_1");
  await api.getSearchRun("search_run_1");
  await api.listCandidates("job_1");
  await api.getCandidate("candidate_1", "job_1");
  await api.getLatestReview("job_1", "candidate_1");

  expect(fetchMock).toHaveBeenNthCalledWith(1, "http://localhost:8000/api/jobs/job_1", {
    headers: { "Content-Type": "application/json" }
  });
  expect(fetchMock).toHaveBeenNthCalledWith(2, "http://localhost:8000/api/search?job_id=job_1", {
    headers: { "Content-Type": "application/json" }
  });
  expect(fetchMock).toHaveBeenNthCalledWith(3, "http://localhost:8000/api/search/search_run_1", {
    headers: { "Content-Type": "application/json" }
  });
  expect(fetchMock).toHaveBeenNthCalledWith(
    4,
    "http://localhost:8000/api/candidates?job_id=job_1",
    { headers: { "Content-Type": "application/json" } }
  );
  expect(fetchMock).toHaveBeenNthCalledWith(
    5,
    "http://localhost:8000/api/candidates/candidate_1?job_id=job_1",
    { headers: { "Content-Type": "application/json" } }
  );
  expect(fetchMock).toHaveBeenNthCalledWith(
    6,
    "http://localhost:8000/api/reviews/latest?job_id=job_1&candidate_id=candidate_1",
    { headers: { "Content-Type": "application/json" } }
  );
});
