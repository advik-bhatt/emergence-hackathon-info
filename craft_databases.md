# The CRAFT Databases — Plain-English Guide

Nine Snowflake connections are exposed through the CRAFT MCP server. Every one is real, public, enterprise-scale data (the Spider 2.0 benchmark set), not toy tables.

Use the `slug` as the `connection` argument in every CRAFT tool call.

| Slug | Domain | Size |
| --- | --- | --- |
| `thelook-ecommerce-5f7bc95c` | Online clothing retailer | 7 tables |
| `brazilian-e-commerce-5f7bc95c` | Brazilian marketplace (Olist) | 10 tables |
| `ga4-5f7bc95c` | Web analytics for an online store | 100 tables |
| `firebase-5f7bc95c` | Mobile app/game analytics | 123 tables |
| `deps-dev-v1-5f7bc95c` | Open-source packages, dependencies, vulnerabilities | 10 tables |
| `github-repos-5f7bc95c` | GitHub repository metadata and code | 6 tables |
| `crypto-5f7bc95c` | Blockchain transactions across 7 chains | 7 schemas |
| `pancancer-atlas-1-5f7bc95c` | Cancer genomics + patient outcomes | 11 tables |
| `idc-5f7bc95c` | Medical imaging metadata | 19 tables |

---

## 1. `thelook-ecommerce` — a fictional online clothing store

The complete life of an e-commerce business: who the customers are, what's in the catalog, what's in the warehouse, what got ordered, and every click on the site along the way.

**Tables:** `USERS` (customer profiles: age, gender, location, how they found the site), `PRODUCTS` (catalog with cost and retail price — so you can compute margin), `INVENTORY_ITEMS` (individual stocked units, with cost and the date sold), `ORDERS` (one row per purchase, with timestamps for created/shipped/delivered/returned), `ORDER_ITEMS` (one row per item in an order, with sale price), `EVENTS` (raw site behavior — every page view, cart add, session, traffic source, browser, IP), `DISTRIBUTION_CENTERS` (warehouse locations with coordinates).

**Good for:** anything joining behavior to money. Funnels, margin analysis, return rates, personalized recommendations, shipping performance by warehouse. This is the database the reference "Customer Experience Intelligence Agent" used.

**Note:** timestamps are microsecond epoch numbers, not dates.

---

## 2. `brazilian-e-commerce` — the Olist marketplace

Real orders from a Brazilian marketplace where independent sellers list products. The distinguishing feature over `thelook` is that **customers leave 1–5 star reviews with written comments**, and you know exactly when the order was promised versus when it actually arrived.

**Tables:** `OLIST_ORDERS` (with purchase, carrier-handoff, delivery, and *estimated* delivery timestamps), `OLIST_ORDER_ITEMS` (price, freight cost, seller, shipping deadline), `OLIST_ORDER_PAYMENTS` (payment method — including Brazilian *boleto* — and installment count), `OLIST_ORDER_REVIEWS` (score + free-text comment), `OLIST_CUSTOMERS`, `OLIST_SELLERS`, `OLIST_PRODUCTS` (+ a near-duplicate `OLIST_PRODUCTS_DATASET`), `OLIST_GEOLOCATION` (lat/long by postal code), `PRODUCT_CATEGORY_NAME_TRANSLATION` (category names are in Portuguese; this maps them to English).

**Good for:** late-delivery → bad-review causation, seller quality scoring, logistics by region, payment behavior. The reference "Seller Delivery Intelligence Agent" used this.

**Note:** you almost always need the translation table to make output readable.

---

## 3. `ga4` — Google Analytics 4 for an online store

Raw web analytics: every event fired by every visitor to the Google Merchandise Store, roughly November 2020 – January 2021.

**Structure:** one table *per day* (`EVENTS_20201101`, `EVENTS_20201102`, …) — about 100 of them — plus a few pre-built helper tables (`DEC_2020_SESSIONS`, `DEC_ENGAGED_SESSIONS`, `PURCHASED_USERS_NOV`).

**Each row is one event** (`page_view`, `add_to_cart`, `purchase`…) with a user pseudo-ID, session, device, geography, traffic source, and e-commerce details.

**The catch — and the point:** the interesting fields are buried inside nested `event_params` arrays, so answering something as simple as "top pages by engagement time" needs Snowflake `LATERAL FLATTEN`. This is the schema the hackathon brief calls "the hardest SQL pattern in Spider 2.0," and it's exactly where CRAFT is supposed to shine versus pasting a schema into a generic assistant.

**Good for:** funnels, drop-off analysis, mobile-vs-desktop behavior, attribution.

---

## 4. `firebase` — mobile app analytics

The same shape as GA4, but for a **mobile game** rather than a website. Events include things like `ad_reward`, `level_complete`, and `session_start`. Data runs from mid-2018.

**Structure:** one table per day (`EVENTS_20180612`, …) inside a schema named `ANALYTICS_153293282`, ~123 tables, plus pre-aggregated August ranges (`AUG_01_07`, `AUG_16_29`, …). Nested JSON `event_params` and `user_properties`, same as GA4.

**Good for:** player retention, monetization via ads, level progression drop-off, and anything comparing app behavior against web behavior (pair it with `ga4`).

---

## 5. `deps-dev-v1` — the open-source supply chain

Google's deps.dev data: a map of essentially every public software package (npm, Maven, PyPI, Go, Cargo, NuGet), what depends on what, and which ones have known security holes.

**Tables:** `PACKAGEVERSIONS` (every version of every package, with licenses and advisories attached), `ADVISORIES` (security vulnerabilities — CVSS score, severity, description, affected ranges), `DEPENDENCIES` (what a package pulls in, plus `MinimumDepth` = how many hops away), `DEPENDENCYGRAPHEDGES` (the raw graph, edge by edge), `DEPENDENTS` (the reverse direction — who relies on *you*), `PROJECTS` (the GitHub/GitLab repo behind a package: stars, forks, open issues, OSS-Fuzz status), `PACKAGEVERSIONTOPROJECT` (links a package to its repo), `NUGETREQUIREMENTS`, `PACKAGEVERSIONHASHES`, `SNAPSHOTS`.

**Two things make this unusually rich:**
- Several columns are nested JSON (`VARIANT`) — `Licenses`, `Advisories`, `Dependency` — so real `LATERAL FLATTEN` work is required.
- Every row is timestamped with `SnapshotAt` and there's a `SNAPSHOTS` table, meaning **this is a time series of the entire dependency graph**, not a single snapshot. You can watch a vulnerability spread or a fix get adopted.

**Good for:** dependency risk, license compliance, upgrade planning, "what breaks if this package dies."

---

## 6. `github-repos` — GitHub metadata and source code

**Read this before planning around it: it is a *sample*, not all of GitHub.** Four of the six tables are literally prefixed `SAMPLE_`.

**Tables:** `LANGUAGES` (languages per repo), `LICENSES` (license per repo), `SAMPLE_REPOS` (repo name + watcher count), `SAMPLE_COMMITS` (commit messages, authors, diffs), `SAMPLE_FILES` (file paths), `SAMPLE_CONTENTS` (**actual file contents as text**).

**Good for:** analyzing code and commit *text* — what's in files, how people write commit messages, language/license distribution.

**Not good for:** issues, pull requests, or full contributor history — those tables don't exist here. Any "maintainer health / bus factor" idea that assumes complete commit history will hit a wall. Use `deps-dev-v1`'s `PROJECTS` table for repo-level stats instead.

---

## 7. `crypto` — blockchain ledgers

Full transaction history for seven chains, each in its own schema: `CRYPTO_BITCOIN`, `CRYPTO_BITCOIN_CASH`, `CRYPTO_DASH`, `CRYPTO_ETHEREUM`, `CRYPTO_ETHEREUM_CLASSIC`, `CRYPTO_ZILLIQA`, `CRYPTO_BAND`.

**Bitcoin-family schemas** have `BLOCKS`, `TRANSACTIONS`, `INPUTS`, `OUTPUTS` — money in, money out, per transaction.
**Ethereum-family schemas** add `LOGS`, `CONTRACTS`, `TOKEN_TRANSFERS`, `TRACES`, `BALANCES` — so you can follow smart contracts and token movement, not just coin transfers.

**Good for:** following money between wallets, detecting structured/split transfers designed to stay under reporting thresholds, cross-chain tracing, contract activity. This is the "compliance hunt" challenge.

**Note:** these are the biggest tables in the set. Always constrain by block height or time or you'll wait forever.

---

## 8. `pancancer-atlas-1` — cancer genomics

The PanCancer Atlas (TCGA): for thousands of tumor samples across many cancer types, what the genome looks like *and* what happened to the patient.

**Tables:** `CLINICAL_PANCAN_PATIENT_WITH_FOLLOWUP_FILTERED` (demographics, diagnosis, treatment, outcomes, follow-up), `MC3_MAF_V5_ONE_PER_TUMOR_SAMPLE` (mutations), `ALL_CNVR_DATA_BY_GENE_FILTERED` (copy-number changes per gene), gene-expression and DNA-methylation tables, plus focused ones like `BRCA_CDH1_DATA`.

Everything links by `ParticipantBarcode` / `SampleBarcode`.

**Good for:** does mutation X correlate with survival, treatment response, or subtype. **No genomics background required** — the clinical table alone supports real questions.

---

## 9. `idc` — medical imaging metadata (Imaging Data Commons)

Metadata about cancer imaging scans — **not the images themselves.** Which patient, which scan type (CT, MRI, PET), which body part, which study, plus measurements extracted from the scans.

**Tables:** `DICOM_ALL` (the big one — one row per imaging instance, with patient ID and study/series identifiers), many `DICOM_ALL_*_AGGREGATED` slices, `ANALYSIS_RESULTS_METADATA`, `AUXILIARY_METADATA`, `TCGA_CLINICAL_REL9` (clinical data for TCGA patients), `VERSION_METADATA`.

**Good for:** the biotech challenge — because `idc` and `pancancer-atlas-1` **share TCGA patient identifiers**, you can join imaging on one side to molecular subtype on the other. That cross-database join is the whole point of that track, and it's the only challenge that genuinely requires two connections.

---

## Practical notes

- **Nested JSON is everywhere that matters.** `ga4`, `firebase`, and `deps-dev-v1` all hide their best fields inside `VARIANT` columns. Snowflake needs `LATERAL FLATTEN` to read them — this is precisely the SQL that generic LLMs get wrong and CRAFT gets right.
- **Date-partitioned tables.** `ga4` and `firebase` split data into one table per day. Multi-day questions mean unioning across tables.
- **Let CRAFT write the SQL.** The judging criteria explicitly reward using `generate_sql` and the semantic layer over hand-rolled queries. Both reference agents advertise "no hand-written SQL anywhere" as a feature.
