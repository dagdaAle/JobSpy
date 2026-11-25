import { useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, CircleHelp, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { AreaKey, AreaMeta } from "../../api/areas";
import { useAreaProfile, useSaveAreaProfile } from "../../hooks/areas";
import { FormField, type FieldConfig, type FormValues } from "./fields";

export function ProfileForm({
  area,
  fields,
  defaults,
  meta,
  hint,
}: {
  area: AreaKey;
  fields: FieldConfig[];
  defaults: FormValues;
  meta?: AreaMeta;
  hint?: string;
}) {
  const profile = useAreaProfile(area);
  if (profile.isLoading) return <Skeleton className="h-80 rounded-xl" />;
  if (profile.isError) {
    return (
      <p className="flex items-center gap-2 text-sm text-destructive">
        <AlertTriangle className="size-4" /> {(profile.error as Error).message}
      </p>
    );
  }
  // Remount on new server data so the form starts from what is saved.
  return <Editor key={profile.dataUpdatedAt} area={area} fields={fields} meta={meta} hint={hint}
    initial={{ ...defaults, ...profile.data }} />;
}

function Editor({
  area,
  fields,
  meta,
  hint,
  initial,
}: {
  area: AreaKey;
  fields: FieldConfig[];
  meta?: AreaMeta;
  hint?: string;
  initial: FormValues;
}) {
  const save = useSaveAreaProfile(area);
  const [form, setForm] = useState(initial);
  const dirty = JSON.stringify(form) !== JSON.stringify(initial);

  return (
    <form
      className="grid max-w-3xl gap-5 rounded-xl border bg-card p-6 sm:p-8"
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate(form, {
          onSuccess: () => toast.success("Profilo salvato: le valutazioni si aggiornano senza nuova analisi"),
          onError: (err) => toast.error(err.message),
        });
      }}
    >
      {hint && (
        <p className={cn("flex items-start gap-2.5 rounded-md p-3 text-[13px] leading-relaxed", area === "pa" ? "bg-area-pa-soft" : "bg-area-gare-soft")}>
          <CircleHelp className={cn("mt-0.5 size-4 shrink-0", area === "pa" ? "text-area-pa" : "text-area-gare")} />
          {hint}
        </p>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        {fields.map((f) => (
          <FormField key={f.name} field={f} meta={meta} value={form[f.name]}
            onChange={(v) => setForm((s) => ({ ...s, [f.name]: v }))} />
        ))}
      </div>
      <div className="flex items-center justify-end gap-3">
        {dirty && <span className="text-[13px] text-muted-foreground">Modifiche non salvate</span>}
        <Button type="submit" className="h-10 px-5" disabled={save.isPending || !dirty}>
          {save.isPending && <Loader2 className="animate-spin" />}
          Salva profilo
        </Button>
      </div>
    </form>
  );
}
