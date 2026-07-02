*===============================================================================
* SCRIPT: 11_merge_facility_quality_demographics.do
* PURPOSE: Merges Inpatient, HOPD, and ASC metrics into Phase 3 Master Sets.
*===============================================================================
clear

global component "in_out_patient"
global script_name "11_merge_facility_quality_demographics"

include "C:/Users/omarf/Dropbox/personal_files_omar_farrag/Research/general_cms_data/cleaningCode/00_initialize.do"

display as text "=== STARTING PHASE 3 QUALITY NETWORK ASSEMBLY ==="

*-------------------------------------------------------------------------------
* STEP 1: PREP THE NEW QUALITY PANELS
*-------------------------------------------------------------------------------
import delimited "$projectRoot/hcahps/harmonized/inpatient_quality_panel.csv", stringcols(1) clear
destring year, replace force
duplicates drop ccn year, force
sort ccn year
tempfile inpatient_qual
save `inpatient_qual', replace

import delimited "$projectRoot/hcahps/harmonized/outpatient_hopd_quality_panel.csv", stringcols(1) clear
destring year, replace force
duplicates drop ccn year, force
sort ccn year
tempfile hopd_qual
save `hopd_qual', replace

import delimited "$projectRoot/hcahps/harmonized/outpatient_asc_quality_panel.csv", stringcols(1) clear
destring year, replace force
tostring zipcode, replace force
duplicates drop asc_id year, force

* Create ASC Market Level Data by ZIP
preserve
    drop if zipcode == "" | zipcode == "." | zipcode == "nan"
    collapse (mean) asc_rate_*, by(zipcode year)
    rename zipcode cms_zip
    tempfile asc_market_data
    save `asc_market_data', replace
restore

save "$phase3/cms_phase3_outpatient_asc_facility.dta", replace

*-------------------------------------------------------------------------------
* STEP 2: BUILD PHASE 3 INPATIENT/HOPD FACILITY NETWORK
*-------------------------------------------------------------------------------
use "$master/cms_ultimate_facility_network.dta", clear
sort ccn year

capture drop rrp_* mortality_* hvbp_* hac_* mspb_* hopd_*
merge 1:1 ccn year using `inpatient_qual', keep(master match)
drop _merge

merge 1:1 ccn year using `hopd_qual', keep(master match)
drop _merge

save "$phase3/cms_phase3_inpatient_facility.dta", replace

*-------------------------------------------------------------------------------
* STEP 3: BUILD PHASE 3 INPATIENT/HOPD PROVIDER NETWORK
*-------------------------------------------------------------------------------
use "$master/cms_ultimate_provider_network.dta", clear
sort ccn year

capture drop rrp_* mortality_* hvbp_* hac_* mspb_* hopd_*
merge m:1 ccn year using `inpatient_qual', keep(master match)
drop _merge

merge m:1 ccn year using `hopd_qual', keep(master match)
drop _merge

save "$phase3/cms_phase3_inpatient_provider.dta", replace

*-------------------------------------------------------------------------------
* STEP 4: BUILD PHASE 3 ASC PROVIDER NETWORK (ZIP LINKAGE)
*-------------------------------------------------------------------------------
use "$phase1/cms_master_provider_panel.dta", clear

tostring cms_zip, replace force
replace cms_zip = substr(cms_zip, 1, 5)

merge m:1 cms_zip year using `asc_market_data', keep(match)
drop _merge

save "$phase3/cms_phase3_outpatient_asc_provider.dta", replace
display "=== PHASE 3 NETWORK ASSEMBLY COMPLETE! ==="