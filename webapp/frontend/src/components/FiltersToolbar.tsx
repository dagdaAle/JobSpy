import { Download, RefreshCw, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { api } from "../api/client";

export type SortKey = "recent" | "score";

export interface Filters {
  search: string;
  remoteOnly: boolean;
  minScore: number;
  sort: SortKey;
}

const SORT_ITEMS = [
  { value: "recent", label: "Più recenti" },
  { value: "score", label: "Più adatte a me" },
];

interface Props {
  filters: Filters;
  onChange: (patch: Partial<Filters>) => void;
  onRefresh: () => void;
  refreshing?: boolean;
  resultCount: number;
}

export function FiltersToolbar({ filters, onChange, onRefresh, refreshing, resultCount }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
      <div className="relative w-full sm:w-72">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="pl-8"
          placeholder="Cerca titolo, azienda, città…"
          value={filters.search}
          onChange={(e) => onChange({ search: e.target.value })}
        />
      </div>

      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        <Switch checked={filters.remoteOnly} onCheckedChange={(v) => onChange({ remoteOnly: v })} />
        Solo remoto
      </label>

      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <span className="whitespace-nowrap">Match minimo</span>
        <Slider
          className="w-28"
          min={0}
          max={100}
          step={5}
          value={filters.minScore}
          onValueChange={(v) => onChange({ minScore: Array.isArray(v) ? v[0] : v })}
        />
        <span className="w-9 tabular-nums text-foreground">{filters.minScore}%</span>
      </div>

      <Select
        items={SORT_ITEMS}
        value={filters.sort}
        onValueChange={(v) => v && onChange({ sort: v as SortKey })}
      >
        <SelectTrigger size="sm" className="w-40">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SORT_ITEMS.map((s) => (
            <SelectItem key={s.value} value={s.value}>
              {s.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <div className="ml-auto flex items-center gap-2">
        <span className="mr-1 text-sm tabular-nums text-muted-foreground">
          {resultCount} {resultCount === 1 ? "offerta" : "offerte"}
        </span>
        <Button variant="ghost" size="icon" onClick={onRefresh} aria-label="Ricarica">
          <RefreshCw className={refreshing ? "animate-spin" : ""} />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="ghost" size="icon" aria-label="Esporta" />}>
            <Download />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem render={<a href={api.exportUrl("csv")} />}>Esporta CSV</DropdownMenuItem>
            <DropdownMenuItem render={<a href={api.exportUrl("xlsx")} />}>Esporta Excel</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
