# Technical Appendix: Data Engineering & Attribution Methodology

## 1. Provider Phenotyping: The "Dual Lens" Approach
To characterize provider behavior from raw claims without selection bias, we aggregated millions of line items using two distinct frameworks:

* **Lens 1: The Microscope (Hypothesis-Driven):** We track highly specific, discretionary clinical choices utilizing both *Absolute* and *Conditional* mathematical frameworks:
    * **Conditional Intensity (Upcoding & Severity Preference):** We calculate rates conditional on specific clinical lanes. For example, the `partb_em_upcode_rate` measures Level 4/5 E&M visits divided strictly by total E&M visits (revenue-seeking). The `partd_opioid_strong_rate` isolates the choice to use Schedule II narcotics rather than weaker alternatives. 
    * **Absolute Reliance (Overtreatment):** We measure systemic overtreatment based on "Choosing Wisely" guidelines (e.g., unnecessary joint injections, broad reliance on advanced imaging), denominating these actions against the provider's *total* service volume.
    * *Note: To ensure peer-review transparency, the Python aggregation scripts automatically export the exact HCPCS/NDC classifications used for these rates directly into LaTeX Appendix tables.*

* **Lens 2: The Telescope (Data-Driven):** We calculate systematic metrics covering the entire universe of claims. 
    * *Generic Prescribing Rate:* Using our internal USAN crosswalk.
    * *Empirical High-Cost Rate:* The proportion of a physician's claims where the drug/service cost falls in the top 25th percentile *for its specific therapeutic class*.

## 2. The Relational Architecture & Geographic Market Proxies
Because Medicare data is siloed, linking a provider's billing actions to their facility's quality environment required two distinct merging strategies:
* **The Inpatient Direct Link:** Using the *Physician Compare* structural datasets, we mapped individual NPIs directly to their affiliated hospital's CMS Certification Number (CCN). This allows a 1:1 attribution of hospital HCAHPS and clinical scores to the specific providers working there.
* **The Outpatient Market Proxy:** Because independent Ambulatory Surgical Centers (ASCs) lack a unified direct-affiliation crosswalk, we utilize a geographic market proxy. We collapse ASC clinical metrics (`asc_rate_`), OAS CAHPS patient satisfaction scores (`oas_`), and volume-weighted ASC provider MIPS scores (`fac_mips_`) to the 5-digit ZIP code level. Outpatient providers inherit the prevailing quality and administrative standards of the localized outpatient market in which they operate.


## 3. Dealing with CMS Data Chaos
Our extraction pipeline was built to handle extreme administrative volatility:
* **HCAHPS File Naming:** Over 15 years, HCAHPS reporting morphed from Microsoft Access `.mdb` files (2008), to generic CSVs, to Socrata Hash anomalies (2020), to snake_case. 
* **Experience Year Lagging:** CMS reports quality metrics with a chronological lag. We explicitly lagged HCAHPS reporting years by $t-1$ to ensure that physician billing behavior in Year $X$ is correlated with the hospital environment of Year $X$.
* **Schema Drift:** We enforce a strict "Golden Schema" (`partd_`, `partb_`, `fac_`) to ensure multi-year structural merges do not collapse due to CMS column renaming.

## 4. Structural Limitations of MIPS
Researchers utilizing the `mips_*` variables must account for three critical structural biases inherent to the MACRA legislation:
1. **The Low Volume Threshold (LVT):** MIPS systemically excludes part-time, rural, or low-Medicare-volume clinicians. The data represents a higher-volume subset of the workforce.
2. **Facility-Based Scoring:** For facility-bound clinicians (e.g., Anesthesiologists), CMS often automatically adopts the hospital's Value-Based Purchasing (VBP) score as the individual's MIPS score.
3. **COVID-19 Extreme and Uncontrollable Circumstances (EUC):** Performance years 2020–2022 feature massive, non-random attrition due to EUC exception applications.