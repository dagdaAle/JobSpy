import { useState } from "react";
import { Icon } from "./Icon";
import type { Channel } from "../api/types";
import {
  useCreateChannel,
  useDeleteChannel,
  useRefreshChannel,
} from "../hooks";

interface Props {
  channels: Channel[];
  sites: string[];
  totalCount: number;
  activeChannelId: number | null;
  onSelect: (id: number | null) => void;
}

export function ChannelBar({
  channels,
  sites,
  totalCount,
  activeChannelId,
  onSelect,
}: Props) {
  const [formOpen, setFormOpen] = useState(false);
  const del = useDeleteChannel();
  const refresh = useRefreshChannel();

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => onSelect(null)}
          className={`px-4 py-2 border-thick border-black text-meta-sm uppercase flex items-center gap-2 neo-shadow transition-all ${
            activeChannelId === null
              ? "bg-primary-fixed text-on-primary-fixed"
              : "bg-surface-container text-on-surface hover:-translate-y-0.5"
          }`}
        >
          TUTTI
          <span className="bg-black text-primary-fixed px-1.5 py-0.5 text-[10px] font-black">
            {totalCount}
          </span>
        </button>

        <div className="flex gap-3 overflow-x-auto pb-2">
          {channels.map((ch) => {
            const active = ch.id === activeChannelId;
            const label = ch.name || `${ch.site} - ${ch.search_term}`;
            return (
              <div
                key={ch.id}
                onClick={() => onSelect(ch.id)}
                className={`flex items-center bg-surface-container border-thick border-black pr-1 pl-4 py-1.5 gap-3 neo-card cursor-pointer whitespace-nowrap ${
                  active ? "ring-2 ring-primary-fixed" : ""
                }`}
              >
                <span className="text-meta-sm uppercase text-on-surface">{label}</span>
                {ch.new_count ? (
                  <span className="bg-secondary-fixed text-on-secondary-fixed px-1.5 py-0.5 text-[10px] font-black">
                    +{ch.new_count}
                  </span>
                ) : (
                  <span className="bg-surface-container-highest text-on-surface-variant px-1.5 py-0.5 text-[10px] font-black">
                    {ch.total_count ?? 0}
                  </span>
                )}
                <button
                  title="Aggiorna canale"
                  onClick={(e) => {
                    e.stopPropagation();
                    refresh.mutate(ch.id);
                  }}
                  className="material-symbols-outlined text-sm p-1 hover:bg-primary-container hover:text-on-primary-fixed transition-colors"
                >
                  {refresh.isPending && refresh.variables === ch.id
                    ? "progress_activity"
                    : "refresh"}
                </button>
                <button
                  title="Elimina canale"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (activeChannelId === ch.id) onSelect(null);
                    del.mutate(ch.id);
                  }}
                  className="material-symbols-outlined text-sm p-1 hover:bg-error-container hover:text-on-error-container transition-colors"
                >
                  close
                </button>
              </div>
            );
          })}
        </div>

        <button
          onClick={() => setFormOpen((v) => !v)}
          className="bg-secondary-fixed text-on-secondary-fixed px-4 py-2 border-thick border-black text-meta-sm uppercase flex items-center gap-2 neo-button ml-auto"
        >
          <Icon name={formOpen ? "expand_less" : "add"} />
          {formOpen ? "CHIUDI" : "NUOVO CANALE"}
        </button>
      </div>

      {formOpen && (
        <NewChannelForm
          sites={sites}
          onDone={() => setFormOpen(false)}
        />
      )}
    </section>
  );
}

function NewChannelForm({
  sites,
  onDone,
}: {
  sites: string[];
  onDone: () => void;
}) {
  const create = useCreateChannel();
  const [form, setForm] = useState({
    site: sites[0] ?? "linkedin",
    search_term: "",
    location: "",
    distance_km: 50,
    results_wanted: 100,
    hours_old: 72,
    is_remote: false,
  });

  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.search_term.trim()) return;
    create.mutate(
      { ...form, hours_old: form.hours_old || null },
      { onSuccess: onDone },
    );
  };

  return (
    <div className="bg-surface-container border-thick border-black p-6 neo-shadow-lg">
      <h3 className="text-headline-md uppercase mb-6 border-b-thin border-black pb-2">
        Configura Scanner Lavoro
      </h3>
      <form
        onSubmit={submit}
        className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6"
      >
        <Field label="Sorgente">
          <select
            className="neo-input p-3 text-meta-sm w-full"
            value={form.site}
            onChange={(e) => set("site", e.target.value)}
          >
            {sites.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Termine Ricerca">
          <input
            className="neo-input p-3 text-meta-sm w-full"
            placeholder="es. Senior Frontend React"
            value={form.search_term}
            onChange={(e) => set("search_term", e.target.value)}
          />
        </Field>
        <Field label="Località">
          <input
            className="neo-input p-3 text-meta-sm w-full"
            placeholder="es. Milano, Italia"
            value={form.location}
            onChange={(e) => set("location", e.target.value)}
          />
        </Field>
        <Field label="Raggio (km)">
          <input
            type="number"
            className="neo-input p-3 text-meta-sm w-full"
            value={form.distance_km}
            onChange={(e) => set("distance_km", Number(e.target.value))}
          />
        </Field>
        <Field label="Max Risultati">
          <input
            type="number"
            className="neo-input p-3 text-meta-sm w-full"
            value={form.results_wanted}
            onChange={(e) => set("results_wanted", Number(e.target.value))}
          />
        </Field>
        <Field label="Fino a (ore fa)">
          <input
            type="number"
            className="neo-input p-3 text-meta-sm w-full"
            value={form.hours_old}
            onChange={(e) => set("hours_old", Number(e.target.value))}
          />
        </Field>
        <div className="flex items-end">
          <label className="flex items-center gap-2 cursor-pointer group py-3">
            <input
              type="checkbox"
              className="w-6 h-6 border-thick border-black bg-surface-container accent-primary-fixed"
              checked={form.is_remote}
              onChange={(e) => set("is_remote", e.target.checked)}
            />
            <span className="text-meta-sm uppercase group-hover:text-primary-fixed transition-colors">
              Solo Remote
            </span>
          </label>
        </div>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={create.isPending}
            className="w-full bg-primary-fixed text-on-primary-fixed text-headline-md py-3 border-thick border-black neo-shadow hover:-translate-y-1 transition-all uppercase disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {create.isPending ? (
              <>
                <Icon name="progress_activity" className="animate-spin" /> RICERCA...
              </>
            ) : (
              "AVVIA SPYING ENGINE"
            )}
          </button>
        </div>
      </form>
      {create.isError && (
        <p className="text-error text-meta-sm mt-4 uppercase">
          {(create.error as Error).message}
        </p>
      )}
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-meta-xs uppercase text-outline">{label}</label>
      {children}
    </div>
  );
}
