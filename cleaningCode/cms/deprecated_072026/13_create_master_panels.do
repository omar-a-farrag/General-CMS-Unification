*===============================================================================
* SCRIPT: 13_create_master_panels.do
* PURPOSE: Final Master Panel Assembler.
* NOTES: Integrates Absolute (Systemic) and Conditional (Thesis) Clinical Lenses.
* LAST EDITED: 03-24-2026
*===============================================================================
clear

global component "cms"
global script_name "13_create_master_panels"

include "C:/Users/omarf/Dropbox/personal_files_omar_farrag/Research/general_cms_data/cleaningCode/00_initialize.do"

capture mkdir "$outputRoot/cleaned_data"

display as text "Building Master Panels (v14 - The Native Injector)..."

*-------------------------------------------------------------------------------
* STEP 1: PREPARE AFFILIATION NETWORK
*-------------------------------------------------------------------------------
display "Step 1: Loading Affiliation Data..."
clear
local facilDir "$projectRoot/cliniciansAndGroups/facilityAffiliation/dta/harmonized"
local files : dir "`facilDir'" files "*_harmonized.dta"

tempfile raw_affil
save `raw_affil', emptyok

foreach f in `files' {
    use "`facilDir'/`f'", clear
    capture tostring zip_code, replace
    capture tostring group_pac_id, replace
    capture tostring num_group_members, replace
    append using `raw_affil'
    save `raw_affil', replace
}
use `raw_affil', clear

* A. Unique Affiliation Demographics
preserve
    keep npi year gender grad_year credential ///
         primary_specialty secondary_specialty_* all_secondary_specialties ///
         group_pac_id num_group_members state zip_code ///
         accepts_assignment quality_participation ehr_participation heart_participation
    rename primary_specialty affil_primary_spec
    rename state affil_state
    rename zip_code affil_zip
    replace gender = upper(gender)
    replace gender = "M" if gender == "MALE"
    replace gender = "F" if gender == "FEMALE"
    destring grad_year, replace force
    replace grad_year = . if grad_year < 1920 | grad_year > 2030
    duplicates drop npi year, force
    tempfile npi_demos
    save `npi_demos'
restore

* B. Network Link (NPI-CCN)
keep npi year ccn
drop if ccn == ""
capture tostring npi, replace force
replace npi = strtrim(npi)
capture tostring ccn, replace force
replace ccn = strtrim(ccn)
duplicates drop npi year ccn, force
tempfile npi_ccn_link
save `npi_ccn_link'

*-------------------------------------------------------------------------------
* STEP 2: PREPARE CLINICAL MEASURES (THE 8 GOLDEN SCHEMA RATES)
*-------------------------------------------------------------------------------
display "Step 2: Importing Python Measures..."
import delimited "$outputRoot/cleaned_data/cms_aggregated_clinical_measures.csv", clear
tostring npi, replace
replace npi = strtrim(npi)
destring year, replace

* --- ABSOLUTE RATES (Systemic Telescope) ---
* 1. Part D: Generic & Cost Agnosticism 
gen partd_generic_rate = 1 - (partd_clms_brand / partd_clms_total)
gen partd_high_cost_rate = partd_clms_high_cost / partd_clms_total

* 2. Part D: Opioid Absolute Reliance 
egen partd_clms_opioid_all = rowtotal(partd_clms_opioid_*)
gen partd_opioid_rate = partd_clms_opioid_all / partd_clms_total

* 3. Part B: Low-Value Overtreatment (Choosing Wisely)
egen partb_srvc_low_value_all = rowtotal(partb_srvc_lv_*)
gen partb_low_value_rate = partb_srvc_low_value_all / partb_srvc_total

* 4. Part B: Imaging Absolute Reliance
egen partb_srvc_img_adv_all = rowtotal(partb_srvc_img_*)
gen partb_imaging_adv_rate = partb_srvc_img_adv_all / partb_srvc_total

* --- CONDITIONAL RATES (Original Thesis Microscope) ---
* 5. Part D: Opioid Intensity (Strong Schedule II vs All Opioids)
egen partd_clms_opioid_strong = rowtotal(partd_clms_opioid_oxycodone partd_clms_opioid_hydrocodone partd_clms_opioid_fentanyl partd_clms_opioid_hydromorphone partd_clms_opioid_morphine partd_clms_opioid_methadone partd_clms_opioid_oxymorphone)
gen partd_opioid_strong_rate = partd_clms_opioid_strong / partd_clms_opioid_all

* 6. Part B: E&M Upcoding (Revenue-Seeking Intensity)
egen partb_srvc_em_total = rowtotal(partb_srvc_em_99212 partb_srvc_em_99213 partb_srvc_em_99214 partb_srvc_em_99215)
egen partb_srvc_em_high  = rowtotal(partb_srvc_em_99214 partb_srvc_em_99215)
gen partb_em_upcode_rate = partb_srvc_em_high / partb_srvc_em_total

* 7. Part B: Imaging Intensity (Advanced Imaging vs All Imaging)
* Leverages the RBCS taxonomy for the denominator
gen partb_imaging_cond_rate = partb_srvc_img_adv_all / partb_srvc_rbcs_imaging

* Handle division by zero & out-of-bounds rates
foreach v of varlist *_rate {
    replace `v' = . if `v' < 0 | `v' > 1
}

tempfile clinical_measures
save `clinical_measures'

*-------------------------------------------------------------------------------
* STEP 3: PREPARE RICH PROVIDER SUMMARY
*-------------------------------------------------------------------------------
display "Step 3: Importing CMS Provider Summary..."
clear
local summaryDir "$cmsRoot/by_provider/dta/harmonized"
local files : dir "`summaryDir'" files "*_harmonized.dta"

tempfile master_vol
save `master_vol', emptyok

foreach f in `files' {
    use "`summaryDir'/`f'", clear
    tostring npi, replace
    
    capture rename nppes_provider_last_org_name last_name
    capture rename nppes_provider_first_name first_name
    capture rename nppes_provider_city city
    capture rename nppes_provider_state cms_state
    capture rename state cms_state
    capture rename rndrng_prvdr_st1 cms_address
    capture rename nppes_provider_zip cms_zip
    capture rename zip_code cms_zip
    capture rename provider_type cms_specialty
    capture rename specialty cms_specialty
    capture rename tot_submitted_chrg_amt tot_sbmtd_chrg
    capture rename tot_mdcr_alowd_amt     tot_alowd_amt
    capture rename tot_mdcr_pymt_amt      tot_pymt_amt
    capture rename bene_race_b_cnt        bene_race_black_cnt
    capture rename bene_race_w_cnt        bene_race_wht_cnt
    capture rename bene_race_h_cnt        bene_race_hspnc_cnt
    capture rename bene_race_o_cnt        bene_race_othr_cnt
    
    capture rename bene_cc_depression     temp_depr_pct
    capture rename bene_cc_depr           temp_depr_pct
    capture rename bene_cc_bh_depress_v1_pct temp_depr_pct
    capture rename bene_cc_diabetes       temp_diab_pct
    capture rename bene_cc_diab           temp_diab_pct
    capture rename bene_cc_ph_diabetes_v2_pct temp_diab_pct
    
    append using `master_vol'
    save `master_vol', replace
}

use `master_vol', clear
replace npi = strtrim(npi)
duplicates drop npi year, force
destring year, replace
capture destring tot_benes, replace force

foreach cond in depr diab {
    capture confirm variable temp_`cond'_pct
    if !_rc {
        capture destring temp_`cond'_pct, replace force
        gen bene_cc_`cond' = (temp_`cond'_pct / 100) * tot_benes
        replace bene_cc_`cond' = round(bene_cc_`cond')
    }
    else {
        gen bene_cc_`cond' = 0
    }
}
foreach var in bene_race_black_cnt bene_race_hspnc_cnt bene_dual_cnt tot_benes tot_srvcs tot_sbmtd_chrg {
    capture confirm variable `var'
    if _rc {
        gen `var' = 0
    }
}

keep npi year entity_type last_name first_name city cms_state cms_zip cms_specialty ///
     tot_benes tot_srvcs tot_sbmtd_chrg tot_alowd_amt tot_pymt_amt ///
     drug_* med_* bene_avg_age bene_age_* bene_feml_cnt bene_male_cnt ///
     bene_race_* bene_dual_cnt bene_ndual_cnt bene_avg_risk_scre ///
     bene_cc_* 
	 
tempfile cms_volume
save `cms_volume'

*-------------------------------------------------------------------------------
* STEP 4: MERGE PROVIDER DATA & DEMOGRAPHICS
*-------------------------------------------------------------------------------
display "Step 4: Merging Provider Base..."

use `cms_volume', clear
merge 1:1 npi year using `clinical_measures', keep(master match) nogenerate
merge 1:1 npi year using `npi_demos', keep(master match) nogenerate

gen is_male = (gender == "M")
gen is_female = (gender == "F")

gen grad_pre_1980 = (grad_year < 1980)
gen grad_1980s = (grad_year >= 1980 & grad_year <= 1989)
gen grad_1990s = (grad_year >= 1990 & grad_year <= 1999)
gen grad_2000s = (grad_year >= 2000 & grad_year <= 2009)
gen grad_2010s = (grad_year >= 2010 & grad_year <= 2019)
gen grad_2020s = (grad_year >= 2020 & grad_year <= 2029)

save "$phase1/cms_master_provider_base.dta", replace
display "  > Saved Provider Base."

*-------------------------------------------------------------------------------
* STEP 5: CREATE FACILITY MASTER PANEL (PREFIXED WITH FAC_)
*-------------------------------------------------------------------------------
display "Step 5: Creating Facility Panel..."

use `npi_ccn_link', clear
merge m:1 npi year using "$phase1/cms_master_provider_base.dta", keep(match) nogenerate

bysort ccn year: egen fac_tot_benes_base = sum(tot_benes)

* ---> WEIGHTING MATH: Match the rate to its specific clinical denominator <---
gen wterm_generic      = partd_generic_rate * partd_clms_total
gen wterm_highcost     = partd_high_cost_rate * partd_clms_total
gen wterm_opioid_abs   = partd_opioid_rate * partd_clms_total
gen wterm_opioid_cond  = partd_opioid_strong_rate * partd_clms_opioid_all

gen wterm_low_value    = partb_low_value_rate * partb_srvc_total
gen wterm_img_abs      = partb_imaging_adv_rate * partb_srvc_total
gen wterm_img_cond     = partb_imaging_cond_rate * partb_srvc_rbcs_imaging
gen wterm_em_upcode    = partb_em_upcode_rate * partb_srvc_em_total

gen wterm_risk         = bene_avg_risk_scre * fac_tot_benes_base

* ---> COLLAPSE TO HOSPITAL LEVEL <---
collapse (mean) fac_mean_generic_rate=partd_generic_rate ///
                fac_mean_highcost_rate=partd_high_cost_rate ///
                fac_mean_opioid_rate=partd_opioid_rate ///
                fac_mean_opioid_strong_rate=partd_opioid_strong_rate ///
                fac_mean_low_value_rate=partb_low_value_rate ///
                fac_mean_img_adv_rate=partb_imaging_adv_rate ///
                fac_mean_img_cond_rate=partb_imaging_cond_rate ///
                fac_mean_em_upcode_rate=partb_em_upcode_rate ///
                fac_avg_risk_score=bene_avg_risk_scre ///
                fac_prop_male_docs=is_male ///
                fac_prop_female_docs=is_female ///
                fac_prop_grad_pre1980=grad_pre_1980 ///
                fac_prop_grad_1980s=grad_1980s ///
                fac_prop_grad_1990s=grad_1990s ///
                fac_prop_grad_2000s=grad_2000s ///
                fac_prop_grad_2010s=grad_2010s ///
                fac_prop_grad_2020s=grad_2020s ///
         (sum)  fac_tot_benes=tot_benes ///
                fac_tot_srvcs=tot_srvcs ///
                fac_tot_chrg=tot_sbmtd_chrg ///
                fac_bene_feml=bene_feml_cnt ///
                fac_bene_male=bene_male_cnt ///
                fac_bene_black=bene_race_black_cnt ///
                fac_bene_hspnc=bene_race_hspnc_cnt ///
                fac_bene_dual=bene_dual_cnt ///
                fac_cc_depression=bene_cc_depr ///
                fac_cc_diabetes=bene_cc_diab ///
                fac_doc_count=partd_clms_total /// 
                fac_partd_clms_total=partd_clms_total ///
                fac_partd_clms_opioid_all=partd_clms_opioid_all ///
                fac_partb_srvc_total=partb_srvc_total ///
                fac_partb_srvc_rbcs_imaging=partb_srvc_rbcs_imaging ///
                fac_partb_srvc_em_total=partb_srvc_em_total ///
                wterm_*, ///
         by(ccn year)

* ---> CALCULATE FINAL WEIGHTED FACILITY RATES <---
gen fac_wgt_generic_rate      = wterm_generic / fac_partd_clms_total
gen fac_wgt_highcost_rate     = wterm_highcost / fac_partd_clms_total
gen fac_wgt_opioid_rate       = wterm_opioid_abs / fac_partd_clms_total
gen fac_wgt_opioid_strong_rate = wterm_opioid_cond / fac_partd_clms_opioid_all

gen fac_wgt_low_value_rate    = wterm_low_value / fac_partb_srvc_total
gen fac_wgt_img_adv_rate      = wterm_img_abs / fac_partb_srvc_total
gen fac_wgt_img_cond_rate     = wterm_img_cond / fac_partb_srvc_rbcs_imaging
gen fac_wgt_em_upcode_rate    = wterm_em_upcode / fac_partb_srvc_em_total

replace fac_avg_risk_score = wterm_risk / fac_tot_benes

* Drop the temporary weighting terms
drop wterm_*

save "$phase1/cms_master_facility_panel.dta", replace
display "  > Saved Facility Panel."

*-------------------------------------------------------------------------------
* STEP 6: EXPAND PROVIDER PANEL & INJECT FACILITY MEANS
*-------------------------------------------------------------------------------
display "Step 6: Injecting Facility Rates into Provider Panel..."

use "$phase1/cms_master_provider_base.dta", clear

* Expand panel to NPI-CCN-Year level (so each provider gets their facility's rates)
merge 1:m npi year using `npi_ccn_link', keep(master match) nogenerate

* Left Join the Facility Panel
merge m:1 ccn year using "$phase1/cms_master_facility_panel.dta", keep(master match) nogenerate

save "$phase1/cms_master_provider_panel.dta", replace
display "  > Saved Provider Panel with Network Integration."

display as text "=== SUCCESS: MASTER PANELS ASSEMBLED ==="
