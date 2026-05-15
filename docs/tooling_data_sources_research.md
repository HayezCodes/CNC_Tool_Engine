# Tooling Data Sources Research

**Purpose:** Identify official, machine-readable tooling data sources for large-scale
import into the Enterprise Tooling Search system.

**Scope:** Research only. No data has been scraped or imported as part of this document.

**Date:** 2026-05-15

---

## Background: ISO 13399 and Industry Data Formats

ISO 13399 ("Cutting Tool Data Representation and Exchange") is the governing
international standard for vendor-neutral cutting tool parameter exchange. It does not
specify a single file format; the standard maps onto several physical encodings:

| Format | Standard | Description |
|--------|----------|-------------|
| `.p21` / `.stp` | ISO 10303-21 (STEP) | Canonical ISO 13399 container — parametric property values in EXPRESS-schema text |
| XML property sets | ISO/TS 13399-72 | XML-based property-set documents; used alongside STEP |
| DXF | ISO/TS 13399-70 | 2D tool drawings |
| GTC (Generic Tool Catalog) | Co-developed by Sandvik, Kennametal, Iscar, Siemens | XML+ZIP catalog hierarchy layered on ISO 13399; vendor-neutral; used by NX, Teamcenter, CoroPlus |
| DIN 4000 / DIN 4003 | German national standards | DIN 4000 = parametric data (maps alongside ISO 13399); DIN 4003 = 3D geometry |

**Critical note for this project:** No manufacturer offers a public, unauthenticated
REST or JSON API. All access is via web applications requiring login or packaged bulk
downloads. JSON is not a standard delivery format for ISO 13399 data. Any import
into the tooling search schema requires a parsing step from GTC/P21/XML → our JSON schema,
followed by manual field verification.

---

## Industry Aggregator Platforms

Two major third-party platforms aggregate and distribute manufacturer data. Understanding
these is essential before approaching individual manufacturers.

### MachiningCloud (machining.cloud)

An independent cloud platform hosting ISO 13399 / GTC / STEP data from 60+ manufacturers.
Delivers tool data to CAM, simulation, and TMS software via web app and integrations.
Follows an "ISO Plus" strategy that extends beyond ISO 13399 to include feeds/speeds and
MTConnect process data.

- **URL:** `https://machining.cloud` (app) / `https://machiningcloud.com` (marketing)
- **Formats:** ISO 13399 / GTC (XML+ZIP), STEP, STL, GTC Light (for Mastercam)
- **API:** No public developer API documented as of this research
- **Login required:** Yes — free account required; broader access appears subscription-based
- **Licensing:** Data IP remains with manufacturers; MachiningCloud acts as licensed distributor
- **Participating manufacturers (from the 8 researched):** Sandvik Coromant, Seco Tools, Walter, Iscar, Mitsubishi Materials, Guhring, Dormer Pramet (7 of 8 — Kennametal is **not** currently a partner due to active litigation; see Kennametal section)

### ToolsUnited (toolsunited.com)

European-origin platform operated by CIMSOURCE GmbH. Claims 1 million+ tool components
from 50+ brands. Provides DIN 4000 / ISO 13399 / GTC data with 20+ CAM/TMS export
interfaces. More cost-transparent than MachiningCloud with published pricing.

- **URL:** `https://info.toolsunited.com`
- **Formats:** DIN 4000 / ISO 13399 / GTC, DXF, STEP (DIN 4003), Excel, 20+ CAM/TMS interfaces
- **API:** "ToolsUnitedDirect" web service for CAM/TMS integration; no public REST API
- **Login required:** Searching free without login; downloading requires registration + paid subscription
- **Pricing:** ~$1,200/year (up to 15 machines) → ~$4,200/year (single site); 3D models add $3,570–$10,680/year + $990 setup; pay-per-use also available
- **Licensing:** Data IP with manufacturers; ToolsUnited licenses "StOB" harmonized schema; no commercial redistribution implied
- **Participating manufacturers (from the 8 researched):** Sandvik Coromant, Kennametal, Seco Tools, Walter, Iscar, Mitsubishi Materials, Guhring (7 confirmed; Dormer Pramet unconfirmed)

---

## Manufacturer Data Sources

---

### 1. Sandvik Coromant

| Field | Detail |
|-------|--------|
| **Official source URL** | `https://www.sandvik.coromant.com/en-us/downloads/tool-data/pages/default.aspx` |
| **Developer portal** | `https://developers.sandvik.coromant.com/` |
| **Available formats** | GTC (XML+ZIP), ISO 13399 / P21, STEP, DXF, PDF catalogs |
| **Login required** | Yes — free registration; CoroPlus Tool Library is subscription SaaS |
| **ISO 13399 supported** | Yes — Sandvik co-developed the GTC format built on ISO 13399 |
| **Tooling-library export** | Yes — CoroPlus Tool Library exports ISO 13399, GTC, and STEP |
| **API exists** | Yes — developer portal exists (Azure API Management); registration required for API key; not fully public |
| **MachiningCloud** | Yes — confirmed partner (January 2026); catalog live on platform |
| **ToolsUnited** | Yes — confirmed |

**Recommended ingestion strategy:**

1. Register at `developers.sandvik.coromant.com` and request API access — if granted, this
   is the cleanest programmatic path.
2. Alternatively, download the full GTC catalog (~8 GB) from the tool-data downloads page;
   parse the XML manifest to extract series, designation, grade, and geometry properties
   for turning inserts, milling inserts, and endmill families.
3. Map extracted fields to our schema; manually verify a sample against the PDF catalog
   before bulk import.
4. As a faster path: use MachiningCloud to browse and export per-brand or per-category GTC
   packages, which are smaller and better curated than the full bulk download.

**Estimated ingestion difficulty:** Medium

**Notes:** The full bulk catalog is ~8 GB and covers every Sandvik Coromant product. GTC
parsing requires an XML library and knowledge of the GTC schema (documented by Siemens/
Sandvik). The developer API is the ideal path if API access is approved — it allows
structured queries rather than bulk parsing. Data described as "free of charge" after
registration; no commercial redistribution terms visible publicly.

---

### 2. Kennametal

| Field | Detail |
|-------|--------|
| **Official source URL** | `https://www.kennametal.com/us/en/my-account/collaboration-space.html` |
| **CAM integrations page** | `https://www.kennametal.com/us/en/resources/software.html` |
| **Available formats** | ISO 13399, GTC, STEP (confirmed for former NOVO platform); current Collaboration Space offers "downloadable CAD files" — specific bulk-export formats not publicly detailed |
| **Login required** | Yes — Kennametal account required for Collaboration Space |
| **ISO 13399 supported** | Yes — Kennametal was an original GTC co-developer |
| **Tooling-library export** | Partial — per-product CAD downloads available; bulk export workflow unclear after NOVO discontinuation |
| **API exists** | No public API identified |
| **MachiningCloud** | **No** — Kennametal is NOT currently a MachiningCloud partner. Their NOVO platform (built on MachiningCloud infrastructure) was discontinued May 25, 2025. MachiningCloud filed litigation against Kennametal in February 2025 alleging theft of trade secrets and breach of contract ($1B+ claim); case ongoing as of this research. |
| **ToolsUnited** | Yes — confirmed |

**Recommended ingestion strategy:**

1. Use ToolsUnited as the primary path for Kennametal structured data (DIN 4000 /
   ISO 13399 export); requires a paid subscription.
2. For family-level seed records without a subscription: manually extract product family
   information from the Kennametal product catalog PDFs, and verify against the
   Collaboration Space per-product pages for ISO designation and material group data.
3. Do not attempt to parse legacy NOVO exports — the platform is discontinued and
   any legacy files would be stale.

**Estimated ingestion difficulty:** Hard

**Notes:** The MachiningCloud litigation is ongoing and unresolved. Kennametal's bulk data
path is the least clear of all 8 manufacturers researched. ToolsUnited is the recommended
structured path, but requires a paid subscription. Do not rely on MachiningCloud for
Kennametal data.

---

### 3. Seco Tools

| Field | Detail |
|-------|--------|
| **Official source URL** | `https://www.secotools.com/article/81837` (Download Center) |
| **Digital Tool Assembly** | `https://www.secotools.com/article/125837` |
| **ISO 13399 page** | `https://www.secotools.com/article/iso_13399_standards_on_catalogs` |
| **Available formats** | ISO 13399, STEP, GTC, MTConnect (for feeds/speeds), PDF catalogs, 2D/3D CAD |
| **Login required** | Likely required for Download Center; MachiningCloud account required |
| **ISO 13399 supported** | Yes — explicitly stated on ISO 13399 page |
| **Tooling-library export** | Yes — Digital Tool Assembly feature for 2D/3D CAD export |
| **API exists** | No public API identified |
| **MachiningCloud** | Yes — confirmed partner; 10,000+ tool items available |
| **ToolsUnited** | Yes — confirmed |

**Recommended ingestion strategy:**

1. Register at secotools.com and access the Download Center for GTC/STEP packages
   by product category.
2. Alternatively, use MachiningCloud to browse Seco's catalog and export by category
   (turning inserts, milling inserts, endmills, drills).
3. Parse GTC XML to extract series, designation, ISO grade, and geometry tags; map to
   our schema; manually verify against the Seco product PDF catalog.

**Estimated ingestion difficulty:** Medium

**Notes:** Seco is a Sandvik Group brand, so data quality and format consistency mirror
Sandvik Coromant. The Digital Tool Assembly feature is primarily for CAD/CAM users
(assembly-level export), not bulk catalog import. No feeds/speeds should be imported —
MTConnect data should be excluded from any parsing step.

---

### 4. Walter Tools

| Field | Detail |
|-------|--------|
| **Official source URL** | `https://www.walter-tools.com/en-us/tools/product-data` |
| **Media library / downloads** | `https://www.walter-tools.com/en-us/news-and-media/media-library/downloads` |
| **Available formats** | STEP, ISO 13399 (via MachiningCloud), PDF catalogs; direct page format details not obtainable (JS-rendered) |
| **Login required** | Likely required for direct downloads |
| **ISO 13399 supported** | Yes — confirmed via MachiningCloud partnership (2018 announcement) and Sandvik Group membership |
| **Tooling-library export** | Yes — Walter GPS (Guided Product Selector) exports tool data |
| **API exists** | No public API identified |
| **MachiningCloud** | Yes — confirmed partner (2018 announcement); catalog live on platform |
| **ToolsUnited** | Yes — confirmed |

**Recommended ingestion strategy:**

1. Use MachiningCloud as the primary path — browse and export Walter's catalog by
   product category in GTC/STEP format.
2. Alternatively, register at walter-tools.com and access the product-data downloads
   page directly for STEP/ISO 13399 packages.
3. Walter GPS can also be used to query specific product families and export tool data.

**Estimated ingestion difficulty:** Medium

**Notes:** Walter is a Sandvik Group brand. Direct download page is JS-rendered and could
not be fully evaluated; MachiningCloud is the more reliable bulk-access path. Walter GPS
(desktop software) may require a separate download/install.

---

### 5. Iscar

| Field | Detail |
|-------|--------|
| **Official source URL** | `https://www.iscar.com/eCatalog/Index.aspx` |
| **P21 download page** | `https://www.iscar.com/ecatalog/p21Excel.aspx` |
| **Available formats** | P21 (ISO 13399 STEP), 2D/3D CAD, GTC (via MachiningCloud) |
| **Login required** | E-catalog appears publicly browsable; P21 package downloads may require account (unconfirmed) |
| **ISO 13399 supported** | Yes — Iscar was an original GTC co-developer; P21 files explicitly available |
| **Tooling-library export** | Yes — NEO-ITA (New ISCAR Tool Advisor) and E-CAT assembly feature export P21 and 3D data |
| **API exists** | No public API; ISCAR WORLD app provides mobile access |
| **MachiningCloud** | Yes — confirmed partner; catalog live |
| **ToolsUnited** | Yes — confirmed |

**Recommended ingestion strategy:**

1. Access the P21 download page directly (`iscar.com/ecatalog/p21Excel.aspx`) to obtain
   ISO 13399-compliant P21 packages by product category; P21 files can be parsed with a
   STEP/P21 parser library (e.g., Python `ifc-tools`, `xbim`, or custom EXPRESS parser).
2. For a simpler path: use MachiningCloud or ToolsUnited to access Iscar's structured
   GTC data with pre-parsed property sets.
3. Map extracted fields (series, ISO designation, substrate, geometry) to our schema;
   exclude any feeds/speeds properties.

**Estimated ingestion difficulty:** Medium

**Notes:** Iscar's P21 download page is the most directly accessible of all 8 manufacturers
for ISO 13399 data without requiring MachiningCloud. P21 parsing is more technical than
GTC XML parsing but is well-supported by open-source STEP libraries. The e-catalog
appears functional and publicly browsable.

---

### 6. Mitsubishi Materials

| Field | Detail |
|-------|--------|
| **Official source URL** | `https://www.mmc-carbide.com/us/technical_information/iso/iso13399` |
| **ISO 13399 property list** | `https://www.mmc-carbide.com/us/technical_information/iso/iso13399_property` |
| **CAD download page** | `https://www.mmc-carbide.com/us/download/others/cad` |
| **General downloads** | `https://www.mmc-carbide.com/us/download` |
| **Available formats** | DXF, STEP (ISO 13399-compliant), PDF catalog; P21 format likely via MachiningCloud |
| **Login required** | Direct CAD downloads appear accessible without login; MachiningCloud/ToolsUnited require accounts |
| **ISO 13399 supported** | Yes — explicit ISO 13399 landing page with property documentation |
| **Tooling-library export** | Yes — via MachiningCloud and ToolsUnited (explicitly named by Mitsubishi as their ISO 13399 distribution channels) |
| **API exists** | No public API identified |
| **MachiningCloud** | Yes — confirmed partner; catalog live |
| **ToolsUnited** | Yes — confirmed; Mitsubishi explicitly lists CIMSOURCE/ToolsUnited as a distribution channel |

**Recommended ingestion strategy:**

1. Check the CAD download page (`mmc-carbide.com/us/download/others/cad`) for
   directly downloadable STEP/DXF packages — this is the most accessible path of all
   8 manufacturers and may not require login.
2. The ISO 13399 property documentation page (`mmc-carbide.com/us/technical_information/
   iso/iso13399_property`) is useful for mapping Mitsubishi's property names to our schema
   fields before parsing.
3. Supplement with MachiningCloud or ToolsUnited for GTC-format data and broader
   product coverage.

**Estimated ingestion difficulty:** Easy–Medium

**Notes:** Mitsubishi Materials has the most explicitly documented ISO 13399 property
mapping of all manufacturers researched — their property documentation page names the
specific ISO 13399 properties they publish, which directly aids schema mapping. This
should be the first manufacturer targeted for a structured import pilot.

---

### 7. Guhring

| Field | Detail |
|-------|--------|
| **Official source URL** | `https://guehring.com/en/service/digital-services/cad-and-cutting-data/` |
| **CAD portal** | `https://guehring.partcommunity.com` |
| **Available formats** | XML (ISO/TS 13399-72 / DIN 4000), STEP/STP (ISO 13399 / DIN 4003), DXF (ISO/TS 13399-70), PNG; 50+ formats via CAD portal for 50,000+ tool models |
| **Login required** | Yes — free registration for online shop and CAD portal |
| **ISO 13399 supported** | Yes — most explicitly documented of all 8 manufacturers; names ISO/TS 13399-70, 13399-72, DIN 4000, and DIN 4003 individually on their public website |
| **Tooling-library export** | Yes — via ToolsUnited (GG company code verified on platform); MachiningCloud also confirmed |
| **API exists** | No public API identified |
| **MachiningCloud** | Yes — confirmed; catalog pages verified at machining.cloud |
| **ToolsUnited** | Yes — confirmed; company code "GG" on ToolsUnited with DIN 4000 and ISO 13399/GTC export options visible |

**Recommended ingestion strategy:**

1. Register at guehring.partcommunity.com for the CAD portal — 50,000+ models in
   50+ formats including the XML (ISO/TS 13399-72 / DIN 4000) format that maps directly
   to property sets our schema needs.
2. The XML (DIN 4000) format is particularly valuable: it is structured property data
   (not geometric), making it more parseable than STEP/P21 for schema field extraction.
3. Use ToolsUnited as an alternative for pre-aggregated GTC packages with built-in
   DIN 4000 → ISO 13399 mapping.
4. Focus first on solid endmill and drill families (Guhring's primary product lines).

**Estimated ingestion difficulty:** Easy–Medium

**Notes:** Guhring's explicit format documentation makes schema mapping straightforward.
The XML (DIN 4000 / ISO/TS 13399-72) format is the best target for semi-automated
ingestion — structured property sets, no geometry parsing required. The PartCommunity
CAD portal is a PTC-operated service used by many tool manufacturers; the format selection
and filtering UI is well-designed for per-category downloads. Guhring and Mitsubishi
Materials are the two highest-priority targets for initial structured data import.

---

### 8. Dormer Pramet

| Field | Detail |
|-------|--------|
| **Official source URL** | `https://www.dormerpramet.com/ISO-13399` |
| **Technical downloads** | `https://www.dormerpramet.com/en-us/downloads/technical-page` |
| **Available formats** | ISO 13399 (via MachiningCloud); direct download format details not obtainable (JS-rendered page); legacy PDF referenced at dormerpramet.com/Downloads/DormerPramet_ISO13399.pdf (currently 404) |
| **Login required** | Likely required; contact info.uk@dormerpramet.com |
| **ISO 13399 supported** | Yes — dedicated ISO 13399 page exists; ~40,000 tool parameters documented |
| **Tooling-library export** | Via MachiningCloud (catalog live and verified) |
| **API exists** | No public API identified |
| **MachiningCloud** | Yes — confirmed partner; catalog live at machining.cloud/app/catalogs/dormer-pramet |
| **ToolsUnited** | Unconfirmed — not found in available ToolsUnited partnership listings |

**Recommended ingestion strategy:**

1. Use MachiningCloud as the primary path — browse the Dormer Pramet catalog by
   category and export GTC/STEP packages.
2. Contact info.uk@dormerpramet.com to inquire about bulk data access and format
   availability for the technical downloads page.
3. Until a structured data path is established, use PDF catalog review for family-level
   seed records (indexable inserts for turning and milling are Pramet's core lines;
   solid drills are Dormer's).

**Estimated ingestion difficulty:** Medium–Hard

**Notes:** Dormer Pramet has the least transparent direct-download path of all 8 manufacturers.
The ISO 13399 page exists and confirms support, but the actual data file previously linked
(PDF) is returning 404. MachiningCloud is the most reliable confirmed path. Consider
treating Dormer Pramet as a lower-priority import target until a clearer direct-download
path is established. Dormer Pramet is a Sandvik Group brand.

---

## Summary Table

| Manufacturer | ISO 13399 | MachiningCloud | ToolsUnited | API | Login | Ingestion Difficulty | Best Path |
|--------------|-----------|----------------|-------------|-----|-------|----------------------|-----------|
| Sandvik Coromant | Yes | Yes | Yes | Yes (registration) | Yes | Medium | Developer portal or GTC bulk download |
| Kennametal | Yes | **No** (litigation) | Yes | No | Yes | Hard | ToolsUnited (paid) |
| Seco Tools | Yes | Yes | Yes | No | Likely | Medium | MachiningCloud or Download Center |
| Walter | Yes | Yes | Yes | No | Likely | Medium | MachiningCloud |
| Iscar | Yes | Yes | Yes | No | Partial | Medium | P21 direct download or MachiningCloud |
| Mitsubishi Materials | Yes | Yes | Yes | No | Partial | Easy–Medium | Direct CAD download page |
| Guhring | Yes (best documented) | Yes | Yes | No | Yes (free) | Easy–Medium | XML (DIN 4000) via CAD portal or ToolsUnited |
| Dormer Pramet | Yes | Yes | Unconfirmed | No | Likely | Medium–Hard | MachiningCloud |

---

## Recommended Ingestion Priority

Based on format accessibility, documentation quality, and absence of legal complications:

1. **Mitsubishi Materials** — Explicit ISO 13399 property docs, accessible CAD download page,
   may not require login for initial files.
2. **Guhring** — Best-documented formats (XML/DIN 4000 named explicitly), 50,000+ models
   in PartCommunity portal, straightforward format for schema mapping.
3. **Iscar** — P21 direct download page accessible; P21 parsing is technical but
   well-supported by open-source STEP libraries.
4. **Sandvik Coromant** — Developer portal API is the cleanest path if access is approved;
   GTC bulk download as fallback.
5. **Seco Tools / Walter** — Both Sandvik Group brands; MachiningCloud is reliable path.
6. **Dormer Pramet** — Lower priority; rely on MachiningCloud; direct download path unclear.
7. **Kennametal** — Lowest priority for structured automation; ToolsUnited (paid) or manual
   catalog extraction are the only reliable paths given the MachiningCloud litigation.

---

## Ingestion Rules (Must Be Followed for All Sources)

Regardless of source or format, these rules apply to any future import:

- **No feeds, speeds, or cutting data** — do not import sfm, rpm, feed rate, ipr, ipm,
  fz, vc, or any related fields from any ISO 13399 source.
- **No invented dimensions** — only import dimension values explicitly present in the source
  data; leave `dimensions: {}` otherwise.
- **Source traceability required** — every imported record must carry `source_label`,
  `source_url`, and `verification_status`.
- **Unverified records** — use `verification_status: sample_family_level_not_catalog_verified`
  until a human reviewer has cross-checked the record against the source catalog page.
- **Audit before commit** — run `python tools/audit_tooling_search_records.py` before any
  bulk import commit.
- **Exact-tooling records stay separate** — do not merge ISO 13399 imports into the
  reviewed family-level catalog records in `tool_data/catalog_ingestion/reviewed/`.

---

## Source References

- [Sandvik Coromant Tool Data Downloads](https://www.sandvik.coromant.com/en-us/downloads/tool-data/pages/default.aspx)
- [Sandvik Coromant Developer Portal](https://developers.sandvik.coromant.com/)
- [Kennametal Collaboration Space](https://www.kennametal.com/us/en/my-account/collaboration-space.html)
- [Kennametal CAM Integrations](https://www.kennametal.com/us/en/resources/software.html)
- [Seco Tools ISO 13399 Page](https://www.secotools.com/article/iso_13399_standards_on_catalogs)
- [Seco Digital Tool Assembly](https://www.secotools.com/article/125837)
- [Walter Tools Product Data](https://www.walter-tools.com/en-us/tools/product-data)
- [Iscar E-Catalog](https://www.iscar.com/eCatalog/Index.aspx)
- [Iscar P21 Download Page](https://www.iscar.com/ecatalog/p21Excel.aspx)
- [Mitsubishi Materials ISO 13399](https://www.mmc-carbide.com/us/technical_information/iso/iso13399)
- [Mitsubishi Materials CAD Downloads](https://www.mmc-carbide.com/us/download/others/cad)
- [Guhring CAD and Cutting Data](https://guehring.com/en/service/digital-services/cad-and-cutting-data/)
- [Guhring CAD Portal](https://guehring.partcommunity.com)
- [Dormer Pramet ISO 13399](https://www.dormerpramet.com/ISO-13399)
- [MachiningCloud Partners with Sandvik Coromant (PR Newswire, Jan 2026)](https://www.prnewswire.com/news-releases/machiningcloud-partners-with-sandvik-coromant-302671616.html)
- [MachiningCloud Litigation Against Kennametal (PR Newswire, Feb 2025)](https://www.prnewswire.com/news-releases/machiningcloud-brings-litigation-against-kennametal-for-theft-of-trade-secrets-and-breach-of-contract-302367951.html)
- [Iscar Partners with MachiningCloud (Canadian Metalworking)](https://www.canadianmetalworking.com/canadianmetalworking/news/management/iscar-partners-with-machining-cloud)
- [ToolsUnited Home](https://info.toolsunited.com/)
- [ToolsUnited Pricing](https://info.toolsunited.com/flatrate/)
- [ISO 13399 Wikipedia](https://en.wikipedia.org/wiki/ISO_13399)
- [GTC Format Overview (Siemens Blog)](https://blogs.sw.siemens.com/nx-manufacturing/generic-tool-catalog-revolutionizes-cutting-tool-data-exchange/)
