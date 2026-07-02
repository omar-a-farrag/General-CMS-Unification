# The CMS Provider-Facility Master Network (2013–2024)
**Principal Investigator:** Omar Farrag  

## Overview
This repository provides a unified, longitudinal data network linking Medicare Part B physicians, Part D prescribing behaviors, hospital structural characteristics, and clinical quality metrics (HCAHPS, MIPS, ASCQR). 

Historically, CMS data is highly fragmented across different reporting ecosystems (e.g., Physician Compare, Hospital Compare, QPP). This project harmonizes over 10 years of messy administrative data into four clean, relational master panels designed specifically for rigorous econometric analysis.

## The Data Philosophy: Modular & Relational
To avoid memory bloat and sparse matrices, this data is not provided as a single monolithic file. It is distributed as four "Terminal Nodes" that can be merged dynamically based on your research question. All data is normalized to a strict "Golden Schema" to track variable origin.

### The 4 Master Panels
1. **`master_provider_inpatient_2013_2023.dta`**: Individual physicians linked to acute care hospitals. Contains individual volume/prescribing, hospital HCAHPS scores, facility averages (`fac_`), and individual MIPS scores.
2. **`master_provider_outpatient_asc_2015_2023.dta`**: Physicians linked to Ambulatory Surgical Centers (ASCs). Contains ASC quality metrics assigned via localized market proxies.
3. **`master_facility_inpatient_2013_2023.dta`**: Hospital-level aggregates, structural data, and volume-weighted average MIPS scores (`fac_mips_*`) of affiliated staff.
4. **`master_facility_outpatient_asc_2015_2024.dta`**: ASC-level aggregate structural and quality data. *(Note: ASC reporting begins robustly in 2015, and facility-level data is available through 2024 due to standard CMS claims processing lags).*

## Quick Start (Stata)
All panels are pre-encoded and compressed. To analyze the impact of a state-level policy on physician behavior, simply load the provider panel and exploit the relational architecture:
```stata
use "master_provider_inpatient_2013_2023.dta", clear
keep if cms_state == 33 // e.g., filter for New York