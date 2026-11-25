import { useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Loader2, MoreHorizontal, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { Channel } from "../api/types";
import { useDeleteChannel, useRefreshChannel } from "../hooks";
import { formatDateTime, siteDot, siteLabel } from "../lib/format";
import { NewChannelDialog } from "./NewChannelDialog";

interface Props {
  channels: Channel[];
  sites: string[];
  allCount: number;
  activeChannelId: number | null;
  onSelect: (id: number | null) => void;
}

export function ChannelBar({ channels, sites, allCount, activeChannelId, onSelect }: Props) {
  const [creating, setCreating] = useState(false);
  const [toDelete, setToDelete] = useState<Channel | null>(null);
  const [editing, setEditing] = useState<Channel | null>(null);
  const del = useDeleteChannel();
  const refresh = useRefreshChannel();

  const runRefresh = (ch: Channel) => {
    const label = ch.name || ch.search_term;
    toast.promise(refresh.mutateAsync(ch.id), {
      loading: `Aggiorno "${label}"…`,
      success: (r) =>
        r.new_count ? `"${label}": ${r.new_count} offerte nuove` : `"${label}": nessuna offerta nuova`,
      error: (e: Error) => `"${label}": ${e.message}`,
    });
  };

  return (
    <section aria-label="Canali di ricerca">
          <div className="flex flex-wrap items-center gap-2">
            <Pill active={activeChannelId === null} onClick={() => onSelect(null)} count={allCount}>
              Tutti i canali
            </Pill>
            {channels.map((ch) => {
              const busy = refresh.isPending && refresh.variables === ch.id;
              const failed = ch.last_refresh_status === "error";
              return (
                <Pill
                  key={ch.id}
                  failed={failed}
                  active={ch.id === activeChannelId}
                  onClick={() => onSelect(ch.id)}
                  count={ch.total_count ?? 0}
                  fresh={ch.new_count ?? 0}
                  lead={
                    busy ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : failed ? (
                      <Tooltip>
                        <TooltipTrigger render={<span className="text-destructive" />}>
                          <AlertTriangle className="size-3.5" />
                        </TooltipTrigger>
                        <TooltipContent>
                          Ultimo aggiornamento fallito ({formatDateTime(ch.last_refresh_at)}). Vedi Log.
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      <span className={cn("size-1.5 rounded-full", siteDot(ch.site))} />
                    )
                  }
                  menu={
                    <DropdownMenu>
                      <DropdownMenuTrigger
                        render={
                          <Button
                            variant="ghost"
                            size="icon-xs"
                            aria-label={`Azioni canale ${ch.name}`}
                            className={cn("-mr-0.5", ch.id === activeChannelId ? "text-primary-foreground hover:bg-transparent hover:text-primary-foreground" : "text-muted-foreground")}
                          />
                        }
                      >
                        <MoreHorizontal />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-56">
                        <div className="px-2 py-1.5 text-xs text-muted-foreground">
                          {siteLabel(ch.site)} · “{ch.search_term}”
                          {ch.location && ` · ${ch.location}`}
                          <br />
                          {ch.last_refresh_at
                            ? `Aggiornato ${formatDateTime(ch.last_refresh_at)}`
                            : "Mai aggiornato"}
                        </div>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem disabled={busy} onClick={() => runRefresh(ch)}>
                          <RefreshCw /> Aggiorna ora
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => setEditing(ch)}>
                          <Pencil /> Modifica filtri
                        </DropdownMenuItem>
                        <DropdownMenuItem variant="destructive" onClick={() => setToDelete(ch)}>
                          <Trash2 /> Elimina canale
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  }
                >
                  {ch.name || `${siteLabel(ch.site)} · ${ch.search_term}`}
                </Pill>
              );
            })}
            <button
              type="button"
              onClick={() => setCreating(true)}
              className="flex h-9 shrink-0 items-center gap-1.5 rounded-full border border-dashed border-input px-3.5 text-[13px] font-medium text-muted-foreground outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <Plus className="size-3.5" /> Nuovo canale
            </button>
          </div>

      <NewChannelDialog open={creating} onOpenChange={setCreating} sites={sites} />
      <NewChannelDialog
        open={editing !== null}
        onOpenChange={(o) => !o && setEditing(null)}
        sites={sites}
        channel={editing}
      />

      <Dialog open={toDelete !== null} onOpenChange={(o) => !o && setToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminare “{toDelete?.name}”?</DialogTitle>
            <DialogDescription>
              Il canale smette di aggiornarsi. Le offerte già salvate e i tuoi preferiti restano.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Annulla</DialogClose>
            <Button
              variant="destructive"
              onClick={() => {
                if (!toDelete) return;
                if (activeChannelId === toDelete.id) onSelect(null);
                del.mutate(toDelete.id, {
                  onSuccess: () => toast.success(`Canale “${toDelete.name}” eliminato`),
                });
                setToDelete(null);
              }}
            >
              Elimina
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

function Pill({
  active,
  onClick,
  count,
  fresh = 0,
  failed,
  lead,
  menu,
  children,
}: {
  active: boolean;
  onClick: () => void;
  count: number;
  fresh?: number;
  failed?: boolean;
  lead?: React.ReactNode;
  menu?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex h-9 shrink-0 items-center rounded-full border pr-1.5 text-[13px] font-medium transition-colors",
        active ? "border-primary bg-primary text-primary-foreground" : failed ? "border-destructive bg-card text-foreground" : "bg-card text-foreground hover:bg-muted",
        !menu && "pr-0",
      )}
    >
      <button
        type="button"
        onClick={onClick}
        aria-pressed={active}
        className="flex h-full items-center gap-2 rounded-full pr-1.5 pl-3.5 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {lead}
        <span className="whitespace-nowrap">{children}</span>
        <span className={cn("rounded-full px-1.5 font-mono text-[11px] leading-4 font-semibold", active ? "bg-area-lavoro text-primary-foreground" : "bg-muted text-muted-foreground")}>{count}</span>
        {fresh > 0 && (
          <span className="rounded-full bg-candidati px-1.5 font-mono text-[11px] leading-4 font-semibold text-candidati-foreground">
            +{fresh}
          </span>
        )}
      </button>
      {menu}
      {!menu && <span className="w-1.5" />}
    </div>
  );
}
