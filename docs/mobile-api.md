# API mobile (app iOS)

Ogni rotta dell'API è raggiungibile anche come `/mobile/<rotta>`, con lo stesso comportamento e le
stesse risposte JSON. Esempio: `GET /mobile/pa/items` = `GET /pa/items`. Stesso schema di HNWatch.

## Autenticazione

- Header `X-Api-Key: <MOBILE_API_KEY>` su ogni richiesta. Chiave: `openssl rand -hex 32`, solo nelle
  variabili d'ambiente dell'app su Coolify.
- In Authentik il provider di jobspy deve escludere `^/mobile/`: lì il controllo lo fa il backend,
  non il login web. Il resto del dominio resta dietro Authentik.
- Errori: `503 {"detail": "accesso mobile non configurato"}` se `MOBILE_API_KEY` non è impostata;
  `401 {"detail": "chiave API non valida"}` se la chiave manca o è sbagliata; `404` JSON per un path
  che non è una rotta (la SPA non è servita sotto `/mobile/`).

## Contratto

`GET /mobile/openapi.json` restituisce lo schema OpenAPI di tutte le rotte, da usare per generare il
client Swift (`swift-openapi-generator`).
