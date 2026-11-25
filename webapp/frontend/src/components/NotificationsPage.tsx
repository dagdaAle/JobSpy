// Web Push on this device: state, enable/disable, test, and which areas notify (specs/005-pwa-notifiche).
import { useEffect, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { BellOff, BellRing, Loader2, Send, Smartphone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { req } from "../api/client";
import { AREAS, type Area } from "./AppHeader";

type State = "loading" | "ios-home" | "unsupported" | "no-keys" | "denied" | "off" | "on";

const post = <T,>(url: string, body: unknown) => req<T>(url, { method: "POST", body: JSON.stringify(body) });

// The VAPID public key comes base64url-encoded; pushManager wants the raw bytes.
function keyBytes(b64: string): Uint8Array<ArrayBuffer> {
  const raw = atob((b64 + "=".repeat((4 - (b64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

const isIos = () => /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
const standalone = () => window.matchMedia("(display-mode: standalone)").matches || (navigator as { standalone?: boolean }).standalone === true;
const supported = () => "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

async function currentSubscription() {
  const reg = await navigator.serviceWorker.register("/sw.js");
  return reg.pushManager.getSubscription();
}

export function NotificationsPage() {
  const [state, setState] = useState<State>("loading");
  const [key, setKey] = useState<string | null>(null);
  const [sub, setSub] = useState<PushSubscription | null>(null);
  const [areas, setAreas] = useState<Area[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      if (!supported()) return setState(isIos() && !standalone() ? "ios-home" : "unsupported");
      const k = await req<{ configured: boolean; public_key: string | null }>("/push/key");
      if (!k.configured || !k.public_key) return setState("no-keys");
      setKey(k.public_key);
      if (Notification.permission === "denied") return setState("denied");
      const s = await currentSubscription();
      if (s && Notification.permission === "granted") {
        // Re-sending the subscription is idempotent and returns the areas saved for it.
        setAreas((await post<{ areas: Area[] }>("/push/subscribe", s.toJSON())).areas);
        setSub(s);
        return setState("on");
      }
      setState("off");
    })().catch((err: Error) => {
      toast.error(err.message);
      setState("unsupported");
    });
  }, []);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  // The permission prompt must come straight from the tap (iOS refuses it otherwise).
  const enable = () =>
    run(async () => {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") return setState(permission === "denied" ? "denied" : "off");
      const reg = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;
      const s = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(key!) });
      setAreas((await post<{ areas: Area[] }>("/push/subscribe", s.toJSON())).areas);
      setSub(s);
      setState("on");
      toast.success("Notifiche attive su questo dispositivo");
    });

  const disable = () =>
    run(async () => {
      if (sub) {
        await post("/push/unsubscribe", { endpoint: sub.endpoint });
        await sub.unsubscribe();
      }
      setSub(null);
      setState("off");
      toast.success("Notifiche disattivate su questo dispositivo");
    });

  const test = () =>
    run(async () => {
      await post("/push/test", { endpoint: sub!.endpoint });
      toast.success("Notifica di prova inviata");
    });

  const toggleArea = (area: Area, on: boolean) =>
    run(async () => {
      const next = on ? [...areas, area] : areas.filter((a) => a !== area);
      setAreas((await post<{ areas: Area[] }>("/push/subscribe", { ...sub!.toJSON(), areas: next })).areas);
    });

  return (
    <section aria-labelledby="notifiche-title" className="max-w-2xl space-y-5 rounded-xl border bg-card p-6 sm:p-8">
      <div className="space-y-1">
        <h2 id="notifiche-title" className="text-lg font-semibold">Notifiche</h2>
        <p className="text-sm text-muted-foreground">
          Dopo l’aggiornamento delle 9: una notifica per area solo se ci sono novità che contano. Al massimo una ogni 12 ore per area.
        </p>
      </div>

      <div aria-live="polite">
        {state === "loading" && <Line icon={<Loader2 className="animate-spin" />}>Controllo lo stato…</Line>}
        {state === "ios-home" && (
          <Line icon={<Smartphone />}>
            Su iPhone le notifiche funzionano solo con l’app sulla schermata Home: in Safari tocca Condividi → «Aggiungi alla schermata Home», poi apri JobSpy da lì (iOS 16.4 o successivo).
          </Line>
        )}
        {state === "unsupported" && <Line icon={<BellOff />}>Questo browser non supporta le notifiche push.</Line>}
        {state === "no-keys" && <Line icon={<BellOff />}>Notifiche non configurate sul server: mancano le chiavi VAPID.</Line>}
        {state === "denied" && (
          <Line icon={<BellOff />}>
            Permesso negato. Riattivalo dalle impostazioni del dispositivo (su iPhone: Impostazioni → Notifiche → JobSpy), poi ricarica la pagina.
          </Line>
        )}
        {state === "off" && <Line icon={<BellOff />}>Notifiche non attive su questo dispositivo.</Line>}
        {state === "on" && <Line icon={<BellRing className="text-candidati-foreground" />}>Notifiche attive su questo dispositivo.</Line>}
      </div>

      {state === "off" && (
        <Button className="h-11 px-5" onClick={enable} disabled={busy}>
          {busy ? <Loader2 className="animate-spin" /> : <BellRing />}
          Attiva notifiche
        </Button>
      )}

      {state === "on" && (
        <>
          <fieldset className="space-y-1" disabled={busy}>
            <legend className="pb-1 text-sm font-medium">Aree da notificare</legend>
            {AREAS.map((a) => (
              <label key={a.area} className="flex min-h-11 cursor-pointer items-center justify-between gap-4 rounded-md px-1">
                <span className="flex items-center gap-2 text-sm [&_svg]:size-4">
                  <span className={a.accent}>{a.icon}</span>
                  {a.label}
                </span>
                <Switch checked={areas.includes(a.area)} onCheckedChange={(on) => toggleArea(a.area, on)} />
              </label>
            ))}
          </fieldset>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" className="h-11 px-5" onClick={test} disabled={busy}>
              <Send /> Invia prova
            </Button>
            <Button variant="outline" className="h-11 px-5" onClick={disable} disabled={busy}>
              <BellOff /> Disattiva
            </Button>
          </div>
        </>
      )}
    </section>
  );
}

function Line({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <p className="flex items-start gap-2.5 text-sm leading-relaxed [&_svg]:mt-0.5 [&_svg]:size-4 [&_svg]:shrink-0">
      {icon}
      <span>{children}</span>
    </p>
  );
}
