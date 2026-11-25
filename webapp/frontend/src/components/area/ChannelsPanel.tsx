import { useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Loader2, Plus, RefreshCw, Trash2 } from "lucide-react";
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
      <div>
        <Button onClick={onCreate}>
          <Plus /> Nuovo canale
        </Button>
      </div>
      {!loading && channels.length === 0 && (
        <p className="text-sm text-muted-foreground">Nessun canale. Creane uno per iniziare a ricevere risultati.</p>
      )}
      <ul className="grid gap-2">
        {channels.map((ch) => {
          const busy = refresh.isPending && refresh.variables === ch.id;
          return (
            <li key={ch.id} className="flex flex-wrap items-center gap-3 rounded-xl border bg-card px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{label(ch)}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {ch.name && `${describe(ch)} · `}
                  {ch.last_refresh_at ? `aggiornato ${formatDateTime(ch.last_refresh_at)}` : "mai aggiornato"}
                  {ch.last_refresh_status === "error" && (
                    <span className="ml-1 inline-flex items-center gap-1 text-destructive">
                      <AlertTriangle className="size-3" /> ultimo aggiornamento fallito
                    </span>
                  )}
                </p>
              </div>
              <div className="flex gap-1">
                <Button variant="outline" size="sm" disabled={busy} onClick={() => runRefresh(ch)}>
                  {busy ? <Loader2 className="animate-spin" /> : <RefreshCw />} Aggiorna
                </Button>
                <Button variant="ghost" size="icon-sm" aria-label={`Elimina ${label(ch)}`} onClick={() => setToDelete(ch)}
                  className="text-muted-foreground hover:text-destructive">
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
