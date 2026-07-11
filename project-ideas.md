# Project Ideas — Emergence × Nebius (CRAFT)

Ideas built on the CRAFT datasets, deliberately **avoiding the ecommerce and biotech
datasets** — the two everyone else will pile onto. Every claim below was verified by
querying the data through the CRAFT MCP, not read off the docs.

Judging rubric this is written against:
**CRAFT usage depth 30% · Insight quality 30% · Agent architecture 20% · Story clarity 20%**

---

## Dataset selection: why `deps-dev-v1`

Three realistic non-ecommerce/non-biotech options, and why the other two lose:

- **`crypto`** — viable (Ethereum: 18.5M token transfers, 2016-04 → 2024-07), but it's a
  *named challenge*, so it is not actually uncontested. Worse: fraud/structuring findings
  have **no ground truth**. The demo reduces to "these wallets look suspicious, trust me,"
  which judges cannot verify. Scores badly on *Insight quality*.
- **`ga4` / `firebase`** — the hardest SQL in the set (nested `LATERAL FLATTEN`), which
  flatters *CRAFT usage depth*, but the deliverable is a funnel dashboard. Weak story.
- **`deps-dev-v1`** — ✅ **winner.**

The reason is one column nothing else has: **`DEPENDENTS.MinimumDepth`**. The transitive
dependency graph is *precomputed*. Blast radius — the thing real security tooling
struggles to compute — becomes a join instead of a graph traversal. Verified scale:

| Ecosystem | Dependent edges | Distinct packages | Distinct dependents | Max depth |
| --- | --- | --- | --- | --- |
| NPM | ~535,000 | 32,675 | 155,336 | **117** |

MAVEN, GO, PYPI, CARGO follow.

---

## 💡 Idea 1 (recommended): **Blast Radius** — a dependency upgrade-triage agent

### The insight nobody else will have

Every SBOM scanner on earth tells you *"you have 47 vulnerabilities."*
**None of them tell you "those 47 collapse into 3 upgrades."**

That is a **minimum set-cover problem over the dependency graph**, and `deps-dev-v1` is
the only dataset here that can express it. That single reframing is the whole pitch:
we don't rank vulnerabilities, we rank *actions*.

### What it does

1. User pastes a `package.json` (or picks a real repo — see validation corpus below).
2. Agent resolves the transitive dependency tree via `DEPENDENCIES` / `DEPENDENTS`.
3. Joins to `ADVISORIES` to find CVEs affecting resolved versions.
4. Scores each vuln by **reach** (how many of *your* packages it sits under) and
   **depth** (`MinimumDepth` — a CVE 6 hops down behind a dev-only path is not your
   Tuesday problem; one at depth 1 is).
5. **Solves for the smallest set of upgrades that removes the most risk** — and prints
   it as an ordered action list, not a vulnerability table.

### Verified supporting data

The core join works. NPM packages with a CRITICAL advisory (CVSS ≥ 9.0), ranked by
distinct downstream dependents:

| Package | Advisory | CVSS | Disclosed | Downstream dependents |
| --- | --- | --- | --- | --- |
| lodash | Prototype Pollution | 9.1 | 2019-07-10 | **1,254** |
| minimist | Prototype Pollution | 9.8 | 2022-03-18 | 871 |
| https-proxy-agent | Denial of Service | 9.1 | 2018-07-27 | 358 |
| loader-utils | Prototype pollution | 9.8 | 2022-10-13 | 314 |
| json-schema | Prototype Pollution | 9.8 | 2021-11-19 | 304 |
| uglify-js | Incorrect Handling of Non-Boolean Comparisons | 9.8 | 2017-10-24 | 229 |

### The line that wins the room: **load-bearing but abandoned**

Fold in a second risk signal — packages a huge chunk of the ecosystem depends on, whose
last release is ancient. Verified:

- **`once`** — **941** packages depend on it. Last published **September 2016**.
- **`isarray`** — **1,239** dependents. Last published July 2019.
- **`lodash`** — **1,254** dependents, *and* an unfixed-in-the-wild critical CVE from 2019.

> *"941 packages depend on code nobody has touched since 2016."*

That is the demo line judges repeat to each other afterwards. It is also a genuinely
novel metric — a "left-pad risk" score — not a restatement of what Dependabot says.

### The cross-connection flex

`github-repos.SAMPLE_CONTENTS` contains **real manifest files**:

| Manifest | Rows | Distinct repos |
| --- | --- | --- |
| `package.json` | 80 | 76 |
| `pom.xml` | 45 | 44 |
| `requirements.txt` | 4 | 4 |
| `Cargo.toml` | 3 | 3 |
| `go.mod` | 0 | 0 |

Too thin to be a product, **perfect as a validation slide**: *"we ran this against 76 real
GitHub repos — here's the leaderboard of most-exposed projects."* It's a genuine
**two-connection join** (`github-repos` → `deps-dev-v1`), the same structural difficulty
as the biotech track's TCGA join, on a dataset nobody is fighting over.

### Why it scores on the rubric

- **CRAFT usage depth (30%)** — `LATERAL FLATTEN` over the `Packages`, `Advisories`,
  `Licenses`, and `Dependent` VARIANT columns; a two-connection join; all SQL via
  `generate_sql` (no hand-written SQL anywhere).
- **Insight quality (30%)** — set-cover over upgrades + the abandonment score are real,
  verifiable, non-obvious findings.
- **Agent architecture (20%)** — natural multi-tool loop: resolve tree → find CVEs →
  score reach/depth → optimize upgrade set → explain.
- **Story clarity (20%)** — "47 vulns → 3 upgrades" and "941 packages, untouched since
  2016." Both land in one sentence.

### Demo

Force-directed graph of the dependency tree, vulnerable nodes glowing red. Agent
recommends 3 upgrades. Apply them → **the red collapses.** Visual, instant, legible from
the back of a room.

---

## 💡 Idea 2: Ecosystem Fragility Index

Score the "left-pad risk" of an entire ecosystem: high dependent count × dead project
(`PROJECTS` stars / open issues) × stale `UpstreamPublishedAt`. Output is a ranked list of
open source's single points of failure.

Genuinely novel and arguably publishable — **but it is an *analysis*, not an agent.** It
demos as a chart. Weak fit for an agent hackathon (kills the 20% architecture score).

**Better used as a feature inside Idea 1**, which is exactly where it's most actionable
anyway.

## 💡 Idea 3: Crypto circular-flow detection

Recursive CTE over 18.5M Ethereum token transfers to surface A→B→C→A wash-trading loops.
Visually stunning graph.

**Risks:** it's a named challenge (crowded), and there's no ground truth to prove the
loops are actually wash trading. Insight quality is unverifiable.

---

## Landmines (verified the hard way)

- **`deps-dev-v1` is NOT a time series of the dependency graph.** `ADVISORIES` and
  `DEPENDENTS` have exactly **one snapshot each**. Only `PACKAGEVERSIONS` (44 snapshots)
  and `DEPENDENCIES` (19) have history. Any plan that assumes you can "watch a vuln
  spread over time" via snapshots will die on contact.
- **The real time signal is event timestamps, and it's better anyway:**
  `ADVISORIES.Disclosed` and `PACKAGEVERSIONS.UpstreamPublishedAt` are true event times.
  That's how you say *"this CVE has been public for 2,100 days and N packages still
  depend on a vulnerable version"* — no snapshot history required.
- **`sample_data` takes a 3-part name** (`DB.SCHEMA.TABLE`), not the 4-part FQN the tool
  docs advertise. It will 400 on you otherwise.
- **All timestamps are microsecond epoch integers.** Divide by 1,000,000 before
  `TO_TIMESTAMP`.
- **`github-repos` is a sample, not all of GitHub.** No issues/PRs tables. Don't plan
  around contributor history.
