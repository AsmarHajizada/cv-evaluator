import { Badge } from "@/components/ui/badge";
import { LEVEL } from "@/lib/display";
import type { Priority, RequirementFit } from "@/lib/types";
import { cn } from "@/lib/utils";

export function Priorities({
  priorities,
  requirements,
}: {
  priorities: Priority[];
  requirements: Map<string, RequirementFit>;
}) {
  return (
    <ol className="space-y-3">
      {priorities.map((p, i) => (
        <li key={i} className="flex gap-4 rounded-lg border p-4">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-medium">
            {i + 1}
          </span>
          <div className="min-w-0 space-y-2">
            <p className="font-medium">{p.title}</p>
            <p className="text-muted-foreground">{p.detail}</p>
            {p.requirement_ids.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {p.requirement_ids.map((id) => {
                  const fit = requirements.get(id);
                  if (!fit) return null;
                  return (
                    <Badge key={id} variant="outline" className="max-w-full">
                      <span className={cn("size-1.5 rounded-full", LEVEL[fit.level].dot)} />
                      <span className="truncate">{fit.requirement.text}</span>
                    </Badge>
                  );
                })}
              </div>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
