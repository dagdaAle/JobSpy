# ADR 008 — Candidatura assistita, mai autonoma

- Data: 02/11/2026
- Stato: proposta (scelta di Claude; le regole vengono dal bot `jobs`, già in uso)

## Contesto

Ale vuole automatizzare le candidature, che sono complesse: portali diversi (ATS aziendali, Indeed, LinkedIn, inPA con SPID),
CV da adattare, domande ricorrenti. Il bot Hermes `jobs` già precompila nel browser locale con regole dure.

## Decisione

- Il sistema prepara il **kit** (CV adattato, lettera, risposte, checklist); il bot **precompila**; **Ale invia**.
- Livello massimo per portale: ATS aziendali e Indeed precompilazione completa con invio dopo l'ok;
  LinkedIn solo precompilazione, invio a mano; PA solo kit e checklist (SPID e invio di Ale); email solo in bozza.
- Il bot non digita password, 2FA o dati di pagamento, si ferma su CAPTCHA, non inventa dati, non supera ~5 invii all'ora.
- Ogni azione del bot diventa un evento della candidatura in JobSpy, con screenshot finale.

## Perché

- Una candidatura sbagliata o inventata costa più del tempo risparmiato.
- Bot di invio automatico su LinkedIn portano a limitazioni dell'account.

## Conseguenze

- Il bot resta sul Mac (sessioni e browser di Ale); il server non fa login sui portali.
