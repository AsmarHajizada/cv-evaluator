import { Sparkles } from "lucide-react";

import { humanize } from "@/lib/display";
import type { RequirementFit } from "@/lib/types";

import { LevelBadge, PassageQuote } from "./shared";

export function JobFit({ requirements }: { requirements: RequirementFit[] }) {
  const groups = [
    {
      title: "Must-have",
      items: requirements.filter((r) => r.requirement.importance === "must_have"),
    },
    {
      title: "Nice-to-have",
      items: requirements.filter((r) => r.requirement.importance === "nice_to_have"),
    },
  ].filter((g) => g.items.length > 0);

  return (
    <div className="space-y-8">
      {groups.map((group) => (
        <section key={group.title} className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">
            {group.title} · {group.items.length}
          </h3>
          <ul className="space-y-3">
            {group.items.map((fit) => (
              <RequirementItem key={fit.requirement.id} fit={fit} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function RequirementItem({ fit }: { fit: RequirementFit }) {
  return (
    <li className="space-y-3 rounded-lg border p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium" title={`From the job: “${fit.requirement.jd_quote}”`}>
            {fit.requirement.text}
          </p>
          <p className="text-xs text-muted-foreground">{humanize(fit.requirement.category)}</p>
        </div>
        <LevelBadge level={fit.level} />
      </div>

      {fit.evidence.length > 0 ? (
        <div className="space-y-2">
          {fit.evidence.map((p) => (
            <PassageQuote key={p.id} passage={p} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground italic">No passage in the CV addresses this.</p>
      )}

      <p>{fit.rationale}</p>
      {fit.suggestion && (
        <p className="flex gap-2 text-muted-foreground">
          <Sparkles className="mt-0.5 size-4 shrink-0" />
          {fit.suggestion}
        </p>
      )}
    </li>
  );
}
