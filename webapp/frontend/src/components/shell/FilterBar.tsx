// Filter bar in the black header (reference image): fields with a round icon, a label and a native control,
// plus one range. Native controls: keyboard and screen readers work out of the box.
import { ChevronDown } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function FilterBar({ children }: { children: ReactNode }) {
  return (
    <div className="px-4 pb-5 sm:px-8 sm:pb-6">
      <div className="flex items-stretch overflow-x-auto rounded-lg border border-header-field [scrollbar-width:none]">
        {children}
      </div>
    </div>
  );
}

const fieldBox = "flex min-w-52 flex-1 items-center gap-3 border-r border-header-field px-4 py-3 last:border-r-0";
const iconBox = "flex size-9 shrink-0 items-center justify-center rounded-full border border-header-field text-header-foreground [&_svg]:size-4";
const controlCls = "w-full min-w-0 appearance-none truncate bg-transparent text-sm font-medium text-header-foreground outline-none placeholder:text-header-muted focus-visible:underline";

export function SelectField<V extends string>({ icon, label, value, options, onChange }: { icon: ReactNode; label: string; value: V; options: { value: V; label: string }[]; onChange: (v: V) => void }) {
  return (
    <label className={fieldBox}>
      <span className={iconBox}>{icon}</span>
      <span className="relative min-w-0 flex-1">
        <span className="block text-[11px] text-header-muted">{label}</span>
        <select value={value} onChange={(e) => onChange(e.target.value as V)} className={cn(controlCls, "cursor-pointer pr-6")}>
          {options.map((o) => <option key={o.value} value={o.value} className="bg-popover text-popover-foreground">{o.label}</option>)}
        </select>
        <ChevronDown className="pointer-events-none absolute right-0 bottom-0.5 size-4 text-header-muted" />
      </span>
    </label>
  );
}

export function TextField({ icon, label, value, placeholder, onChange }: { icon: ReactNode; label: string; value: string; placeholder: string; onChange: (v: string) => void }) {
  return (
    <label className={fieldBox}>
      <span className={iconBox}>{icon}</span>
      <span className="min-w-0 flex-1">
        <span className="block text-[11px] text-header-muted">{label}</span>
        <input type="search" value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} className={controlCls} />
      </span>
    </label>
  );
}

/** One-handle range ("RAL minima", "Scade entro", "Importo massimo"); 0 or max means "no limit". */
export function RangeField({ label, value, min, max, step, format, onChange, accent }: { label: string; value: number; min: number; max: number; step: number; format: (v: number) => string; onChange: (v: number) => void; accent: string }) {
  return (
    <label className="flex min-w-72 flex-col justify-center gap-2 px-5 py-3">
      <span className="flex items-center justify-between gap-3">
        <span className="text-[13px] font-medium text-header-foreground">{label}</span>
        <span className="font-mono text-xs font-medium text-header-foreground">{format(value)}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className={cn("h-4 w-full cursor-pointer", accent)}
      />
    </label>
  );
}
