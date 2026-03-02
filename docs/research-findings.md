# Keyframe Reverse Search — Research Findings

_Date: 2026-03-02_

## TL;DR (recommended stack)

1. **Primary reverse image API**: **Google Cloud Vision Web Detection** (`WEB_DETECTION`) for broad web coverage and structured matches (`pagesWithMatchingImages`, `fullMatchingImages`, `partialMatchingImages`).
2. **Secondary/verification API**: **TinEye API** for independent corroboration and commercial-safe usage.
3. **Yandex coverage**: no clearly documented first-party reverse-image API intended for direct public use in this workflow; practical options are third-party scraping providers (SerpApi/SearchAPI) with higher legal/operational risk.
4. **Earliest publication date**: do **not** trust one signal. Use a **multi-source evidence pipeline** (Wayback CDX earliest capture + page metadata + sitemap/news metadata + independent index evidence), then compute a confidence score.

---

## 1) Reverse image APIs/libraries assessment

## Google Cloud Vision (Web Detection)

**What it gives**
- Web entities/labels
- Full matching images
- Partial matching images
- Pages with matching images
- Visually similar images

This is closest to a production-grade reverse-search API with structured JSON output suitable for ranking and downstream date extraction.

**Strengths**
- Official API, stable auth/billing model (Google Cloud)
- Structured output specifically useful for provenance investigation
- Good global coverage for many mainstream domains

**Weaknesses**
- Paid usage
- Not guaranteed to return earliest source (returns matching/similar evidence, not canonical origin)

**Key source**
- Google Vision Web Detection docs: https://docs.cloud.google.com/vision/docs/detecting-web

---

## TinEye API

**What it gives**
- Commercial reverse image search API access (paid bundles)
- Useful as a second opinion / corroboration source

**Strengths**
- Explicitly commercial API offering
- Often strong for image re-use tracking and duplicate discovery

**Weaknesses**
- Additional cost and integration
- Coverage characteristics differ from Google; may miss results Google sees (and vice versa)

**Key sources**
- TinEye non-commercial vs commercial policy: https://help.tineye.com/article/239-is-tineye-free-to-use
- TinEye API product page: https://services.tineye.com/TinEyeAPI

---

## Yandex reverse image search

**Current practical situation**
- There are third-party APIs (e.g., SerpApi) that expose Yandex reverse-image results by scraping/parsing Yandex image search output.
- This can improve recall in some geographies/content segments.

**Risks**
- Operational fragility (anti-bot changes, markup changes)
- Potential ToS/compliance risk if relying on scraping-based pipelines
- Less predictable long-term stability than first-party APIs

**Key source (third-party wrapper example)**
- SerpApi Yandex Reverse Image endpoint: https://serpapi.com/yandex-reverse-image-api

---

## Recommended search strategy

Use **hybrid retrieval**:
- **Tier 1**: Google Vision Web Detection
- **Tier 2**: TinEye API
- **Tier 3 (optional)**: Yandex via vetted third-party wrapper, feature-flagged by region/risk posture

Then normalize all hits into a single schema:
- `matched_image_url`
- `source_page_url`
- `match_type` (`full`/`partial`/`similar`)
- `provider`
- `provider_score`
- `retrieved_at`

---

## 2) Legal / ToS constraints (important)

## Safe baseline
- Prefer **official commercial APIs** (Google Cloud Vision, TinEye API).
- Avoid direct scraping of consumer search UIs unless legal review explicitly accepts risk.

## Google ToS signal
- Google Terms include restrictions around abusive/automated access and use of automated means contrary to machine-readable instructions.
- This supports using official Google Cloud APIs rather than scraping Google Images.

Source:
- Google Terms of Service: https://policies.google.com/terms?hl=en-US

## TinEye usage split
- TinEye states web usage is free for non-commercial use; commercial use should use TinEye API.

Source:
- https://help.tineye.com/article/239-is-tineye-free-to-use

## Practical compliance checklist
- Keep provider contracts/DPAs on file.
- Respect robots/usage limits and provider attribution requirements.
- Add per-provider kill-switches and circuit breakers.
- Log provenance of every result (provider, endpoint, timestamp, query hash).

> Note: final legal posture should be confirmed by counsel for your jurisdiction/use case.

---

## 3) Most reliable method to derive **earliest publication date**

There is no universally reliable single field. Best results come from **evidence fusion**.

## Evidence sources (ordered by practical reliability)

1. **Earliest web archive capture for candidate page URL**
   - Query Wayback/CDX for earliest timestamp for each candidate URL.
   - Strong independent timestamp evidence, but only from first crawl (not necessarily true first publish).
   - Sources:
     - Wayback APIs: https://archive.org/help/wayback_api.php
     - CDX concepts: https://index.commoncrawl.org (CDX-style index reference)

2. **On-page machine-readable dates**
   - `datePublished`, `dateCreated`, `article:published_time`, JSON-LD fields, `<time datetime>`, RSS/Atom entries.
   - Higher quality on publisher sites; can be missing/incorrect/rewritten.

3. **Sitemap / news sitemap timestamps**
   - Useful corroboration for publishers with disciplined sitemap hygiene.

4. **Image object metadata when available**
   - EXIF dates are weak for web publication (often stripped or altered) but can still support confidence when consistent.

5. **Cross-index first-seen signals**
   - Earliest appearance across independent indexes (e.g., Common Crawl index snapshots) as supporting evidence.

## Recommended algorithm (production)

For each matched page/image candidate:

1. Collect date candidates from:
   - Wayback earliest capture timestamp (`t_wayback_first`)
   - Structured metadata (`t_schema`, `t_og`, `t_html_time`)
   - Sitemap/news feed (`t_sitemap`)
   - Optional index evidence (`t_commoncrawl_first`)

2. Normalize to UTC and store as `date_evidence[]` with:
   - `source`
   - `timestamp`
   - `confidence_weight`
   - `raw_value`

3. Score confidence (example weights):
   - Wayback earliest capture: 0.35
   - JSON-LD/Article metadata: 0.30
   - Sitemap/news sitemap: 0.20
   - HTML heuristics/text parse: 0.10
   - EXIF/other weak signals: 0.05

4. Pick `earliest_supported_date` as the minimum timestamp that has at least **two independent source families** supporting near that date window (e.g., ±72h).

5. Output both:
   - `earliest_possible_date` (minimum observed)
   - `earliest_confident_date` (minimum with corroboration threshold)
   - plus `confidence` (0–1)

This prevents false certainty from a single bad field while still surfacing earliest plausible evidence.

---

## 4) Implementation notes for Keyframe Reverse Search app

- Build a provider abstraction: `search(image) -> normalized_hits[]`
- Keep provider adapters isolated (Google, TinEye, optional Yandex-wrapper).
- Add retry/backoff and response caching by image hash.
- Compute image fingerprints (pHash/dHash) to dedupe near-identical frames before paid API calls.
- Persist an evidence graph per candidate result:
  - `candidate_url`
  - `first_seen_claims[]`
  - `supporting_sources[]`
  - `final_date_decision`

---

## 5) Final recommendation

For launch reliability and compliance:
- **Ship with Google Vision + TinEye first.**
- Implement **evidence-fusion date inference** (Wayback + page metadata + sitemap) as core logic.
- Keep Yandex via third-party wrappers as **optional/experimental**, behind config + legal review.

This gives the best balance of coverage, legal defensibility, and reproducible date provenance.
