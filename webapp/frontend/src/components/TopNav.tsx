import { Icon } from "./Icon";

const SOURCES =
  "INDEED • GLASSDOOR • LINKEDIN • REMOTIVE • REMOTEOK • WEWORKREMOTELY • WORKING NOMADS";

type View = "all" | "saved" | "analytics";

interface Props {
  view: View;
  onNav: (view: View) => void;
}

export function TopNav({ view, onNav }: Props) {
  const linkBase = "text-meta-sm transition-colors cursor-pointer";
  const linkActive = "text-primary-fixed border-b-thick border-primary-fixed";
  const linkIdle = "text-on-surface-variant hover:text-primary-fixed";
  return (
    <nav className="flex justify-between items-center w-full px-margin-page py-4 sticky top-0 z-50 bg-surface border-b-thick border-black neo-shadow">
      <div className="flex flex-col">
        <h1 className="text-headline-lg font-black text-secondary-fixed tracking-tighter uppercase leading-none">
          JobSpy
        </h1>
        <p className="text-meta-xs text-outline uppercase tracking-tighter mt-1 hidden sm:block">
          {SOURCES}
        </p>
      </div>
      <div className="hidden md:flex gap-6 items-center">
        <button
          onClick={() => onNav("all")}
          className={`${linkBase} ${view === "all" ? linkActive : linkIdle}`}
        >
          All Jobs
        </button>
        <button
          onClick={() => onNav("saved")}
          className={`${linkBase} ${view === "saved" ? linkActive : linkIdle}`}
        >
          Saved
        </button>
        <button
          onClick={() => onNav("analytics")}
          className={`${linkBase} ${view === "analytics" ? linkActive : linkIdle}`}
        >
          Analytics
        </button>
        <div className="flex gap-2">
          <button className="material-symbols-outlined p-2 text-on-surface-variant hover:bg-surface-container-high transition-all">
            settings
          </button>
          <button className="material-symbols-outlined p-2 text-on-surface-variant hover:bg-surface-container-high transition-all">
            notifications
          </button>
        </div>
        <button className="bg-primary-container text-on-primary-fixed text-meta-sm px-4 py-2 border-thick border-black neo-shadow hover:-translate-y-1 hover:-translate-x-1 hover:neo-shadow-lg transition-all flex items-center gap-1">
          <Icon name="bolt" className="text-base" /> ENGINE
        </button>
      </div>
    </nav>
  );
}
