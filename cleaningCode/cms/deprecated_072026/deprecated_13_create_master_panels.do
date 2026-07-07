*===============================================================================
* SCRIPT: 14_create_master_panels_v14.do
* PURPOSE: Final Master Panel Assembler.
* FIX: Natively injects fac_ prefixed facility-level means into the Provider Panel.
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
* STEP 2: PREPARE CLINICAL MEASURES
*-------------------------------------------------------------------------------
display "Step 2: Importing Python Measures..."
import delimited "$outputRoot/cleaned_data/cms_aggregated_clinical_measures.csv", clear
tostring npi, replace
replace npi = strtrim(npi)
destring year, replace

gen partd_generic_rate = 1 - (tot_brand_clms / tot_partd_clms)
gen partd_high_cost_rate = partd_empirical_high_cost_claims / tot_partd_clms
gen partd_opioid_rate = partd_opioid_strong_claims / partd_opioid_claims
gen svc_em_upcode_rate = svc_em_high_intensity / svc_em_total
gen svc_img_adv_rate = svc_imaging_advanced / svc_imaging_total

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
* STEP 4: CREATE BASE PROVIDER PANEL 
*-------------------------------------------------------------------------------
display "Step 4: Merging Base Provider Data..."

use `cms_volume', clear
* Left Join the clinical measures so non-prescribing doctors stay in the panel
merge 1:1 npi year using `clinical_measures', keep(master match) nogenerate
* Left Join the demographics
merge 1:1 npi year using `npi_demos', keep(master match) nogenerate

gen wterm_generic = partd_generic_rate * tot_benes
gen wterm_opioid  = partd_opioid_rate * tot_benes
gen wterm_highcost= partd_high_cost_rate * tot_benes
gen wterm_upcode  = svc_em_upcode_rate * tot_benes
gen wterm_img_adv = svc_img_adv_rate * tot_benes
gen wterm_risk    = bene_avg_risk_scre * tot_benes

gen is_male = (gender == "M")
gen is_female = (gender == "F")

gen grad_decade = .
replace grad_decade = 1970 if grad_year < 1980 & !missing(grad_year)
replace grad_decade = 1980 if grad_year >= 1980 & grad_year < 1990
replace grad_decade = 1990 if grad_year >= 1990 & grad_year < 2000
replace grad_decade = 2000 if grad_year >= 2000 & grad_year < 2010
replace grad_decade = 2010 if grad_year >= 2010 & grad_year < 2020
replace grad_decade = 2020 if grad_year >= 2020 & !missing(grad_year)

label define decade_lbl 1970 "Pre-1980" 1980 "1980s" 1990 "1990s" 2000 "2000s" 2010 "2010s" 2020 "2020s"
label values grad_decade decade_lbl

gen grad_pre_1980 = (grad_year < 1980) if !missing(grad_year)
gen grad_1980s    = (grad_year >= 1980 & grad_year < 1990) if !missing(grad_year)
gen grad_1990s    = (grad_year >= 1990 & grad_year < 2000) if !missing(grad_year)
gen grad_2000s    = (grad_year >= 2000 & grad_year < 2010) if !missing(grad_year)
gen grad_2010s    = (grad_year >= 2010 & grad_year < 2020) if !missing(grad_year)
gen grad_2020s    = (grad_year >= 2020) if !missing(grad_year)

order npi year last_name first_name gender grad_year grad_decade ///
      cms_specialty affil_primary_spec credential ///
      city cms_state cms_zip affil_state affil_zip ///
      tot_benes tot_srvcs tot_sbmtd_chrg ///
      bene_avg_risk_scre bene_avg_age

* Save as a temporary base panel
save "$phase1/cms_master_provider_base.dta", replace
display "  > Saved Base Provider Panel."

*-------------------------------------------------------------------------------
* STEP 5: CREATE FACILITY MASTER PANEL (PREFIXED WITH FAC_)
*-------------------------------------------------------------------------------
display "Step 5: Creating Facility Panel..."

use `npi_ccn_link', clear
merge m:1 npi year using "$phase1/cms_master_provider_base.dta", keep(match) nogenerate

collapse (mean) fac_mean_generic_rate=partd_generic_rate ///
                fac_mean_opioid_rate=partd_opioid_rate ///
                fac_mean_highcost_rate=partd_high_cost_rate ///
                fac_mean_upcode_rate=svc_em_upcode_rate ///
                fac_mean_img_adv_rate=svc_img_adv_rate ///
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
                fac_doc_count=tot_partd_clms ///
                wterm_generic wterm_opioid wterm_highcost wterm_upcode wterm_img_adv wterm_risk, ///
         by(ccn year)

gen fac_wgt_generic_rate  = wterm_generic / fac_tot_benes
gen fac_wgt_opioid_rate   = wterm_opioid / fac_tot_benes
gen fac_wgt_highcost_rate = wterm_highcost / fac_tot_benes
gen fac_wgt_upcode_rate   = wterm_upcode / fac_tot_benes
gen fac_wgt_img_adv_rate  = wterm_img_adv / fac_tot_benes
replace fac_avg_risk_score = wterm_risk / fac_tot_benes

* Drop the temporary weighting terms so they don't clutter the final panel
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

* Merge the newly created facility means directly into the provider panel
merge m:1 ccn year using "$phase1/cms_master_facility_panel.dta", keep(master match) nogenerate

save "$phase1/cms_master_provider_panel.dta", replace
display "  > Saved Ultimate Provider Panel."
