*===============================================================================
* SCRIPT: 02_polish_and_publish.do
* PURPOSE: Finalizes the 4 Master Datasets for public distribution and analysis.
*===============================================================================
clear

global component "general"
global script_name "02_polish_and_publish"


include "C:/Users/omarf/Dropbox/personal_files_omar_farrag/Research/general_cms_data/cleaningCode/00_initialize.do"

capture mkdir "$projectRoot/publishable_data"
local outDir "$projectRoot/publishable_data"

display as text "=== STARTING FINAL DATA POLISH & PUBLISH ==="

* Define the standard lists of variables to process
local encode_vars "cms_specialty affil_primary_spec credential cms_state affil_state entity_type gender hosp_type ownership emergency_services accepts_assignment county secondary_specialty_1 secondary_specialty_2 secondary_specialty_3 secondary_specialty_4"
local string_vars "city cms_zip affil_zip all_secondary_specialties"

* Define the 4 Terminal Nodes and their new polished names
local file1 "$phase4/cms_phase4_inpatient_provider$fileSuffix.dta"
local name1 "master_provider_inpatient_2013_2023.dta"

local file2 "$phase4/cms_phase4_outpatient_asc_provider.dta"
local name2 "master_provider_outpatient_asc_2015_2023.dta"

local file3 "$phase4/cms_phase4_inpatient_facility.dta"
local name3 "master_facility_inpatient_2013_2023.dta"

local file4 "$phase3/cms_phase3_outpatient_asc_facility.dta"
local name4 "master_facility_outpatient_asc_2015_2024.dta"

* Loop through all 4 Terminal Nodes
local i = 1
foreach f in "`file1'" "`file2'" "`file3'" "`file4'" {
    
    capture confirm file "`f'"
    if _rc == 0 {
        display "Processing: `f'..."
        use "`f'", clear
        
        * 1. Drop lingering merge artifacts
        capture drop _merge
        
        * 2. Fix the num_group_members variable
        capture confirm variable num_group_members
        if _rc == 0 {
            destring num_group_members, replace force
        }
        
        * 3. Clean and standardize all geographic and free-text strings
        foreach v of local string_vars {
            capture confirm variable `v'
            if _rc == 0 {
                capture tostring `v', replace force
                replace `v' = strtrim(strupper(`v'))
            }
        }
        
        * 4. Clean, standardize, and ENCODE all categorical variables
        foreach v of local encode_vars {
            capture confirm variable `v'
            if _rc == 0 {
                * Force to string if it somehow isn't
                capture tostring `v', replace force
                
                * Trim spaces and make all uppercase to fix fragmentation
                replace `v' = strtrim(strupper(`v'))
                
                * Encode into high-speed integers with value labels
                encode `v', gen(`v'_id)
                
                * Drop the old string variable and rename the encoded one
                drop `v'
                rename `v'_id `v'
            }
        }
        
        * 5. Final Compression to minimize file size
        compress
        
        * 6. Save to the Publishable Directory
        local current_name "name`i'"
        save "`outDir'/``current_name''", replace
        display "  > Saved as: ``current_name''"
    }
    else {
        display as error "  > FILE NOT FOUND: `f'"
    }
    local i = `i' + 1
}

display "=== POLISHING COMPLETE. DATASETS ARE READY FOR ANALYSIS! ==="