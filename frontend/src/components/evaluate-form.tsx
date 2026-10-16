"use client";

import { type FormEvent, useState } from "react";
import { FileText, Link, LoaderCircle, Upload, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { fetchJobPosting } from "@/lib/api";
import { cn } from "@/lib/utils";

const ACCEPT = ".pdf,.docx,.md,.txt,.html";
const MAX_BYTES = 5 * 1024 * 1024;
export const MIN_JD_CHARS = 50;

function JobLink({ onLoaded }: { onLoaded: (text: string) => void }) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [note, setNote] = useState<{ error: boolean; text: string } | null>(null);

  async function load(e: FormEvent) {
    e.preventDefault();
    const link = /^https?:\/\//i.test(url.trim()) ? url.trim() : `https://${url.trim()}`;
    setLoading(true);
    setNote(null);
    try {
      const posting = await fetchJobPosting(link);
      onLoaded(posting.text);
      const host = new URL(posting.url).hostname.replace(/^www\./, "");
      const what = posting.title ? `“${posting.title}”` : "the posting";
      setNote({
        error: false,
        text: `Loaded ${what} from ${host}. Check the text below before evaluating.${
          posting.truncated ? " It was long, so the end was cut off." : ""
        }`,
      });
    } catch (error) {
      setNote({ error: true, text: error instanceof Error ? error.message : String(error) });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-1.5">
      <form onSubmit={load} className="flex gap-2">
        <div className="relative flex-1">
          <Link className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            inputMode="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Link to the job posting"
            aria-label="Job posting link"
            className="pl-8"
          />
        </div>
        <Button type="submit" variant="outline" disabled={!url.trim() || loading}>
          {loading && <LoaderCircle className="animate-spin" />}
          {loading ? "Loading" : "Load"}
        </Button>
      </form>
      {note && (
        <p className={cn("text-sm", note.error ? "text-destructive" : "text-muted-foreground")}>
          {note.text}
        </p>
      )}
    </div>
  );
}

interface Props {
  file: File | null;
  onFileChange: (file: File | null) => void;
  jobDescription: string;
  onJobDescriptionChange: (text: string) => void;
  onSubmit: () => void;
}

export function EvaluateForm({
  file,
  onFileChange,
  jobDescription,
  onJobDescriptionChange,
  onSubmit,
}: Props) {
  const [dragging, setDragging] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [loadingSample, setLoadingSample] = useState(false);

  function pick(candidate: File | undefined) {
    if (!candidate) return;
    const suffix = candidate.name.slice(candidate.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPT.split(",").includes(suffix)) {
      setFileError("Use a PDF, DOCX, Markdown, HTML, or plain-text file.");
    } else if (candidate.size > MAX_BYTES) {
      setFileError("The file must be under 5 MB.");
    } else {
      setFileError(null);
      onFileChange(candidate);
    }
  }

  async function loadSample() {
    setLoadingSample(true);
    try {
      const [cv, jd] = await Promise.all([
        fetch("/samples/cv_ml_engineer.pdf").then((r) => r.blob()),
        fetch("/samples/jd_ml_engineer.txt").then((r) => r.text()),
      ]);
      onFileChange(new File([cv], "cv_ml_engineer.pdf", { type: "application/pdf" }));
      onJobDescriptionChange(jd);
      setFileError(null);
    } finally {
      setLoadingSample(false);
    }
  }

  const ready = file !== null && jobDescription.trim().length >= MIN_JD_CHARS;

  return (
    <Card>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="cv">CV</Label>
          <label
            htmlFor="cv"
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              pick(e.dataTransfer.files[0]);
            }}
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed px-4 py-8 text-center transition-colors hover:bg-muted/50",
              dragging && "border-foreground/40 bg-muted",
            )}
          >
            <input
              id="cv"
              type="file"
              accept={ACCEPT}
              className="sr-only"
              onChange={(e) => {
                pick(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
            {file ? (
              <>
                <FileText className="size-5 text-muted-foreground" />
                <span className="font-medium break-all">{file.name}</span>
                <span className="text-xs text-muted-foreground">
                  {(file.size / 1024).toFixed(0)} KB · click to replace
                </span>
              </>
            ) : (
              <>
                <Upload className="size-5 text-muted-foreground" />
                <span>
                  Drop your CV here or <span className="underline underline-offset-4">browse</span>
                </span>
                <span className="text-xs text-muted-foreground">
                  PDF, DOCX, Markdown, or plain text · up to 5 MB
                </span>
              </>
            )}
          </label>
          {fileError && <p className="text-sm text-destructive">{fileError}</p>}
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="jd">Job description</Label>
            {jobDescription && (
              <Button variant="ghost" size="xs" onClick={() => onJobDescriptionChange("")}>
                <X /> Clear
              </Button>
            )}
          </div>
          <JobLink onLoaded={onJobDescriptionChange} />
          <Textarea
            id="jd"
            value={jobDescription}
            onChange={(e) => onJobDescriptionChange(e.target.value)}
            placeholder="…or paste the full job description, including requirements and nice-to-haves."
            className="field-sizing-fixed h-64 resize-y"
          />
        </div>

        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Button variant="link" className="px-0" onClick={loadSample} disabled={loadingSample}>
            {loadingSample ? "Loading sample…" : "Try a sample CV and job"}
          </Button>
          <Button size="lg" onClick={onSubmit} disabled={!ready}>
            Evaluate CV
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
