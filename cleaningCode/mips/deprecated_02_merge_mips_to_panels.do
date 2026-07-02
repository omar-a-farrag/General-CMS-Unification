clear all
set more off

* ==============================================================================
* 1. INITIALIZE ENVIRONMENT & START DYNAMIC LOG
* ==============================================================================
global component "mips"
global script_name "02_merge_mips_to_panels"

* Hardcode the path to the initialize script
do "C:/Users/omarf/Dropbox/personal_files_omar_farrag/Research/general_cms_data/cleaningCode/00_initialize.do"


* ==============================================================================
* 2. INPATIENT PROVIDER PANEL MERGE
* ==============================================================================
di "Starting Inpatient Provider Merge..."
use "$phase3/cms_phase3_inpatient_provider.dta", clear

* Ensure NPI is a string to match the MIPS master panel
capture tostring npi, replace force

* Merge MIPS data 
merge m:1 npi year using "$phase4/mips_clinician_master_panel_2017_2023$fileSuffix.dta", ///
    keep(master match) gen(_merge_mips)

* Rename the merge variable so it doesn't collide in future merges
rename _merge_mips mips_merge_status_inp
label define mips_lbl 1 "No MIPS Score (Exempt/LVT)" 3 "Matched to MIPS"
label values mips_merge_status_inp mips_lbl

* Save the new Phase 4 Inpatient Provider Panel
save "$phase4/cms_phase4_inpatient_provider$fileSuffix.dta", replace

* ==============================================================================
* 3. OUTPATIENT (ASC) PROVIDER PANEL MERGE
* ==============================================================================
di "Starting Outpatient ASC Provider Merge..."
use "$phase3/cms_phase3_outpatient_asc_provider.dta", clear

capture tostring npi, replace force

* Merge MIPS into ASC providers
merge m:1 npi year using "$phase4/mips_clinician_master_panel_2017_2023$fileSuffix.dta", ///
    keep(master match) gen(_merge_mips)

rename _merge_mips mips_merge_status_asc
label values mips_merge_status_asc mips_lbl

* Save the new Phase 4 Outpatient ASC Provider Panel
save "$phase4/cms_phase4_outpatient_asc_provider.dta", replace

* ==============================================================================
* 4. GENERATE AGGREGATED FACILITY-LEVEL MIPS SCORES
* ==============================================================================
di "Aggregating Provider Scores to Facility Level..."
* Load the newly merged Phase 4 inpatient provider panel 
use "$phase4/cms_phase4_inpatient_provider.dta", clear

* Drop rows that don't have a MIPS score, or lack the weights/identifiers needed for collapse
drop if mips_merge_status_inp == 1
drop if missing(ccn)
drop if missing(tot_benes)

* Calculate the volume-weighted average MIPS scores per facility
collapse (mean) mips_final_score mips_quality_score mips_ia_score mips_pi_score mips_cost_score ///
    [aw=tot_benes], by(ccn year)

* Prefix the variables to clearly indicate they are facility-level aggregated metrics
rename mips_* fac_mips_*

* Save as a temporary crosswalk
tempfile fac_mips_scores
save `fac_mips_scores', replace

* ==============================================================================
* 5. INPATIENT FACILITY PANEL MERGE
* ==============================================================================
di "Merging Aggregated Scores into Facility Panel..."
use "$phase3/cms_phase3_inpatient_facility.dta", clear

* Ensure ccn is a string to match the collapsed crosswalk
capture tostring ccn, replace force

* Merge the aggregated scores into the master hospital panel
merge 1:1 ccn year using `fac_mips_scores', keep(master match) gen(_merge_fac_mips)

rename _merge_fac_mips mips_merge_status_fac
label define fac_mips_lbl 1 "No Affiliated MIPS Providers" 3 "Has MIPS Providers"
label values mips_merge_status_fac fac_mips_lbl

* Save the final Phase 4 Inpatient Facility Panel
save "$phase4/cms_phase4_inpatient_facility.dta", replace

di "========================================"
di "   Phase 4 Integration Complete!"
di "========================================"
log close
