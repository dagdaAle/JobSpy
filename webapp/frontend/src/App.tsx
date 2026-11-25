import { useState } from "react";
import { AppHeader, AREAS, type Area } from "./components/AppHeader";
import { LavoroArea } from "./components/LavoroArea";
import { PaArea } from "./components/pa/PaArea";
import { GareArea } from "./components/gare/GareArea";

function areaFromUrl(): Area {
  const a = new URLSearchParams(window.location.search).get("area");
  return AREAS.some((x) => x.area === a) ? (a as Area) : "lavoro";
}

export default function App() {
  const [area, setArea] = useState<Area>(areaFromUrl);

  // The area lives in ?area= so a reload stays put; other params (e.g. ?cv=) are kept.
  const changeArea = (next: Area) => {
    const url = new URL(window.location.href);
    if (next === "lavoro") url.searchParams.delete("area");
    else url.searchParams.set("area", next);
    window.history.replaceState(null, "", url);
    setArea(next);
  };

  if (area === "lavoro") return <LavoroArea onArea={changeArea} />;

  return (
    <div className="min-h-screen">
      <AppHeader area={area} onArea={changeArea} />
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
        {area === "pa" ? <PaArea /> : <GareArea />}
      </main>
    </div>
  );
}
