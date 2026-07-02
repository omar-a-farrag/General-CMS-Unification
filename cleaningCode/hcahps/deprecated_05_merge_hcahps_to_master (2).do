*===============================================================================
* SCRIPT: 05_merge_hcahps_to_master.do
* PURPOSE: Assembles HCAHPS Panel, then merges to BOTH Facility & Provider Networks.
*===============================================================================
clear

global component "hcahps"
global script_name "05_merge_hcahps_to_master"

include "C:/Users/omarf/Dropbox/personal_files_omar_farrag/Research/general_cms_data/cleaningCode/00_initialize.do"

display as text "=== STARTING PHASE 2 MULTI-LEVEL MASTER MERGE ==="

*-------------------------------------------------------------------------------
* STEP 1: ASSEMBLE HCAHPS STANDALONE PANEL
*-------------------------------------------------------------------------------
import delimited "$projectRoot/hcahps/harmonized/hcahps_structural_panel.csv", stringcols(1 6) clear
destring year, replace force
replace state = upper(state)
replace hosp_name = upper(hosp_name)
replace ccn = subinstr(ccn, "'", "", .)
replace ccn = strtrim(ccn)
duplicates drop ccn year, force
sort ccn year
tempfile structural_data
save `structural_data', replace

import delimited "$projectRoot/hcahps/harmonized/hcahps_master_panel.csv", stringcols(1) clear
destring year, replace force
replace ccn = subinstr(ccn, "'", "", .)
replace ccn = strtrim(ccn)
duplicates drop ccn year, force
sort ccn year

merge 1:1 ccn year using `structural_data'
drop if _merge == 2 
drop _merge
save "$phase2/hcahps_final_panel.dta", replace

*-------------------------------------------------------------------------------
* STEP 2: MERGE TO FACILITY AGGREGATE PANEL
*-------------------------------------------------------------------------------
capture confirm file "$phase1/cms_master_facility_panel.dta"
if _rc == 0 {
    use "$phase1/cms_master_facility_panel.dta", clear
    capture tostring ccn, replace force
    replace ccn = strtrim(ccn)
    duplicates drop ccn year, force 
    
    * Left Join the HCAHPS data
    merge 1:1 ccn year using "$phase2/hcahps_final_panel.dta", keep(master match) nogenerate
    save "$master/cms_ultimate_facility_network.dta", replace
}

*-------------------------------------------------------------------------------
* STEP 3: MERGE TO INDIVIDUAL PROVIDER PANEL 
*-------------------------------------------------------------------------------
capture confirm file "$phase1/cms_master_provider_panel.dta"
if _rc == 0 {
    use "$phase1/cms_master_provider_panel.dta", clear
    capture tostring ccn, replace force
    replace ccn = strtrim(ccn)
    
    * Left Join the HCAHPS data directly to the providers
    merge m:1 ccn year using "$phase2/hcahps_final_panel.dta", keep(master match) nogenerate
    
    save "$master/cms_ultimate_provider_network.dta", replace
}