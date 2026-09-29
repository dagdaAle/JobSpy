<img src="https://github.com/cullenwatson/JobSpy/assets/78247585/ae185b7e-e444-4712-8bb9-fa97f53e896b" width="400">

**JobSpy** is a job scraping library with the goal of aggregating all the jobs from popular job boards with one tool.

## Features

- Scrapes job postings from **LinkedIn**, **Indeed**, **Glassdoor**, **Google**, **ZipRecruiter**, & other job boards concurrently
- Remote-only boards: **Remotive**, **RemoteOK**, **WeWorkRemotely**, **Working Nomads**
- Aggregates the job postings in a dataframe
- Proxies support to bypass blocking
- Italian-market helpers (`search_italy`, `search_remote`) that fix km/miles and language mismatches

![jobspy](https://github.com/cullenwatson/JobSpy/assets/78247585/ec7ef355-05f6-4fd3-8161-a817e31c5c57)

### Installation

```
pip install -U python-jobspy
```

_Python version >= [3.10](https://www.python.org/downloads/release/python-3100/) required_

### Usage

```python
import csv
from jobspy import scrape_jobs

jobs = scrape_jobs(
    site_name=["indeed", "linkedin", "zip_recruiter", "google"], # "glassdoor", "bayt", "naukri", "bdjobs"
    search_term="software engineer",
    google_search_term="software engineer jobs near San Francisco, CA since yesterday",
    location="San Francisco, CA",
    results_wanted=20,
    hours_old=72,
    country_indeed='USA',
    
    # linkedin_fetch_description=True # gets more info such as description, direct job url (slower)
    # proxies=["208.195.175.46:65095", "208.195.175.45:65095", "localhost"],
)
print(f"Found {len(jobs)} jobs")
print(jobs.head())
jobs.to_csv("jobs.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False) # to_excel
```

### Remote-only boards

Four boards that only list remote jobs are supported. They ignore `location` /
`distance` (every result is remote) and are searched client-side by keyword:

```python
from jobspy import scrape_jobs

jobs = scrape_jobs(
    site_name=["remotive", "remoteok", "weworkremotely", "workingnomads"],
    search_term="python",
    results_wanted=20,
    is_remote=True,
)
```

- **Remotive** – public JSON API, server-side keyword filter.
- **RemoteOK** – public JSON API, client-side keyword filter.
- **WeWorkRemotely** – per-category RSS feeds (programming, full-stack, back-end, front-end, devops, design, product).
- **Working Nomads** – public JSON API; the `location` field carries the time zone (e.g. `Time zone: CET`), handy for filtering European roles.

### Italian market / remote presets

`jobspy.presets` provides two thin wrappers around `scrape_jobs()` that fix the
ergonomics that make Italian searches under-perform (distance is in **miles**,
Italian Indeed/Glassdoor index Italian-language postings, and `country_indeed`
must be `"Italy"`):

```python
from jobspy.presets import search_italy, search_remote

# Jobs near Verona — think in KILOMETERS (converted to miles internally),
# sets country_indeed="Italy" and includes LinkedIn by default.
df = search_italy("sviluppatore", "Verona, Veneto", distance_km=25)

# Remote-only jobs across all four remote boards.
df = search_remote("python")
```

Tips for Italian searches: prefer Italian search terms (`"sviluppatore"` matches
far more than `"developer"` on `it.indeed.com`), qualify the location with its
region (`"Verona, Veneto"`), and keep the radius tight — the default 50 miles is
~80 km.

### Output

```
SITE           TITLE                             COMPANY           CITY          STATE  JOB_TYPE  INTERVAL  MIN_AMOUNT  MAX_AMOUNT  JOB_URL                                            DESCRIPTION
indeed         Software Engineer                 AMERICAN SYSTEMS  Arlington     VA     None      yearly    200000      150000      https://www.indeed.com/viewjob?jk=5e409e577046...  THIS POSITION COMES WITH A 10K SIGNING BONUS!...
indeed         Senior Software Engineer          TherapyNotes.com  Philadelphia  PA     fulltime  yearly    135000      110000      https://www.indeed.com/viewjob?jk=da39574a40cb...  About Us TherapyNotes is the national leader i...
linkedin       Software Engineer - Early Career  Lockheed Martin   Sunnyvale     CA     fulltime  yearly    None        None        https://www.linkedin.com/jobs/view/3693012711      Description:By bringing together people that u...
linkedin       Full-Stack Software Engineer      Rain              New York      NY     fulltime  yearly    None        None        https://www.linkedin.com/jobs/view/3696158877      Rain’s mission is to create the fastest and ea...
zip_recruiter Software Engineer - New Grad       ZipRecruiter      Santa Monica  CA     fulltime  yearly    130000      150000      https://www.ziprecruiter.com/jobs/ziprecruiter...  We offer a hybrid work environment. Most US-ba...
zip_recruiter Software Developer                 TEKsystems        Phoenix       AZ     fulltime  hourly    65          75          https://www.ziprecruiter.com/jobs/teksystems-0...  Top Skills' Details• 6 years of Java developme...

```

### Parameters for `scrape_jobs()`

```plaintext
Optional
├── site_name (list|str):
|    linkedin, zip_recruiter, indeed, glassdoor, google, bayt, bdjobs, naukri,
|    remotive, remoteok, weworkremotely, workingnomads
|    (default is all)
│
├── search_term (str)
|
├── google_search_term (str)
|     search term for google jobs. This is the only param for filtering google jobs.
│
├── location (str)
│
├── distance (int): 
|    in miles, default 50
│
├── job_type (str): 
|    fulltime, parttime, internship, contract
│
├── proxies (list): 
|    in format ['user:pass@host:port', 'localhost']
|    each job board scraper will round robin through the proxies
|
├── is_remote (bool)
│
├── results_wanted (int): 
|    number of job results to retrieve for each site specified in 'site_name'
│
├── easy_apply (bool): 
|    filters for jobs that are hosted on the job board site (LinkedIn easy apply filter no longer works)
|
├── user_agent (str): 
|    override the default user agent which may be outdated
│
├── description_format (str): 
|    markdown, html (Format type of the job descriptions. Default is markdown.)
│
├── offset (int): 
|    starts the search from an offset (e.g. 25 will start the search from the 25th result)
│
├── hours_old (int): 
|    filters jobs by the number of hours since the job was posted 
|    (ZipRecruiter and Glassdoor round up to next day.)
│
├── verbose (int) {0, 1, 2}: 
|    Controls the verbosity of the runtime printouts 
|    (0 prints only errors, 1 is errors+warnings, 2 is all logs. Default is 2.)

├── linkedin_fetch_description (bool): 
|    fetches full description and direct job url for LinkedIn (Increases requests by O(n))
│
├── linkedin_company_ids (list[int]): 
|    searches for linkedin jobs with specific company ids
|
├── country_indeed (str): 
|    filters the country on Indeed & Glassdoor (see below for correct spelling)
|
├── enforce_annual_salary (bool): 
|    converts wages to annual salary
|
├── ca_cert (str)
|    path to CA Certificate file for proxies
```

```
├── Indeed limitations:
|    Only one from this list can be used in a search:
|    - hours_old
|    - job_type & is_remote
|    - easy_apply
│
└── LinkedIn limitations:
|    Only one from this list can be used in a search:
|    - hours_old
|    - easy_apply
```

## Supported Countries for Job Searching

### **LinkedIn**

LinkedIn searches globally & uses only the `location` parameter. 

### **ZipRecruiter**

ZipRecruiter searches for jobs in **US/Canada** & uses only the `location` parameter.

### **Indeed / Glassdoor**

Indeed & Glassdoor supports most countries, but the `country_indeed` parameter is required. Additionally, use the `location`
parameter to narrow down the location, e.g. city & state if necessary. 

You can specify the following countries when searching on Indeed (use the exact name, * indicates support for Glassdoor):

|                      |              |            |                |
|----------------------|--------------|------------|----------------|
| Argentina            | Australia*   | Austria*   | Bahrain        |
| Belgium*             | Brazil*      | Canada*    | Chile          |
| China                | Colombia     | Costa Rica | Czech Republic |
| Denmark              | Ecuador      | Egypt      | Finland        |
| France*              | Germany*     | Greece     | Hong Kong*     |
| Hungary              | India*       | Indonesia  | Ireland*       |
| Israel               | Italy*       | Japan      | Kuwait         |
| Luxembourg           | Malaysia     | Mexico*    | Morocco        |
| Netherlands*         | New Zealand* | Nigeria    | Norway         |
| Oman                 | Pakistan     | Panama     | Peru           |
| Philippines          | Poland       | Portugal   | Qatar          |
| Romania              | Saudi Arabia | Singapore* | South Africa   |
| South Korea          | Spain*       | Sweden     | Switzerland*   |
| Taiwan               | Thailand     | Turkey     | Ukraine        |
| United Arab Emirates | UK*          | USA*       | Uruguay        |
| Venezuela            | Vietnam*     |            |                |

### **Bayt**

Bayt only uses the search_term parameter currently and searches internationally



## Notes
* Indeed is the best scraper currently with no rate limiting.  
* All the job board endpoints are capped at around 1000 jobs on a given search.  
* LinkedIn is the most restrictive and usually rate limits around the 10th page with one ip. Proxies are a must basically.

## Frequently Asked Questions

---
**Q: Why is Indeed giving unrelated roles?**  
**A:** Indeed searches the description too.

- use - to remove words
- "" for exact match

Example of a good Indeed query

```py
search_term='"engineering intern" software summer (java OR python OR c++) 2025 -tax -marketing'
```

This searches the description/title and must include software, summer, 2025, one of the languages, engineering intern exactly, no tax, no marketing.

---

**Q: No results when using "google"?**  
**A:** You have to use super specific syntax. Search for google jobs on your browser and then whatever pops up in the google jobs search box after applying some filters is what you need to copy & paste into the google_search_term. 

---

**Q: Received a response code 429?**  
**A:** This indicates that you have been blocked by the job board site for sending too many requests. All of the job board sites are aggressive with blocking. We recommend:

- Wait some time between scrapes (site-dependent).
- Try using the proxies param to change your IP address.

---

### JobPost Schema

```plaintext
JobPost
├── title
├── company
├── company_url
├── job_url
├── location
│   ├── country
│   ├── city
│   ├── state
├── is_remote
├── description
├── job_type: fulltime, parttime, internship, contract
├── job_function
│   ├── interval: yearly, monthly, weekly, daily, hourly
│   ├── min_amount
│   ├── max_amount
│   ├── currency
│   └── salary_source: direct_data, description (parsed from posting)
├── date_posted
└── emails

Linkedin specific
└── job_level

Linkedin & Indeed specific
└── company_industry

Indeed specific
├── company_country
├── company_addresses
├── company_employees_label
├── company_revenue_label
├── company_description
└── company_logo

Naukri specific
├── skills
├── experience_range
├── company_rating
├── company_reviews_count
├── vacancy_count
└── work_from_home_type
```


## Workflow personale: Verona e remoto dall’Italia

La webapp considera due alternative: presenza/ibrido vicino a Verona e remoto
accessibile dall’Italia. I nuovi canali locali propongono `Verona, Veneto` e
50 km (modificabili); `Solo remoto` rimane disattivato. I canali esistenti non
vengono riscritti. Il raggio dipende dai filtri supportati dalla singola fonte;
la valutazione AI non inventa distanze o tempi di percorrenza.

L’analisi distingue compatibilità geografica, modalità, attendibilità e requisiti
da verificare. Una sede mancante o un fuso orario non provano che sia possibile
lavorare dall’Italia. CV o descrizione insufficienti producono un match non
calcolabile, non un punteggio basso. L’area ammessa rimane visibile nelle schede.

- Le copie vengono raggruppate solo con titolo, azienda, sede, modalità,
  contratto e descrizione sufficientemente completa coincidenti. I giudizi già
  salvati restano conservati; si possono correggere dalla vista Scartate.
- Nuove mostra gli annunci scoperti nell’ultimo aggiornamento completato di
  ciascun canale, anche quando il successivo aggiornamento trova zero risultati.
- Le quattro fonti remote applicano la finestra temporale prima del limite dei
  risultati. Le date disponibili hanno precisione giornaliera: il giorno limite
  viene incluso; gli annunci senza data restano visibili.
- Archivio consente di recuperare le offerte nascoste automaticamente. Il
  ripristino concede una nuova finestra di revisione senza alterare il primo
  avvistamento storico.
- Candidature registra stato, data invio, note, prossimo passo e relativa data.
  Le candidature salvate non vengono archiviate automaticamente. Il pulsante
  Candidati apre solo l’annuncio: l’invio e lo stato si registrano manualmente.
- Cambiando CV, modello o versione del prompt le analisi precedenti restano nello
  storico, ma vengono ricalcolate e non sono mostrate come attuali. Il PDF montato
  viene riletto al riavvio. Il primo avvio di questa versione aggiorna anche le
  analisi precedenti secondo i nuovi criteri Verona/remoto Italia.

### Aggiornamento e verifiche

Il Dockerfile compila React in uno stage Node e copia il bundle nella webapp:
non occorre più compilare e committare manualmente `webapp/static` prima del build.
La migrazione SQLite è automatica e conserva i dati; prima dell’aggiornamento
crea un backup `pre-workflow-v2-*` nel volume. I backup sullo stesso volume non
sostituiscono una copia esterna per il recupero da perdita del disco.

Test offline, con database temporanei e fonti simulate (nessuna chiamata AI):

```sh
python tests/test_workflow.py
cd webapp/frontend
npm ci
npm run build
```

Il backend rimane monoutente: sul server usare il proxy autenticato esistente
(es. Authentik) ed evitare accesso pubblico diretto alla porta del backend.
Questa modifica non configura né verifica l’autenticazione del deployment.


### Registro candidature e cronologia

La pagina Candidature ha ricerca per ruolo/azienda/contatto, filtri di stato e
scadenza, contatori e ordinamento per prossima azione. “Da seguire oggi” include
le scadenze passate e odierne delle candidature non rifiutate/ritirate. Sono
promemoria visibili nell’app, non notifiche automatiche.

“Inserisci candidatura” registra offerte esterne anche senza link. I record
manuali senza URL ricevono un identificatore interno e non hanno un pulsante
per aprire l’annuncio. I record manuali non attivano analisi AI. Inserire un link
già seguito restituisce un conflitto senza sovrascrivere la candidatura.

Il dettaglio conserva nome/versione del CV, contatto, data invio, note e prossimo
passo. “Candidatura inviata oggi” registra esplicitamente l’invio; aprire il link
non cambia lo stato. È disponibile lo stato “Primo contatto”. Ogni modifica
significativa registra i valori precedenti e nuovi nella cronologia; salvataggi
identici non producono eventi. Si possono aggiungere aggiornamenti con data.

Le candidature preesistenti vengono importate nella cronologia una sola volta;
la migrazione crea prima un backup `pre-application-history-*`. Nessuna email
viene letta/inviata e nessun portale viene sincronizzato da questa funzione.
