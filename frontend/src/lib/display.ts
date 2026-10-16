import type { EvidenceLevel, Rating } from "./types";

export const LEVEL: Record<EvidenceLevel, { label: string; badge: string; dot: string }> = {
  supported: {
    label: "Supported",
    badge: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    dot: "bg-emerald-500",
  },
  partial: {
    label: "Partial",
    badge: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
    dot: "bg-amber-500",
  },
  missing: {
    label: "Missing evidence",
    badge: "bg-rose-500/10 text-rose-700 dark:text-rose-400",
    dot: "bg-rose-500",
  },
};

export const RATING: Record<Rating, string> = {
  strong: LEVEL.supported.badge,
  adequate: LEVEL.partial.badge,
  weak: LEVEL.missing.badge,
};

/** "missing_outcome" -> "Missing outcome" */
export function humanize(value: string): string {
  const text = value.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}
