"use client";

import { RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LEVEL } from "@/lib/display";
import type { EvidenceLevel, FitScore, LevelCounts, Report } from "@/lib/types";
import { cn } from "@/lib/utils";

import { CvQuality } from "./cv-quality";
import { Improvements } from "./improvements";
import { JobFit } from "./job-fit";
import { Priorities } from "./priorities";

export function ReportView({ report, onReset }: { report: Report; onReset: () => void }) {
  const passages = new Map(report.passages.map((p) => [p.id, p]));
  const requirements = new Map(report.requirements.map((r) => [r.requirement.id, r]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <p className="min-w-0 truncate text-muted-foreground">
          Results for <span className="font-medium text-foreground">{report.cv_filename}</span>
        </p>
        <Button variant="outline" onClick={onReset}>
          <RotateCcw /> New evaluation
        </Button>
      </div>

      <ScoreCard score={report.score} />

      <Tabs defaultValue="fit">
        <TabsList className="w-full sm:w-fit">
          <TabsTrigger value="fit">Job fit</TabsTrigger>
          <TabsTrigger value="quality">CV quality</TabsTrigger>
          <TabsTrigger value="improvements">Improvements</TabsTrigger>
          <TabsTrigger value="priorities">Priorities</TabsTrigger>
        </TabsList>
        <TabsContent value="fit" className="pt-4">
          <JobFit requirements={report.requirements} />
        </TabsContent>
        <TabsContent value="quality" className="pt-4">
          <CvQuality quality={report.feedback.quality} passages={passages} />
        </TabsContent>
        <TabsContent value="improvements" className="pt-4">
          <Improvements feedback={report.feedback} passages={passages} />
        </TabsContent>
        <TabsContent value="priorities" className="pt-4">
          <Priorities priorities={report.feedback.priorities} requirements={requirements} />
        </TabsContent>
      </Tabs>

      <RunFooter meta={report.meta} />
    </div>
  );
}

function ScoreCard({ score }: { score: FitScore }) {
  return (
    <Card>
      <CardContent className="space-y-5">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">How well the CV demonstrates the job</p>
            <p className="flex items-baseline gap-2">
              <span className="text-4xl font-semibold tabular-nums">{score.score}</span>
              <span className="text-muted-foreground">/ 100 · {score.band}</span>
            </p>
          </div>
          <div className="space-y-1.5 text-sm">
            <CountsRow label="Must-have" counts={score.must_have} />
            <CountsRow label="Nice-to-have" counts={score.nice_to_have} />
          </div>
        </div>
        <Progress value={score.score} aria-label="Evidence score" />
        <details className="text-sm text-muted-foreground">
          <summary className="cursor-pointer select-none hover:text-foreground">
            How the score works
          </summary>
          <p className="mt-2 whitespace-pre-line">{score.rubric}</p>
        </details>
      </CardContent>
    </Card>
  );
}

function CountsRow({ label, counts }: { label: string; counts: LevelCounts }) {
  const total = counts.supported + counts.partial + counts.missing;
  if (total === 0) return null;
  const levels: EvidenceLevel[] = ["supported", "partial", "missing"];
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <span className="w-24 text-muted-foreground">{label}</span>
      {levels.map((level) => (
        <span key={level} className="flex items-center gap-1.5 tabular-nums">
          <span className={cn("size-2 rounded-full", LEVEL[level].dot)} />
          {counts[level]} {level}
        </span>
      ))}
    </div>
  );
}

function RunFooter({ meta }: { meta: Report["meta"] }) {
  const seconds = meta.stages.reduce((sum, s) => sum + s.seconds, 0);
  const tokens = meta.stages.reduce((sum, s) => sum + s.input_tokens + s.output_tokens, 0);
  return (
    <p className="text-xs text-muted-foreground">
      {meta.matcher} · {seconds.toFixed(1)}s · {tokens.toLocaleString()} tokens
    </p>
  );
}
