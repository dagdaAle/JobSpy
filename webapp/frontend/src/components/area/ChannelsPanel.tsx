import { useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Loader2, Plus, RefreshCw, Trash2, Radio } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { AreaChannel, AreaKey } from "../../api/areas";
import { useDeleteAreaChannel, useRefreshAreaChannel } from "../../hooks/areas";
import { formatDateTime } from "../../lib/format";

export function ChannelsPanel({
  area,
  channels,
  loading,
  describe,
  onCreate,
  onDeleted,
}: {
  area: AreaKey;
  channels: AreaChannel[];
  loading?: boolean;
  describe: (ch: AreaChannel) => string;
  onCreate: () => void;
  onDeleted: (id: number) => void;
}) {
  const [toDelete, setToDelete] = useState<AreaChannel | null>(null);
  const del = useDeleteAreaChannel(area);
  const refresh = useRefreshAreaChannel(area);
  const label = (ch: AreaChannel) => ch.name || describe(ch);

  const runRefresh = (ch: AreaChannel) => {
    toast.promise(refresh.mutateAsync(ch.id), {
      loading: `Aggiorno "${label(ch)}"…`,
      success: (r) => (r.new_count ? `"${label(ch)}": ${r.new_count} nuovi risultati` : `"${label(ch)}": niente di nuovo`),
      error: (e: Error) => `"${label(ch)}": ${e.message}`,
    });
  };

  return (
    <section className="space-y-3">
      {!loading && channels.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-input bg-card px-6 py-14 text-center">
          <p className="font-heading text-lg font-semibold">Nessun canale</p>
          <p className="max-w-sm text-sm text-muted-foreground">Un canale è una ricerca salvata che gira ogni mattina.</p>
          <Button className="h-10 px-4" onClick={onCreate}><Plus /> Nuovo canale</Button>
        </div>
      )}
      <ul className="grid gap-3">
        {channels.map((ch) => {
          const busy = refresh.isPending && refresh.variables === ch.id;
          const failed = ch.last_refresh_status === "error";
          return (
            <li key={ch.id} className={cn("flex flex-wrap items-center gap-4 rounded-lg border bg-card px-5 py-4", failed && "border-destructive")}>
              <span className={cn("flex size-10 shrink-0 items-center justify-center rounded-md [&_svg]:size-4.5",
                failed ? "bg-destructive-soft text-destructive" : area === "pa" ? "bg-area-pa-soft text-area-pa" : "bg-area-gare-soft text-area-gare")}>
                {failed ? <AlertTriangle /> : <Radio />}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[15px] font-semibold">{label(ch)}</p>
                <p className="truncate text-[13px] text-muted-foreground">{describe(ch)}</p>
                {failed && <p className="text-xs text-destructive">Ultimo aggiornamento fallito: il prossimo tentativo è al giro di domattina.</p>}
              </div>
              <p className="w-44 text-xs text-muted-foreground">
                {ch.last_refresh_at ? `aggiornato ${formatDateTime(ch.last_refresh_at)}` : "mai aggiornato"}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" className="h-9 px-3.5" disabled={busy} onClick={() => runRefresh(ch)}>
                  {busy ? <Loader2 className="animate-spin" /> : <RefreshCw />} {failed ? "Riprova" : "Aggiorna"}
                </Button>
                <Button variant="outline" size="icon" aria-label={`Elimina ${label(ch)}`} onClick={() => setToDelete(ch)}
                  className="size-9 text-destructive hover:text-destructive">
                  <Trash2 />
                </Button>
              </div>
            </li>
          );
        })}
      </ul>

      <Dialog open={toDelete !== null} onOpenChange={(o) => !o && setToDelete(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Eliminare il canale?</DialogTitle>
            <DialogDescription>
              {toDelete && `"${label(toDelete)}" smette di aggiornarsi. I risultati già trovati e i tuoi giudizi restano.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Annulla</DialogClose>
            <Button
              variant="destructive"
              disabled={del.isPending}
              onClick={() => {
                const ch = toDelete!;
                del.mutate(ch.id, {
                  onSuccess: () => {
                    toast.success("Canale eliminato");
                    onDeleted(ch.id);
                    setToDelete(null);
                  },
                  onError: (e) => toast.error(e.message),
                });
              }}
            >
              {del.isPending && <Loader2 className="animate-spin" />}
              Elimina
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
