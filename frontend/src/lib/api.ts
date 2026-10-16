import type { Report, Stage, StreamEvent } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface JobPosting {
  url: string;
  title: string | null;
  text: string;
  source: "json-ld" | "page" | "text";
  truncated: boolean;
}

async function errorMessage(response: Response): Promise<string> {
  const payload = await response.json().catch(() => null);
  return typeof payload?.detail === "string"
    ? payload.detail
    : `Request failed (${response.status}).`;
}

async function request(url: string, init: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new Error(`Can't reach the API at ${API_URL}. Is the backend running?`);
  }
  if (!response.ok) throw new Error(await errorMessage(response));
  return response;
}

export async function fetchJobPosting(url: string): Promise<JobPosting> {
  const response = await request(`${API_URL}/api/job-posting`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  return response.json();
}

/** Calls `onStage` as each stage starts and resolves with the final report. */
export async function evaluate(
  cv: File,
  jobDescription: string,
  onStage: (stage: Stage) => void,
  signal?: AbortSignal,
): Promise<Report> {
  const body = new FormData();
  body.append("cv", cv);
  body.append("job_description", jobDescription);

  const response = await request(`${API_URL}/api/evaluate`, { method: "POST", body, signal });
  const reader = response.body!.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let newline: number;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (!line) continue;
      const event = JSON.parse(line) as StreamEvent;
      if (event.type === "stage") onStage(event.stage);
      else if (event.type === "report") return event.report;
      else throw new Error(event.message);
    }
  }
  throw new Error("The connection closed before the report was ready.");
}
