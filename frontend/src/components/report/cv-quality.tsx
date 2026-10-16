import { Badge } from "@/components/ui/badge";
import { humanize, RATING } from "@/lib/display";
import type { DimensionFeedback, Passage } from "@/lib/types";

import { PassageQuote } from "./shared";

const DESCRIPTIONS: Record<DimensionFeedback["dimension"], string> = {
  clarity: "Easy to scan, plain language, one idea per bullet",
  relevance: "What this job needs is prominent",
  specificity: "Concrete tools, scope, and context",
  achievements: "Outcomes and impact, not only duties",
};

export function CvQuality({
  quality,
  passages,
}: {
  quality: DimensionFeedback[];
  passages: Map<string, Passage>;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {quality.map((q) => (
        <div key={q.dimension} className="space-y-3 rounded-lg border p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-medium">{humanize(q.dimension)}</p>
              <p className="text-xs text-muted-foreground">{DESCRIPTIONS[q.dimension]}</p>
            </div>
            <Badge className={RATING[q.rating]}>{humanize(q.rating)}</Badge>
          </div>
          <p>{q.comment}</p>
          {q.passage_ids.slice(0, 2).map((id) => {
            const passage = passages.get(id);
            return passage && <PassageQuote key={id} passage={passage} className="text-xs" />;
          })}
        </div>
      ))}
    </div>
  );
}
