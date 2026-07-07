import pandas as pd
import numpy as np
import os
import glob
import time

# --- 1. SETUP PATHS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..",".."))

partd_dir = os.path.join(project_root, "cms", "partD", "dta", "harmonized")
service_dir = os.path.join(project_root, "cms", "by_provider_service", "dta", "harmonized")
dict_dir = os.path.join(project_root, "dictionaries_and_crosswalks")
output_dir = os.path.join(project_root, "outputs_while_cleaning", "cleaned_data")

if not os.path.exists(output_dir): os.makedirs(output_dir)

# --- 2. WORKER FUNCTIONS ---

def process_partd_file(f, map_partd, empirical_lookup):
    fname = os.path.basename(f)
    print(f"  [Part D] Starting {fname}...")
    start = time.time()
    
    try:
        df = pd.read_stata(f)
        if 'npi' in df.columns:
            df['npi'] = df['npi'].astype(str).str.replace(r'\.0$', '', regex=True)
        else:
            return None
            
        if 'generic_name' in df.columns:
            df['generic_name'] = df['generic_name'].astype(str).str.upper().str.strip()
        else:
            print(f"  [Part D] WARNING: 'generic_name' missing in {fname}")
            return None

        # ---> THE BRAND LOGIC <---
        if 'brnd_name' in df.columns:
            df['brnd_name'] = df['brnd_name'].astype(str).str.upper().str.strip()
            df['is_brand'] = (df['brnd_name'] != df['generic_name']).astype(int)
        else:
            df['is_brand'] = 0

        import re
        year_match = re.search(r'(20\d{2})', fname)
        df['year'] = int(year_match.group(1)) if year_match else 9999
        
        # ---> THE GOLDEN SCHEMA: STRICT PART D PREFIXES <---
        agg_dict = {
            'npi': df['npi'],
            'year': df['year'],
            'partd_clms_total': df['tot_clms'],
            'partd_cst_total': df['tot_drug_cst'],
            'partd_clms_brand': df['tot_clms'] * df['is_brand'] 
        }
        
        # --- LENS 1: MICROSCOPE (Hypothesis-Driven Phenotypes) ---
        for key, details in map_partd.items():
            if details['category'] == 'Opioid':
                is_target = df['generic_name'].str.contains(key, na=False)
                agg_dict[f'partd_clms_opioid_{key.lower()}'] = df['tot_clms'] * is_target
            elif details['category'] == 'High-Risk':
                is_target = df['generic_name'].str.contains(key, na=False)
                agg_dict[f'partd_clms_hr_{key.lower()}'] = df['tot_clms'] * is_target

        # --- LENS 2: TELESCOPE (Empirical Thresholds) ---
        df['is_high_cost'] = df['generic_name'].map(empirical_lookup).fillna(0)
        agg_dict['partd_clms_high_cost'] = df['tot_clms'] * df['is_high_cost']
        
        grouped = pd.DataFrame(agg_dict).groupby(['npi', 'year']).sum().reset_index()
        print(f"  [Part D] Finished {fname} ({time.time() - start:.1f}s) - {len(grouped)} rows")
        return grouped
        
    except Exception as e:
        print(f"  [Part D] ERROR in {fname}: {e}")
        return None

def process_service_file(f, service_lookup, partb_lookup, rbcs_cat_dict, rbcs_subcat_dict):
    fname = os.path.basename(f)
    print(f"  [Service] Starting {fname}...")
    start = time.time()
    
    try:
        df = pd.read_stata(f)
        if 'npi' in df.columns:
            df['npi'] = df['npi'].astype(str).str.replace(r'\.0$', '', regex=True)
            
        if 'hcpcs' in df.columns:
            df['hcpcs'] = df['hcpcs'].astype(str).str.upper().str.strip()
        else:
            print(f"  [Service] WARNING: 'hcpcs' missing in {fname}")
            return None

        import re
        year_match = re.search(r'(20\d{2})', fname)
        df['year'] = int(year_match.group(1)) if year_match else 9999

        # ---> THE GOLDEN SCHEMA: STRICT PART B PREFIXES <---
        agg_dict = {
            'npi': df['npi'],
            'year': df['year'],
            'partb_srvc_total': df['tot_srvcs'],
            'partb_cst_total': df['tot_partb_cst']
        }
        
        # --- LENS 1: MICROSCOPE (Specific HCPCS Definitions) ---
        for key, details in partb_lookup.items():
            is_target = df['hcpcs'] == key
            
            if details['category'] == 'Imaging':
                agg_dict[f'partb_srvc_img_{key}'] = df['tot_srvcs'] * is_target
            elif details['category'] == 'High-Value':
                agg_dict[f'partb_srvc_hv_{key}'] = df['tot_srvcs'] * is_target
            elif details['category'] == 'Low-Value':
                agg_dict[f'partb_srvc_lv_{key}'] = df['tot_srvcs'] * is_target
            elif details['category'] == 'E&M': # ---> RESTORED E&M LOGIC
                agg_dict[f'partb_srvc_em_{key}'] = df['tot_srvcs'] * is_target

        # --- LENS 2: TELESCOPE (RBCS Taxonomy) ---
        df['rbcs_cat'] = df['hcpcs'].map(rbcs_cat_dict).fillna('Unknown')
        
        agg_dict['partb_srvc_rbcs_imaging'] = df['tot_srvcs'] * (df['rbcs_cat'] == 'Imaging')
        agg_dict['partb_srvc_rbcs_procedures'] = df['tot_srvcs'] * (df['rbcs_cat'] == 'Procedures')
        agg_dict['partb_srvc_rbcs_tests'] = df['tot_srvcs'] * (df['rbcs_cat'] == 'Tests')
        agg_dict['partb_srvc_rbcs_em'] = df['tot_srvcs'] * (df['rbcs_cat'] == 'Evaluation and Management')

        grouped = pd.DataFrame(agg_dict).groupby(['npi', 'year']).sum().reset_index()
        print(f"  [Service] Finished {fname} ({time.time() - start:.1f}s) - {len(grouped)} rows")
        return grouped
        
    except Exception as e:
        print(f"  [Service] ERROR in {fname}: {e}")
        return None

# --- 3. MAIN EXECUTION ---
if __name__ == '__main__':
    print(f"--- DUAL-LENS AGGREGATION STARTING (SEQUENTIAL MODE) ---")
    
    try:
        df_clinical_partd = pd.read_csv(os.path.join(dict_dir, "dict_partd_clinical.csv"))
        map_partd = df_clinical_partd.set_index('keyword').to_dict(orient='index')
        
        df_clinical_partb = pd.read_csv(os.path.join(dict_dir, "dict_partb_clinical.csv"))
        partb_lookup = df_clinical_partb.set_index('keyword').to_dict(orient='index')
        
        df_costs = pd.read_csv(os.path.join(dict_dir, "crosswalk_partd_empirical_costs.csv"))
        empirical_lookup = df_costs.set_index('generic_name')['is_high_cost_in_class'].to_dict()
        
        df_rbcs = pd.read_csv(os.path.join(dict_dir, "crosswalk_rbcs_services.csv"))
        rbcs_cat_dict = df_rbcs.set_index('hcpcs')['rbcs_cat'].to_dict()
        rbcs_subcat_dict = df_rbcs.set_index('hcpcs')['rbcs_subcat'].to_dict()
        
    except Exception as e:
        print(f"Dictionary Error: {e}")
        exit()

    partd_files = glob.glob(os.path.join(partd_dir, "*.dta"))
    service_files = glob.glob(os.path.join(service_dir, "*.dta"))

    print("\n--- Processing Part D (Sequential) ---")
    partd_dfs = []
    for f in partd_files:
        result = process_partd_file(f, map_partd, empirical_lookup)
        if result is not None:
            partd_dfs.append(result)

    df_partd_final = pd.concat(partd_dfs).groupby(['npi', 'year']).sum().reset_index() if partd_dfs else pd.DataFrame()
    print(f"Part D Complete. Rows: {len(df_partd_final):,}")

    print("\n--- Processing Services (Sequential) ---")
    service_dfs = []
    for f in service_files:
        result = process_service_file(f, None, partb_lookup, rbcs_cat_dict, rbcs_subcat_dict)
        if result is not None:
            service_dfs.append(result)

    df_svc_final = pd.concat(service_dfs).groupby(['npi', 'year']).sum().reset_index() if service_dfs else pd.DataFrame()
    print(f"Services Complete. Rows: {len(df_svc_final):,}")

    print("\n--- Final Merge ---")
    if not df_partd_final.empty and not df_svc_final.empty:
        df_final = pd.merge(df_partd_final, df_svc_final, on=['npi', 'year'], how='outer').fillna(0)
    elif not df_partd_final.empty:
        df_final = df_partd_final
    else:
        df_final = df_svc_final
        
    output_file = os.path.join(output_dir, "cms_aggregated_clinical_measures.csv")
    df_final.to_csv(output_file, index=False)
    print(f"SUCCESS! Master Dataset Saved to: {output_file}")
