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
* --- INPATIENT (Clinical Outcomes & HVBP) ---
import delimited "$projectRoot/hcahps/harmonized/inpatient_quality_panel.csv", stringcols(1) clear
destring year, replace force
tostring zipcode, replace force
duplicates drop ccn year, force
sort ccn year
tempfile inpatient_qual

* Apply Inpatient Labels
capture label variable totalperformance_score "HVBP: Total Performance Score"
capture label variable mspb_score "Medicare Spending Per Beneficiary (MSPB) Score"
capture label variable mortality_rate_ami "30-Day Mortality Rate (AMI)"
capture label variable mortality_rate_hf "30-Day Mortality Rate (HF)"
capture label variable mortality_rate_pn "30-Day Mortality Rate (PN)"
capture label variable rrp_excess_ratio_ami "Readmission: Excess Ratio (AMI)"
capture label variable rrp_excess_ratio_hf "Readmission: Excess Ratio (HF)"
capture label variable rrp_excess_ratio_pn "Readmission: Excess Ratio (PN)"
capture label variable haiconditionprocedure_score "HVBP: HAI Condition Total Score"
capture label variable amiconditionprocedure_score "HVBP: AMI Condition Total Score"
capture label variable hfconditionprocedure_score "HVBP: HF Condition Total Score"
capture label variable pnconditionprocedure_score "HVBP: PN Condition Total Score"
capture label variable hac_total_score "Hospital-Acquired Condition (HAC) Score"
capture label variable paym_30_ami "Payment Category: 30-Day AMI Episode"
capture label variable paym_30_hf "Payment Category: 30-Day Heart Failure Episode"
capture label variable paym_30_pn "Payment Category: 30-Day Pneumonia Episode"
save `inpatient_qual', replace


* --- HOPD (ED Wait Times & Volume) ---
import delimited "$projectRoot/hcahps/harmonized/outpatient_hopd_quality_panel.csv", stringcols(1) clear
destring year, replace force
tostring zipcode, replace force
duplicates drop ccn year, force
sort ccn year
tempfile hopd_qual

* Apply HOPD Labels
capture label variable op_8 "HOPD (OP-8): MRI Lumbar Spine for Low Back Pain (Overuse)"
capture label variable op_22 "HOPD (OP-22): Patient Left ED Without Being Seen (%)"
capture label variable op_26 "HOPD (OP-26): Total Outpatient Surgical Procedure Volume"
capture label variable op_40 "HOPD (OP-40): STEMI Clinical Quality Measure"
capture label variable oas_rating_linear "HOPD OAS CAHPS: Linear Mean Rating"
capture label variable oas_recmnd_linear "HOPD OAS CAHPS: Linear Mean Recommend"
capture label variable oas_rating_9_10 "HOPD OAS CAHPS: Rating 9 or 10 (%)"
capture label variable oas_recmnd_dy "HOPD OAS CAHPS: Definitely Recommend (%)"
save `hopd_qual', replace


* --- ASC (OAS CAHPS & Clinical) ---
import delimited "$projectRoot/hcahps/harmonized/outpatient_asc_quality_panel.csv", stringcols(1) clear
destring year, replace force
tostring zipcode, replace force

* Ensure metrics are numeric
capture destring asc_* oas_*, replace force

* Apply ASC Labels
capture label variable asc_1 "ASC-1: Patient Burn Rate"
capture label variable asc_2 "ASC-2: Patient Fall Rate"
capture label variable asc_3 "ASC-3: Wrong Site/Side/Patient/Procedure/Implant Rate"
capture label variable asc_4 "ASC-4: All-Cause Hospital Transfer or Admission Rate"
capture label variable asc_8 "ASC-8: Influenza Vaccination Coverage"
capture label variable oas_rating_linear "ASC OAS CAHPS: Linear Mean Rating"
capture label variable oas_recmnd_linear "ASC OAS CAHPS: Linear Mean Recommend"
capture label variable oas_rating_9_10 "ASC OAS CAHPS: Rating 9 or 10 (%)"
capture label variable oas_recmnd_dy "ASC OAS CAHPS: Definitely Recommend (%)"

* Build the 100-Point Outpatient Composite permanently
capture confirm variable oas_prof_care_clean
if !_rc {
    egen oas_grp1 = rowmean(oas_prof_care_clean)
    egen oas_grp2 = rowmean(oas_communic_expect)
    egen oas_grp3 = rowmean(oas_rating_9_10 oas_recmnd_dy)
    egen oas_100_score = rowmean(oas_grp1 oas_grp2 oas_grp3)
}
duplicates drop asc_id year, force

* ---> SAVE THE FACILITY ASC PANEL FIRST <---
save "$phase3/cms_phase3_outpatient_asc_facility.dta", replace

* ---> NOW COLLAPSE FOR THE PROVIDER MARKET PROXY <---
* We use 'ds' to select ONLY the numeric variables, protecting text columns like asc_id and city.
ds asc_* oas_*, has(type numeric)
local num_vars = r(varlist)

collapse (mean) `num_vars', by(zipcode year)

* Rename them to avoid overwriting identical metrics inside the provider panel
rename asc_* zip_asc_*
rename oas_* zip_oas_*

* ---> RENAME TO MATCH PROVIDER PANEL <---
rename zipcode cms_zip 
tempfile asc_market_data
save `asc_market_data', replace


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
