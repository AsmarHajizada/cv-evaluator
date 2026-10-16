"use client";

import { useRef, useState } from "react";
import { CircleAlert } from "lucide-react";

import { EvaluateForm } from "@/components/evaluate-form";
import { ProgressSteps } from "@/components/progress-steps";
import { ReportView } from "@/components/report/report-view";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { evaluate } from "@/lib/api";
import type { Report, Stage } from "@/lib/types";

type Status =
  | { kind: "idle"; error?: string }
  | { kind: "running"; stage: Stage }
  | { kind: "done"; report: Report };

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const abort = useRef<AbortController | null>(null);

  async function run() {
    if (!file) return;
    const controller = new AbortController();
    abort.current = controller;
    setStatus({ kind: "running", stage: "upload" });
    try {
      const report = await evaluate(
        file,
        jobDescription,
        (stage) => setStatus({ kind: "running", stage }),
        controller.signal,
      );
      setStatus({ kind: "done", report });
      window.scrollTo({ top: 0 });
    } catch (error) {
      if (controller.signal.aborted) return;
      setStatus({ kind: "idle", error: error instanceof Error ? error.message : String(error) });
    }
  }

  function cancel() {
    abort.current?.abort();
    setStatus({ kind: "idle" });
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-10 sm:py-14">
      <header className="mb-8 space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">CV Evaluator</h1>
        <p className="max-w-2xl text-muted-foreground">
          Check a CV against a job description. Each requirement is matched to the CV passages that
          support it.
        </p>
      </header>

      {status.kind === "idle" && (
        <div className="space-y-4">
          {status.error && (
            <Alert variant="destructive">
              <CircleAlert />
              <AlertTitle>The evaluation didn&apos;t finish</AlertTitle>
              <AlertDescription>{status.error}</AlertDescription>
            </Alert>
          )}
          <EvaluateForm
            file={file}
            onFileChange={setFile}
            jobDescription={jobDescription}
            onJobDescriptionChange={setJobDescription}
            onSubmit={run}
          />
        </div>
      )}

      {status.kind === "running" && (
        <ProgressSteps stage={status.stage} filename={file?.name ?? "CV"} onCancel={cancel} />
      )}

      {status.kind === "done" && (
        <ReportView report={status.report} onReset={() => setStatus({ kind: "idle" })} />
      )}
    </main>
  );
}
