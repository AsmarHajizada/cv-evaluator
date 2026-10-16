import { CircleCheck, Circle, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Stage } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEPS: { stage: Stage; label: string }[] = [
  { stage: "upload", label: "Reading the CV" },
  { stage: "requirements", label: "Extracting job requirements" },
  { stage: "matching", label: "Matching requirements to CV evidence" },
  { stage: "feedback", label: "Writing feedback and rewrites" },
];

export function ProgressSteps({
  stage,
  filename,
  onCancel,
}: {
  stage: Stage;
  filename: string;
  onCancel: () => void;
}) {
  const current = STEPS.findIndex((s) => s.stage === stage);
  return (
    <Card>
      <CardContent className="space-y-5">
        <div>
          <p className="font-medium">Evaluating {filename}</p>
          <p className="text-sm text-muted-foreground">This usually takes under a minute.</p>
        </div>
        <ol className="space-y-3">
          {STEPS.map((step, i) => (
            <li
              key={step.stage}
              className={cn(
                "flex items-center gap-3 text-sm",
                i > current && "text-muted-foreground",
              )}
            >
              {i < current ? (
                <CircleCheck className="size-4 text-emerald-600" />
              ) : i === current ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : (
                <Circle className="size-4" />
              )}
              {step.label}
            </li>
          ))}
        </ol>
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
      </CardContent>
    </Card>
  );
}
