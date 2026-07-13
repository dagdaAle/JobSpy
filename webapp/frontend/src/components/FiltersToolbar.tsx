import { Icon } from "./Icon";
import { api } from "../api/client";

export interface Filters {
  search: string;
  remoteOnly: boolean;
  minScore: number;
  saved: "all" | "liked" | "hidden";
}

interface Props {
  filters: Filters;
  onChange: (patch: Partial<Filters>) => void;
  onRefresh: () => void;
  refreshing?: boolean;
}

export function FiltersToolbar({ filters, onChange, onRefresh, refreshing }: Props) {
  return (
    <div className="bg-surface border-thick border-black p-4 flex flex-col lg:flex-row gap-6 items-center neo-shadow">
      <div className="relative w-full lg:w-96">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">
          search
        </span>
        <input
          className="neo-input w-full pl-10 pr-4 py-2 text-meta-sm"
          placeholder="Cerca tra i risultati..."
          value={filters.search}
          onChange={(e) => onChange({ search: e.target.value })}
        />
      </div>

      <div className="flex flex-wrap items-center gap-4 w-full lg:w-auto">
        <select
          className="neo-input py-2 px-4 text-meta-sm bg-surface"
          value={filters.saved}
          onChange={(e) => onChange({ saved: e.target.value as Filters["saved"] })}
        >
          <option value="all">Tutti i lavori</option>
          <option value="liked">Preferiti</option>
          <option value="hidden">Nascosti</option>
        </select>

        <label className="flex items-center gap-2 cursor-pointer group">
          <input
            type="checkbox"
            className="w-6 h-6 border-thick border-black bg-surface-container accent-primary-fixed"
            checked={filters.remoteOnly}
            onChange={(e) => onChange({ remoteOnly: e.target.checked })}
          />
          <span className="text-meta-sm uppercase group-hover:text-primary-fixed transition-colors">
            Solo Remote
          </span>
        </label>

        <div className="flex items-center gap-3">
          <span className="text-meta-xs uppercase text-outline">Min AI Score:</span>
          <input
            type="range"
            min={0}
            max={100}
            value={filters.minScore}
            onChange={(e) => onChange({ minScore: Number(e.target.value) })}
            className="accent-primary-fixed bg-black h-2 border-thin border-black appearance-none w-32"
          />
          <span className="text-meta-sm font-bold w-10">{filters.minScore}%</span>
        </div>
      </div>

      <div className="flex gap-2 ml-auto">
        <button
          onClick={onRefresh}
          className="neo-button bg-surface p-2 flex items-center gap-2 text-meta-xs uppercase"
        >
          <Icon name="refresh" className={refreshing ? "animate-spin" : ""} /> REFRESH
        </button>
        <a
          href={api.exportUrl("csv")}
          className="neo-button bg-surface p-2 flex items-center gap-2 text-meta-xs uppercase"
        >
          <Icon name="download" /> CSV
        </a>
        <a
          href={api.exportUrl("xlsx")}
          className="neo-button bg-surface p-2 flex items-center gap-2 text-meta-xs uppercase"
        >
          <Icon name="table_view" /> EXCEL
        </a>
      </div>
    </div>
  );
}
