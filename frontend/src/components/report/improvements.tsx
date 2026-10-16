import { Badge } from "@/components/ui/badge";
import { humanize } from "@/lib/display";
import type { Feedback, Passage } from "@/lib/types";

import { CopyButton, WithPlaceholders } from "./shared";

export function Improvements({
  feedback,
  passages,
}: {
  feedback: Feedback;
  passages: Map<string, Passage>;
}) {
  const hasPlaceholders = [
    feedback.summary.text,
    ...feedback.rewrites.map((r) => r.rewritten),
  ].some((t) => /\[[^\]]+\]/.test(t));

  return (
    <div className="space-y-8">
      <p className="text-muted-foreground">
        Rewrites only use facts already in your CV.
        {hasPlaceholders && (
          <>
            {" "}
            Replace <WithPlaceholders text="[highlighted]" /> details with your real numbers, or
            remove them.
          </>
        )}
      </p>

      <section className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground">Suggested summary</h3>
        <div className="space-y-2 rounded-lg border p-4">
          <div className="flex items-start justify-between gap-3">
            <p className="text-base leading-relaxed">
              <WithPlaceholders text={feedback.summary.text} />
            </p>
            <CopyButton text={feedback.summary.text} />
          </div>
          <p className="text-muted-foreground">{feedback.summary.rationale}</p>
        </div>
      </section>

      {feedback.rewrites.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">
            Rewritten bullets · {feedback.rewrites.length}
          </h3>
          <ul className="space-y-3">
            {feedback.rewrites.map((r) => (
              <li key={r.passage_id} className="space-y-3 rounded-lg border p-4">
                <Badge variant="secondary">{humanize(r.issue)}</Badge>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Before · {r.passage_id}</p>
                    <p className="text-muted-foreground">{passages.get(r.passage_id)?.text}</p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">After</p>
                    <div className="flex items-start justify-between gap-2">
                      <p>
                        <WithPlaceholders text={r.rewritten} />
                      </p>
                      <CopyButton text={r.rewritten} />
                    </div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">{r.rationale}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
