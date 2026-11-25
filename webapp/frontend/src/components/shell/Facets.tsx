// Facet filters in the sidebar: one group of checkboxes per facet, every box filters the list.
export interface FacetOption<K extends string> {
  key: K;
  label: string;
  count?: number;
}

export function Facets({ onReset, children }: { onReset?: () => void; children: React.ReactNode }) {
  return (
    <section className="space-y-5" aria-label="Filtri">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Filtri</h2>
        {onReset && (
          <button type="button" onClick={onReset} className="text-[13px] font-medium text-muted-foreground hover:text-foreground">
            Azzera
          </button>
        )}
      </div>
      {children}
    </section>
  );
}

export function FacetGroup<K extends string>({ title, options, selected, onToggle }: { title: string; options: FacetOption<K>[]; selected: Set<K>; onToggle: (key: K) => void }) {
  return (
    <fieldset className="space-y-0.5">
      <legend className="pb-1 text-xs font-medium text-muted-foreground">{title}</legend>
      {options.map((o) => (
        <label key={o.key} className="flex h-7 cursor-pointer items-center gap-2.5 text-sm">
          <input type="checkbox" checked={selected.has(o.key)} onChange={() => onToggle(o.key)} className="size-4.5 cursor-pointer rounded accent-primary" />
          <span className="flex-1">{o.label}</span>
          {o.count != null && <span className="font-mono text-xs text-muted-foreground">{o.count}</span>}
        </label>
      ))}
    </fieldset>
  );
}

/** Toggle helper for Set-based facet state. */
export function toggle<K>(set: Set<K>, key: K): Set<K> {
  const next = new Set(set);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  return next;
}
