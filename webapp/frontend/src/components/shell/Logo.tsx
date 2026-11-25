import { cn } from "@/lib/utils";

/** Mark: a lens with the green "candidati" dot. `onDark` swaps tile and lens colours. */
export function LogoMark({ size = 32, onDark, className }: { size?: number; onDark?: boolean; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden className={cn("shrink-0", className)}>
      <rect width="40" height="40" rx="11" className={onDark ? "fill-header-foreground" : "fill-primary"} />
      <circle cx="17.5" cy="17.5" r="8.5" fill="none" strokeWidth="3.5" className={onDark ? "stroke-header" : "stroke-primary-foreground"} />
      <path d="M24 24 L30.5 30.5" strokeWidth="3.5" strokeLinecap="round" className={onDark ? "stroke-header" : "stroke-primary-foreground"} />
      <circle cx="17.5" cy="17.5" r="3.2" className="fill-brand-dot" />
    </svg>
  );
}

export function Logo({ onDark }: { onDark?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark onDark={onDark} />
      <span className={cn("hidden font-heading text-[25px] leading-none font-bold tracking-tight sm:inline", onDark ? "text-header-foreground" : "text-foreground")}>
        jobspy
      </span>
    </span>
  );
}
