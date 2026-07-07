# Technical Appendix: Data Engineering & Attribution Methodology

## 1. Provider Phenotyping: The "Dual Lens" Approach
To characterize provider behavior from raw claims without selection bias, we aggregated millions of line items using two distinct frameworks:

* **Lens 1: The Microscope (Hypothesis-Driven):** We track highly specific, discretionary clinical choices utilizing both *Absolute* and *Conditional* mathematical frameworks:
    * **Conditional Intensity (Upcoding & Severity Preference):** We calculate rates conditional on specific clinical lanes. For example, the `partb_em_upcode_rate` measures Level 4/5 E&M visits divided strictly by total E&M visits (revenue-seeking). 
    * **Absolute Reliance (Overtreatment):** We measure systemic overtreatment based on "Choosing Wisely" guidelines (e.g., unnecessary joint injections, broad reliance on advanced imaging), denominating these actions against the provider's *total* service volume.
**Isolating Productivity (RVU Weighting):** A persistent flaw in claims analysis is utilizing raw service counts (`tot_srvcs`), which mathematically equates a 5-minute checkup with a 4-hour surgery. To isolate true clinical effort and standardize productivity, this dataset maps line-item HCPCS codes directly to the Q1 CMS Physician Fee Schedule. Utilizing the Q1 baseline eliminates administrative intra-year "RVU drift." Provider effort is quantified precisely using pure Work RVUs (`partb_rvu_work`), while aggregate hospital capacity is modeled utilizing the sum of Work, Facility Practice Expense, and Malpractice RVUs (`fac_total_fac_rvu`).

* **Lens 2: The Telescope (Data-Driven):** We calculate systematic metrics covering the entire universe of claims. 
    * *Generic Prescribing Rate:* Using our internal USAN crosswalk.
    * *Empirical High-Cost Rate:* The proportion of prescribed drugs residing in the 75th+ cost percentile of their therapeutic class.

## 2. Facility Attribution and Market Boundaries
To analyze facility-level spillovers, clinicians must be accurately attributed to specific care settings. 
* **Inpatient Linkage:** Achieved utilizing the CMS Provider Enrollment, Chain, and Ownership System (PECOS) Medicare Data on Provider Practice and Specialty (MDPPAS) files, which reliably map NPIs to hospital CCNs based on billing plurality.
* **Outpatient ASC Linkage:** Due to sparse reporting of specific ASC IDs in PECOS, outpatient facility attributes are linked via Geographic ZIP Market Proxies (`cms_zip`), allowing us to attach localized ASC market metrics (e.g., competition, patient satisfaction) to providers operating in those areas.
**Market Boundaries:** To formalize the demand-side choice set and control for spatial market dynamics, all providers and facilities are geographically linked to the Dartmouth Atlas. By mapping local billing ZIP codes to standard Hospital Service Areas (HSAs) and Hospital Referral Regions (HRRs), the data isolates discrete, empirically validated health care markets rather than relying on arbitrary state or county lines.

## 3. Dealing with CMS Data Chaos
Our Python/Stata extraction pipeline was custom-built to handle extreme administrative volatility in CMS data distribution over the 10-year panel:
* **Content-Agnostic Extraction:** In 2020, CMS migrated hospital data to the Socrata API, replacing descriptive filenames (e.g., `hvbp_outcomes.csv`) with gibberish alphanumeric hashes (e.g., `48nr-hqxx.csv`). Our pipeline bypasses filenames entirely, dynamically scanning every CSV column header for required metrics to immunize the data build against future CMS renaming.
* **Universal Demographics Sniffer:** CMS routinely splits quality datasets into separate files, often dropping geographic identifiers (ZIP, City, State) in the process. The pipeline utilizes a continuous sniffer combined with Pandas `.combine_first()` to reconstruct and carry forward geographic data across fragmented files.
* **Wide-to-Long Aggregation:** Certain metrics are mathematically reconstructed from nested arrays. For example, the `op_26` Outpatient Surgical Volume metric is derived by safely cleaning and summing 9 separate wide-format anatomical columns (e.g., Gastrointestinal, Musculoskeletal) into a true facility-level aggregate.
* **Experience Year Lagging:** CMS reports quality metrics with a chronological lag. We explicitly lagged HCAHPS/HVBP reporting years by $t-1$ to ensure that physician billing behavior in Year $X$ is correlated with the hospital environment of Year $X$.

## 4. Structural Limitations of MIPS
Researchers utilizing the `mips_*` variables must account for three critical structural biases inherent to the MACRA legislation:
1. **The Low Volume Threshold (LVT):** MIPS systemically excludes part-time, rural, or low-Medicare-volume clinicians. The data represents a higher-volume subset of the workforce.
2. **Facility-Based Scoring:** For facility-bound clinicians (e.g., Anesthesiologists), CMS often automatically adopts the hospital's Value-Based Purchasing (HVBP) score as the individual's MIPS score.
3. **COVID-19 Extreme and Uncontrollable Circumstances (EUC):** Performance years 2020–2022 feature massive, non-random attrition due to EUC exception applications.