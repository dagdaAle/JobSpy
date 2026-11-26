# JobSpy iOS (SwiftUI)

App nativa di JobSpy, v1 solo area Lavoro ([spec 005](../specs/005-ios-app/spec.md), design Penpot I1–I6).
Parla con l'API mobile del backend: `<URL>/mobile/<rotta>` con header `X-Api-Key` ([docs/mobile-api.md](../docs/mobile-api.md)).

Swift 6 (concorrenza stretta, isolamento di default `MainActor`), SwiftUI, iOS 18+, solo iPhone, nessuna dipendenza.

## Struttura

- `JobSpy/API` — modelli Codable tolleranti (numeri e booleani anche come stringa), client con timeout e errori
- `JobSpy/Domain` — porting di `decision.tsx`, `JobCard.tsx`, `JobDetailSheet.tsx`, `format.ts`, `applications.ts`
- `JobSpy/App` — entry point (Feed, Preferiti, Candidature, CV, Cerca), `Store`, `Settings` (Keychain)
- `JobSpy/Screens` — feed e card, dettaglio con «Valutazione | CV per questa offerta», CV match e sheet, altre viste
- `JobSpy/UI` — token Penpot (Asset Catalog con variante scura), badge, tag, barre, anello, toast, banner
- `JobSpyTests` — fixture finte, decodifica, dominio, Store e CV match con `URLProtocol`
- `Tools/fake_backend.py` — backend locale con DB usa e getta di dati finti (anche il CV match, senza DeepSeek)

## Configurazione

```bash
brew install xcodegen
cd ios-native
cp Config/Signing.example.xcconfig Config/Signing.xcconfig   # gitignored: DEVELOPMENT_TEAM
cp Config/Secrets.example.xcconfig Config/Secrets.xcconfig   # facoltativo, solo Debug: precompila URL e chiave
xcodegen generate
```

URL e chiave si inseriscono nell'app (menu Lavoro → Impostazioni); la chiave va nel Portachiavi.
La Release non incorpora mai URL o chiave e accetta solo `https`. Sul server: `MOBILE_API_KEY` impostata e
Authentik che esclude `^/mobile/`.

## Simulatore contro il backend finto

```bash
cd webapp && FEEDBACK_DB=/tmp/jobspy-ios.db MOBILE_API_KEY=devkey python ../ios-native/Tools/fake_backend.py
cd ios-native && xcodebuild -scheme JobSpy -destination 'platform=iOS Simulator,name=iPhone 18 Pro' -derivedDataPath build-local build
xcrun simctl install booted build-local/Build/Products/Debug-iphonesimulator/JobSpy.app
xcrun simctl launch booted dev.intecha.jobspy
```

Argomenti di lancio per gli screenshot: `-uiTab 0…4`, `-uiJob <job_url>` (con `-uiTab 0`),
`-uiDetailTab cv`, `-uiSheet keywords|patches`, `-uiSaved 0|1|2`, `-uiScreen channels|settings`, `-uiSearch <testo>`.

## Test

```bash
xcodebuild -scheme JobSpy -destination 'platform=iOS Simulator,name=iPhone 18 Pro' test
```

## Scelte

- **Decisione e componenti sul client**, come la web app: porting 1:1 con gli stessi casi nei test.
- **Niente `convertFromSnakeCase`**: le mappe `analysis` / `feedback` / `applications` sono indicizzate per `job_url`.
- **Font di sistema** (SF e SF Mono per i numeri) al posto di Outfit/Inter/JetBrains Mono: Dynamic Type senza
  file di font nel bundle. Da rivedere con le tavole definitive.
- **Canali e CV in sola lettura**: creare o modificare canali e CV resta nella web app (v2).

## Installazione sul telefono

Con `Config/Signing.xcconfig` a posto: iPhone collegato, Modalità sviluppatore attiva, Run da Xcode oppure
`xcrun devicectl device install app`. Con l'account gratuito la firma dura 7 giorni.
