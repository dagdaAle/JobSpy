// Form fields described by config, shared by the channel dialog and the profile form.
import { useId, useState } from "react";
import { X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import type { AreaMeta } from "../../api/areas";

export type Option = { value: string; label: string };
export type FormValues = Record<string, unknown>;

export interface FieldConfig {
  name: string;
  label: string;
  // tags = free list typed by hand, multi = pick from options.
  kind: "text" | "number" | "select" | "tags" | "multi" | "switch";
  placeholder?: string;
  required?: boolean;
  wide?: boolean; // full row in the two-column grid
  min?: number;
  max?: number;
  options?: Option[] | ((meta?: AreaMeta) => Option[]);
}

export const resolveOptions = (f: FieldConfig, meta?: AreaMeta) =>
  typeof f.options === "function" ? f.options(meta) : f.options ?? [];

export function FormField({
  field,
  value,
  onChange,
  meta,
}: {
  field: FieldConfig;
  value: unknown;
  onChange: (value: unknown) => void;
  meta?: AreaMeta;
}) {
  const id = useId();
  const wide = field.wide ? "sm:col-span-2" : "";

  if (field.kind === "switch") {
    return (
      <label className={cn("flex items-center justify-between gap-3 rounded-lg border px-3 py-2.5", wide)}>
        <span className="text-sm">{field.label}</span>
        <Switch checked={Boolean(value)} onCheckedChange={onChange} />
      </label>
    );
  }

  const options = resolveOptions(field, meta);
  let control: React.ReactNode;
  if (field.kind === "select") {
    control = (
      <Select items={options} value={(value as string | null) ?? null} onValueChange={(v) => v && onChange(v)}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue placeholder={field.placeholder ?? "Scegli"} />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  } else if (field.kind === "multi") {
    const picked = (value as string[] | undefined) ?? [];
    control = options.length ? (
      <div role="group" aria-labelledby={id} className="flex flex-wrap gap-1.5">
        {options.map((o) => {
          const on = picked.includes(o.value);
          return (
            <button
              key={o.value}
              type="button"
              aria-pressed={on}
              onClick={() => onChange(on ? picked.filter((p) => p !== o.value) : [...picked, o.value])}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                on ? "border-primary bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {o.label}
            </button>
          );
        })}
      </div>
    ) : (
      <p id={id} className="text-xs text-muted-foreground">Nessuna voce disponibile.</p>
    );
  } else if (field.kind === "tags") {
    control = <TagInput id={id} value={(value as string[] | undefined) ?? []} onChange={onChange} placeholder={field.placeholder} />;
  } else {
    const number = field.kind === "number";
    control = (
      <Input
        id={id}
        type={number ? "number" : "text"}
        required={field.required}
        min={field.min}
        max={field.max}
        placeholder={field.placeholder}
        value={value == null ? "" : String(value)}
        // Empty number = null (not set), never 0.
        onChange={(e) => onChange(number ? (e.target.value === "" ? null : Number(e.target.value)) : e.target.value)}
      />
    );
  }

  return (
    <div className={cn("grid content-start gap-1.5", wide)}>
      <Label htmlFor={field.kind === "multi" ? undefined : id} id={field.kind === "multi" ? id : undefined}>
        {field.label}
      </Label>
      {control}
    </div>
  );
}

// Enter, comma or leaving the field adds a tag; Backspace on an empty input removes the last one.
function TagInput({
  id,
  value,
  onChange,
  placeholder,
}: {
  id: string;
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");
  // Commits every comma-separated piece of `text` but the last, which stays as the draft.
  const type = (text: string, flush = false) => {
    const parts = text.split(",");
    const rest = flush ? "" : parts.pop() ?? "";
    const fresh = parts.map((p) => p.trim()).filter((p, i, all) => p && !value.includes(p) && all.indexOf(p) === i);
    if (fresh.length) onChange([...value, ...fresh]);
    setDraft(rest);
  };
  return (
    <div className="flex min-h-8 flex-wrap items-center gap-1.5 rounded-lg border border-input px-2 py-1 focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50 dark:bg-input/30">
      {value.map((t) => (
        <span key={t} className="inline-flex items-center gap-1 rounded-md bg-secondary px-1.5 py-0.5 text-xs text-secondary-foreground">
          {t}
          <button type="button" aria-label={`Rimuovi ${t}`} onClick={() => onChange(value.filter((v) => v !== t))}
            className="rounded-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/50">
            <X className="size-3" />
          </button>
        </span>
      ))}
      <input
        id={id}
        value={draft}
        placeholder={value.length ? undefined : placeholder}
        onChange={(e) => type(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            type(draft, true);
          } else if (e.key === "Backspace" && !draft && value.length) onChange(value.slice(0, -1));
        }}
        onBlur={() => type(draft, true)}
        className="min-w-24 flex-1 bg-transparent py-0.5 text-sm outline-none placeholder:text-muted-foreground"
      />
    </div>
  );
}
