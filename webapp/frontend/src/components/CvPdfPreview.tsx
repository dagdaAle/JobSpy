import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { Button } from "@/components/ui/button";

export function CvPdfPreview({ id, version }: { id: number; version: string }) {
  const [page, setPage] = useState(1);
  const [imageError, setImageError] = useState(false);
  const info = useQuery({ queryKey: ["cv-preview", id, version], queryFn: () => api.cvPreviewInfo(id) });
  useEffect(() => { setPage(1); setImageError(false); }, [id, version]);
  if (info.isError) return <p role="alert" className="text-sm text-destructive">Anteprima non disponibile: {info.error.message}</p>;
  if (!info.data) return <p className="text-sm text-muted-foreground">Preparazione anteprima PDF…</p>;
  return <div className="overflow-hidden rounded-lg border bg-slate-200/60">
    <div className="flex items-center justify-center gap-3 border-b bg-background p-2 text-sm">
      <Button size="sm" variant="ghost" disabled={page <= 1} onClick={() => { setPage((p) => p - 1); setImageError(false); }}>Precedente</Button>
      <span>Pagina {page} di {info.data.pages}</span>
      <Button size="sm" variant="ghost" disabled={page >= info.data.pages} onClick={() => { setPage((p) => p + 1); setImageError(false); }}>Successiva</Button>
    </div>
    {imageError ? <p role="alert" className="p-4 text-sm">Impossibile caricare la pagina. Puoi aprire il PDF con il pulsante PDF.</p> :
      <img key={`${id}-${version}-${page}`} src={`/cvs/${id}/preview/${page}?v=${encodeURIComponent(version)}`}
        alt={`Anteprima del PDF salvato, pagina ${page} di ${info.data.pages}`} onError={() => setImageError(true)}
        className="mx-auto my-4 h-auto w-full max-w-[850px] bg-white shadow-md" />}
  </div>;
}
