* ==============================================================================
* SCRIPT: The Final Phase 3 Merge Audit
* ==============================================================================
clear all
include "C:/Users/omarf/Dropbox/personal_files_omar_farrag/Research/general_cms_data/cleaningCode/00_initialize.do"

display as text ""
display as text "=== AUDIT 1: PHASE 3 INPATIENT PROVIDER NETWORK ==="
use "$phase3/cms_phase3_inpatient_provider.dta", clear

* Checking coexistence of Provider Data and Facility Data
capture noisily summarize partd_opioid_rate totalperformance_score op_26 mspb_score mortality_rate_ami

display as text ""
display as text "=== AUDIT 2: PHASE 3 ASC PROVIDER NETWORK ==="
use "$phase3/cms_phase3_outpatient_asc_provider.dta", clear

* Checking the Geographic Zip Linkage
capture noisily summarize zip_asc_1 zip_asc_4 zip_oas_recmnd_linear