import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { AreaChannelRequest, AreaKey, AreaMeta } from "../../api/areas";
import { useCreateAreaChannel } from "../../hooks/areas";
import { FormField, type FieldConfig, type FormValues } from "./fields";

// Blank text means "not set": the backend gets null, not "".
const clean = (v: FormValues): AreaChannelRequest =>
  Object.fromEntries(Object.entries(v).map(([k, x]) => [k, typeof x === "string" ? x.trim() || null : x]));

export function ChannelDialog({
  area,
  open,
  onOpenChange,
  fields,
  defaults,
  meta,
  hint,
  canSubmit = () => true,
  toRequest = (v) => v,
}: {
  area: AreaKey;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  fields: FieldConfig[];
  defaults: FormValues;
  meta?: AreaMeta;
  hint?: string;
  canSubmit?: (values: FormValues) => boolean;
  toRequest?: (values: FormValues) => FormValues;
}) {
  const create = useCreateAreaChannel(area);
  const [form, setForm] = useState<FormValues>(defaults);
  useEffect(() => {
    if (open) setForm(defaults);
  }, [open, defaults]);
  const ok = canSubmit(form);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ok) return;
    create.mutate(clean(toRequest(form)), {
      onSuccess: (r) => {
        toast.success(`Canale creato: ${r.new_count} nuovi risultati`);
        onOpenChange(false);
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !create.isPending && onOpenChange(o)}>
      <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-lg">
        <form onSubmit={submit} className="grid gap-5">
          <DialogHeader>
            <DialogTitle>Nuovo canale</DialogTitle>
            <DialogDescription>
              Un canale è una ricerca su una fonte, aggiornata ogni mattina. La prima ricerca parte subito.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 sm:grid-cols-2">
            {fields.map((f) => (
              <FormField key={f.name} field={f} meta={meta} value={form[f.name]}
                onChange={(v) => setForm((s) => ({ ...s, [f.name]: v }))} />
            ))}
          </div>

          {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
          {create.isError && <p className="text-sm text-destructive">{(create.error as Error).message}</p>}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={create.isPending}>
              Annulla
            </Button>
            <Button type="submit" disabled={create.isPending || !ok}>
              {create.isPending && <Loader2 className="animate-spin" />}
              {create.isPending ? "Cerco i primi risultati…" : "Crea canale"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
