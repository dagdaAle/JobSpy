# Implementation Plan: app iOS nativa (area Lavoro)

**Spec**: [spec.md](spec.md) · **Contratto**: [contract.md](contract.md)

## Approccio

Stesso schema di HNWatch (`~/Progetti/server-apps/hnwatch/ios-native`), già in uso:

- **Backend**: nessun cambio di comportamento. Il gate `_MobileGate` di `webapp/app.py` (PR #26) copre tutte le
  rotte (anche `pa` e `gare`, incluse prima del gate) e non serve mai la SPA. Qui si aggiungono test di bordo,
  `MOBILE_API_KEY` in `.env.example` e la documentazione delle rotte che l'app usa.
- **App**: `ios-native/`, progetto `xcodegen` (`project.yml` versionato, `.xcodeproj` ignorato), Swift 6 con
  isolamento di default `MainActor`, SwiftUI `@Observable`, iOS 18+, solo iPhone, nessuna dipendenza esterna.

## Struttura

| Cartella | Cosa |
|---|---|
| `JobSpy/API` | modelli `Codable` tolleranti, `APIClient` (timeout per chiamata, errori 401/409/502/503), date |
| `JobSpy/Domain` | porting di `decision.tsx`, `JobCard.tsx` (motivo, modalità), `JobDetailSheet.tsx` (5 componenti), `format.ts`, `applications.ts` |
| `JobSpy/App` | entry point, `Store` (stato condiviso, verdetti con Annulla), `Settings` + Keychain |
| `JobSpy/Screens` | Feed, card, dettaglio, CV match e sheet, Preferiti, Candidature, CV, Canali, Cerca, Impostazioni |
| `JobSpy/UI` | `Theme` (colori Asset Catalog), badge, tag, toast, banner, stati vuoti |
| `JobSpyTests` | fixture JSON finte, test di decodifica, dominio, Store con `URLProtocol` |

## Scelte

- **Logica di decisione sul client**, come la web app: il backend restituisce l'analisi grezza e la web app
  calcola decisione e componenti in TypeScript. Il porting Swift è 1:1 e coperto da test con gli stessi casi.
- **Niente `convertFromSnakeCase`**: le mappe sono indicizzate per `job_url`; i modelli usano i nomi del JSON.
- **Chiave nel Keychain** (`kSecClassGenericPassword`, `AfterFirstUnlockThisDeviceOnly`), URL in `UserDefaults`.
- **Font di sistema** (SF, SF Mono per i numeri) in v1 al posto di Outfit/Inter/JetBrains Mono: Dynamic Type
  gratis e nessun file di font da licenziare nel bundle. Da rivedere con le tavole finali.
- **Ricerca** sulle offerte già caricate (titolo, azienda, luogo, tag), niente nuova rotta.
- **Firma**: `Config/Signing.xcconfig` (gitignored) con `DEVELOPMENT_TEAM`, esempio versionato.
- **ATS**: nessuna eccezione; `localhost` è già esente da ATS (backend locale nel simulatore). Release: le Impostazioni accettano solo `https`.

## Verifica

- `cd webapp && python -m unittest discover -s ../tests` verde.
- `xcodegen generate && xcodebuild test` sul simulatore «iPhone 18 Pro».
- Screenshot chiaro e scuro contro un backend locale con DB di prova di dati finti, fuori dalla repo.
