# The CMS Provider-Facility Master Network (2013–2024)
**Principal Investigator:** Omar Farrag  

## Overview
This repository provides a unified, longitudinal data network linking Medicare Part B physician behaviors, Part D prescribing patterns, hospital structural characteristics, and facility-level clinical quality metrics (HCAHPS, HVBP, MIPS, ASCQR). 

Historically, CMS data is highly fragmented across different reporting ecosystems (e.g., Physician Compare, Hospital Compare, QPP). This project harmonizes over 10 years of messy administrative data into four clean, relational master panels. The architecture of these datasets is explicitly designed to facilitate rigorous econometric analysis, particularly regarding the spillovers of the Hospital Value-Based Purchasing (HVBP) program into outpatient prescribing, facility substitution, and clinical decision-making.

## Order of Scripts
Code is located in `cleaningCode`. Run the scripts sequentially within these subfolders:
1) `cms`
2) `hcahps`
3) `mips`
4) `final_cleaning`

The `00_initialize.do` script, located at the same level as the above four subfolders within `cleaningCode`, is necessary to establish global macros and paths for all downstream scripts. 

## The Data Philosophy: Modular & Relational
To avoid memory bloat and sparse matrices, this data is not provided as a single monolithic file. It is distributed as four "Terminal Nodes" that can be merged dynamically based on your research question. All data is normalized to a strict "Golden Schema" to track variable origin.

### The 4 Master Panels (Phase 4 / Publishable Data)
1. **`master_provider_inpatient_2013_2024.dta`**: Individual physicians linked to acute care hospitals. Contains individual volume/prescribing, hospital HCAHPS scores, HVBP penalties, mortality/readmission rates, facility averages (`fac_`), and individual MIPS scores.
2. **`master_provider_outpatient_asc_2013_2024.dta`**: Physicians linked to Ambulatory Surgical Centers (ASCs). Contains individual prescribing/MIPS, along with ASC quality metrics (`zip_asc_`), patient experience (`zip_oas_`), and facility MIPS (`fac_mips_`) assigned via localized ZIP-code market proxies.
3. **`master_facility_inpatient_2013_2024.dta`**: Hospital-level aggregates, structural data, outpatient surgical volumes (OP-26), HVBP metrics, and volume-weighted average MIPS scores (`fac_mips_*`) of affiliated staff.
4. **`master_facility_outpatient_asc_2013_2024.dta`**: ASC-level aggregate structural data, clinical quality rates, OAS CAHPS patient satisfaction scores, and local-market average MIPS scores. *(Note: ASC reporting begins robustly in 2015, and facility-level data is available through 2024 due to standard CMS claims processing lags).*
