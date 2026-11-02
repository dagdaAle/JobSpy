import { useEffect, useId, useState } from "react";
import { FileCheck2, Loader2, ScanText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "../api/client";
import type { CvPdfCheck, CvReview } from "../api/types";

export function CvReviewPanel({ id, source, dirty, jobUrl, onCreated }: {
  id: number; source: string; dirty: boolean; jobUrl?: string;
  onCreated: (id: number) => void;
}) {
  const fid = useId();
  const [facts, setFacts] = useState("");
  const [review, setReview] = useState<CvReview | null>(null);
  const [chosen, setChosen] = useState<number[]>([]);
  const [check, setCheck] = useState<CvPdfCheck | null>(null);
  const [busy, setBusy] = useState<"review" | "save" | "check" | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { setReview(null); setChosen([]); setCheck(null); setError(""); }, [source]);

  async function run(action: "review" | "save" | "check") {
    setBusy(action); setError("");
    try {
      if (action === "review") {
        setReview(null); setChosen([]);
        setReview(await api.reviewCv(id, facts, jobUrl));
      } else if (action === "check") {
        setCheck(null);
        setCheck(await api.checkCvPdf(id));
      } else if (review) {
        const result = await api.reviseCv(id, review.source_hash, review.patches.filter((_, i) => chosen.includes(i)));
        setReview(null); setChosen([]);
        onCreated(result.cv.id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Operazione non riuscita");
    } finally { setBusy(null); }
  }

  return (
    <section className="space-y-4 rounded-lg border p-4" aria-label="Revisione mirata del CV">
      <div className="space-y-1">
        <h3 className="font-medium">Revisione mirata</h3>
        <p className="text-sm text-muted-foreground">
          Piccole correzioni al CV esistente. Confronta prima e dopo e salva solo quelle che scegli, in una copia.
          {jobUrl && " L’offerta aperta viene usata come riferimento."}
        </p>
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${fid}-facts`}>Dati che confermi (facoltativi)</Label>
        <Textarea id={`${fid}-facts`} maxLength={3000} value={facts} disabled={busy !== null}
          onChange={(e) => { setFacts(e.target.value); setReview(null); setChosen([]); }}
          placeholder="Es. email da usare; dove hai usato Java; strumenti usati in un progetto. Inserisci solo informazioni vere." />
        <p className="text-xs text-muted-foreground">Le informazioni non documentate diventano domande, non nuove competenze nel CV.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" disabled={dirty || busy !== null} onClick={() => run("review")}>
          {busy === "review" ? <Loader2 className="animate-spin" /> : <ScanText />} Proponi correzioni
        </Button>
        <Button variant="outline" disabled={dirty || busy !== null} onClick={() => run("check")}>
          {busy === "check" ? <Loader2 className="animate-spin" /> : <FileCheck2 />} Verifica testo del PDF
        </Button>
      </div>
      {dirty && <p className="text-sm text-muted-foreground">Salva le modifiche nell’editor prima di eseguire o applicare la revisione.</p>}
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      {review && <div className="space-y-4" aria-live="polite">
        {review.observations.length > 0 && <div>
          <h4 className="text-sm font-medium">Osservazioni sul testo</h4>
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
            {review.observations.map((o, i) => <li key={i}>{o}</li>)}
          </ul>
        </div>}
        {review.questions.length > 0 && <div className="rounded-md bg-muted/50 p-3 text-sm">
          <h4 className="font-medium">Da chiarire con te</h4>
          <ul className="list-disc space-y-1 pl-5">{review.questions.map((q, i) => <li key={i}>{q}</li>)}</ul>
          <p className="mt-2 text-muted-foreground">Rispondi nei dati confermati e ripeti la revisione.</p>
        </div>}
        {review.patches.map((patch, i) => <div key={i} className="space-y-2 rounded-md border p-3">
          <label className="flex items-start gap-2 text-sm font-medium">
            <input type="checkbox" className="mt-1" checked={chosen.includes(i)} disabled={dirty || busy !== null}
              onChange={(e) => setChosen((old) => e.target.checked ? [...old, i] : old.filter((n) => n !== i))} />
            {patch.reason}
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <div><p className="text-xs font-medium text-muted-foreground">Prima</p><p className="whitespace-pre-wrap break-words text-sm">{patch.before}</p></div>
            <div><p className="text-xs font-medium text-muted-foreground">Dopo</p><p className="whitespace-pre-wrap break-words text-sm">{patch.after}</p></div>
          </div>
        </div>)}
        {review.patches.length === 0 ? <p className="text-sm text-muted-foreground">Nessuna correzione applicabile proposta. Controlla le osservazioni e le domande.</p> : <>
          <p className="text-xs text-muted-foreground">Controlla che ogni proposta AI rispecchi la tua esperienza. Nessuna modifica è selezionata automaticamente.</p>
          <Button disabled={dirty || busy !== null || chosen.length === 0} onClick={() => run("save")}>
            {busy === "save" && <Loader2 className="animate-spin" />} Salva {chosen.length} {chosen.length === 1 ? "correzione" : "correzioni"} in una copia
          </Button>
          <p className="text-xs text-muted-foreground">Il CV originale e il CV predefinito per il match restano quelli attuali.</p>
        </>}
      </div>}
      {check && <div className="space-y-2 rounded-md bg-muted/40 p-3 text-sm" aria-live="polite">
        <p className="font-medium">PDF esportato: {check.pages} {check.pages === 1 ? "pagina" : "pagine"} · {check.chars} caratteri estratti</p>
        {check.warnings.length === 0 && <p>Il PDF contiene testo estraibile. Controlla qui sotto che l’ordine sia corretto.</p>}
        {check.warnings.map((w, i) => <p key={i}>{w}</p>)}
        <details><summary className="cursor-pointer">Mostra il testo letto dal PDF</summary>
          <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs">{check.text}</pre>
        </details>
        <p className="text-xs text-muted-foreground">{check.scope}. Non garantisce l’accettazione di una candidatura.</p>
      </div>}
    </section>
  );
}
