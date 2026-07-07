* ==============================================================================
* SCRIPT: Final Publication Audit (RVUs & Geographic Markets)
* ==============================================================================
clear all
include "C:/Users/omarf/Dropbox/personal_files_omar_farrag/Research/general_cms_data/cleaningCode/00_initialize.do"

display as text ""
display as text "=== AUDIT 1: INPATIENT PROVIDER PANEL ==="
use "$projectRoot/publishable_data/master_provider_inpatient_2013_2024.dta", clear

* 1. Check RVU Integrity (Individual and Inherited Facility)
capture noisily summarize partb_rvu_work fac_total_work_rvu fac_total_fac_rvu

* 2. Check Geographic Market Linkage (Dartmouth Atlas)
capture noisily summarize hsanum hrrnum
capture noisily count if missing(hsanum)

display as text ""
display as text "=== AUDIT 2: INPATIENT FACILITY PANEL ==="
use "$projectRoot/publishable_data/master_facility_inpatient_2013_2024.dta", clear

* 1. Check Facility RVU Aggregation
capture noisily summarize fac_total_work_rvu fac_total_fac_rvu

* 2. Check Geographic Market Linkage
capture noisily summarize hsanum hrrnum
capture noisily count if missing(hsanum)