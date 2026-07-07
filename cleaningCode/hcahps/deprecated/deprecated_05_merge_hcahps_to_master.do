*===============================================================================
* SCRIPT: 05_merge_hcahps_to_master.do
* PURPOSE: Assembles HCAHPS Panel, then merges to BOTH Facility & Provider Networks.
*===============================================================================

include "C:/Users/omarf/Dropbox/personal_files_omar_farrag/Research/general_cms_data/cleaningCode/00_initialize.do"

display as text "=== STARTING PHASE 2 MULTI-LEVEL MASTER MERGE ==="

/*
*-------------------------------------------------------------------------------
* STEP 1: ASSEMBLE HCAHPS STANDALONE PANEL
*-------------------------------------------------------------------------------
import delimited "$projectRoot/hcahps/harmonized/hcahps_structural_panel.csv", stringcols(1 6) clear
destring year, replace force
replace state = upper(state)
replace hosp_name = upper(hosp_name)
duplicates drop ccn year, force
sort ccn year
tempfile structural_data
save `structural_data', replace

import delimited "$projectRoot/hcahps/harmonized/hcahps_master_panel.csv", stringcols(1) clear
destring year, replace force
duplicates drop ccn year, force
sort ccn year

merge 1:1 ccn year using `structural_data'
drop if _merge == 2 
drop _merge
save "$phase2/hcahps_final_panel.dta", replace
*/

*-------------------------------------------------------------------------------
* STEP 1: ASSEMBLE HCAHPS STANDALONE PANEL
*-------------------------------------------------------------------------------
import delimited "$projectRoot/hcahps/harmonized/hcahps_structural_panel.csv", stringcols(1 6) clear
destring year, replace force
replace state = upper(state)
replace hosp_name = upper(hosp_name)

* ---> THE FIX: Strip single quotes from the structural CCNs <---
replace ccn = subinstr(ccn, "'", "", .)

duplicates drop ccn year, force
sort ccn year
tempfile structural_data
save `structural_data', replace

import delimited "$projectRoot/hcahps/harmonized/hcahps_master_panel.csv", stringcols(1) clear
destring year, replace force

* ---> THE FIX: Strip single quotes from the master CCNs <---
replace ccn = subinstr(ccn, "'", "", .)

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
    duplicates drop ccn year, force 
    
    * ANTI-GHOST PROTOCOL
    capture drop h_comp* h_clean* h_quiet* h_hosp_rating* h_recmnd* hosp_name city state zip_code county hosp_type ownership emergency_services
    
    merge 1:1 ccn year using "$phase2/hcahps_final_panel.dta"
    keep if _merge == 3
    drop _merge
    save "$master/cms_ultimate_facility_network.dta", replace
}

*-------------------------------------------------------------------------------
* STEP 3: MERGE TO INDIVIDUAL PROVIDER PANEL (NOW WITH FACILITY AGGREGATES!)
*-------------------------------------------------------------------------------
capture confirm file "$phase1/cms_master_provider_panel.dta"
if _rc == 0 {
    local facilDir "$projectRoot/cliniciansAndGroups/facilityAffiliation/dta/harmonized"
    local files : dir "`facilDir'" files "*_harmonized.dta"
    
    tempfile npi_ccn_link
    save `npi_ccn_link', emptyok
    foreach f in `files' {
        use "`facilDir'/`f'", clear
        keep npi year ccn
        drop if ccn == ""
        append using `npi_ccn_link'
        save `npi_ccn_link', replace
    }
    use `npi_ccn_link', clear
    duplicates drop npi year ccn, force
    save `npi_ccn_link', replace
    
    merge m:1 npi year using "$phase1/cms_master_provider_panel.dta"
    keep if _merge == 3
    drop _merge
    
    * ---> THE FIX: INJECT HOSPITAL AGGREGATES (mean_*, prop_*) INTO PROVIDER PANEL <---
    *merge m:1 ccn year using "$outputRoot/cleaned_data/cms_master_facility_panel.dta", keep(master match) nogenerate
    * ---> THE FIX: INJECT HOSPITAL AGGREGATES (mean_*, prop_*) INTO PROVIDER PANEL <---
    merge m:1 ccn year using "$phase1/cms_master_facility_panel.dta", keep(master match) update replace nogenerate

    * ANTI-GHOST PROTOCOL: Drop existing HCAHPS vars, but KEEP mean_* and prop_*
    capture drop h_comp* h_clean* h_quiet* h_hosp_rating* h_recmnd* hosp_name city state zip_code county hosp_type ownership emergency_services
    
    merge m:1 ccn year using "$phase2/hcahps_final_panel.dta"
    keep if _merge == 3
    drop _merge
    save "$master/cms_ultimate_provider_network.dta", replace
}