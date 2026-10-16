"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LEVEL } from "@/lib/display";
import type { EvidenceLevel, Passage } from "@/lib/types";
import { cn } from "@/lib/utils";

export function LevelBadge({ level }: { level: EvidenceLevel }) {
  return <Badge className={LEVEL[level].badge}>{LEVEL[level].label}</Badge>;
}

export function PassageQuote({ passage, className }: { passage: Passage; className?: string }) {
  return (
    <blockquote className={cn("border-l-2 pl-3", className)}>
      <p>“{passage.text}”</p>
      <p className="mt-0.5 text-xs text-muted-foreground">
        {passage.section ?? "CV header"} · {passage.id}
      </p>
    </blockquote>
  );
}

/** Highlights [placeholders] the candidate needs to fill in. */
export function WithPlaceholders({ text }: { text: string }) {
  return text.split(/(\[[^\]]+\])/g).map((part, i) =>
    part.startsWith("[") && part.endsWith("]") ? (
      <mark key={i} className="rounded bg-amber-500/15 px-0.5 text-amber-800 dark:text-amber-300">
        {part}
      </mark>
    ) : (
      part
    ),
  );
}

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant="ghost"
      size="icon-sm"
      aria-label="Copy"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? <Check /> : <Copy />}
    </Button>
  );
}
