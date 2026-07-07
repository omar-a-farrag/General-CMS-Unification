import pandas as pd
import numpy as np
import os
import glob
import time
from multiprocessing import Pool, cpu_count
from functools import partial

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
    """Worker function to process a single Part D file."""
    fname = os.path.basename(f)
    print(f"  [Part D] Starting {fname}...")
    start = time.time()
    
    try:
        df = pd.read_stata(f)
        if 'npi' in df.columns:
            df['npi'] = df['npi'].astype(str).str.replace(r'\.0$', '', regex=True)
        else:
            return None
            
        df['generic_name'] = df['generic_name'].astype(str).str.upper().str.strip()
        
        # Determine Brand Fill (Telescope Metric)
        if 'brnd_name' in df.columns:
            df['brnd_name'] = df['brnd_name'].astype(str).str.upper().str.strip()
            df['is_brand'] = ((df['brnd_name'] != df['generic_name']) & (df['brnd_name'] != '')).astype(int)
        else:
            df['is_brand'] = 0

        # Empirical High Cost Lookup (Telescope Metric)
        df['is_high_cost_empirical'] = df['generic_name'].map(empirical_lookup).fillna(0)
        
        # Clinical Dictionary Flags (Microscope Metric)
        cols = ['is_opioid', 'is_opioid_strong', 'is_antibiotic', 'is_antibiotic_broad', 
                'is_muscle_relaxant', 'is_benzo', 'is_cynical_high_cost']
        for c in cols: df[c] = 0
        
        for _, row in map_partd.iterrows():
            mask = df['generic_name'].str.contains(row['keyword'], na=False, regex=False)
            if not mask.any(): continue
            
            if row['category'] == 'Opioid':
                df.loc[mask, 'is_opioid'] = 1
                if 'Strong' in row['sub_category']: df.loc[mask, 'is_opioid_strong'] = 1
            if row['category'] == 'Antibiotic':
                df.loc[mask, 'is_antibiotic'] = 1
                if 'Broad' in row['sub_category']: df.loc[mask, 'is_antibiotic_broad'] = 1
            if row['category'] == 'Muscle Relaxant': df.loc[mask, 'is_muscle_relaxant'] = 1
            if row['category'] == 'Sedative' and 'Benzodiazepine' in row['sub_category']: df.loc[mask, 'is_benzo'] = 1
            if row['high_cost'] == 1: df.loc[mask, 'is_cynical_high_cost'] = 1

        weight = df['tot_clms'].fillna(0) if 'tot_clms' in df.columns else 1
        
        agg_dict = {
            # --- TELESCOPE (Systematic) ---
            'partd_total_claims': weight,
            'partd_brand_claims': df['is_brand'] * weight,
            'partd_empirical_high_cost_claims': df['is_high_cost_empirical'] * weight,
            
            # --- MICROSCOPE (Clinical) ---
            'partd_opioid_claims': df['is_opioid'] * weight,
            'partd_opioid_strong_claims': df['is_opioid_strong'] * weight,
            'partd_antibiotic_claims': df['is_antibiotic'] * weight,
            'partd_antibiotic_broad_claims': df['is_antibiotic_broad'] * weight,
            'partd_muscle_relaxant_claims': df['is_muscle_relaxant'] * weight,
            'partd_benzo_claims': df['is_benzo'] * weight,
            'partd_cynical_high_cost_claims': df['is_cynical_high_cost'] * weight
        }
        
        grouped = pd.DataFrame(agg_dict).groupby([df['npi'], df['year']]).sum().reset_index()
        
        print(f"  [Part D] Finished {fname} ({time.time() - start:.1f}s)")
        return grouped

    except Exception as e:
        print(f"  [Part D] ERROR in {fname}: {e}")
        return None

def process_service_file(f, service_lookup, partb_lookup, rbcs_cat_dict, rbcs_subcat_dict):
    """Worker function to process a single Service file."""
    fname = os.path.basename(f)
    print(f"  [Service] Starting {fname}...")
    start = time.time()
    
    try:
        df = pd.read_stata(f)
        if 'npi' in df.columns:
            df['npi'] = df['npi'].astype(str).str.replace(r'\.0$', '', regex=True)
        else:
            return None

        if 'hcpcs' not in df.columns:
            if 'hcpcs_cd' in df.columns: df.rename(columns={'hcpcs_cd': 'hcpcs'}, inplace=True)
            elif 'hcpcs_code' in df.columns: df.rename(columns={'hcpcs_code': 'hcpcs'}, inplace=True)
            else: return None

        df['hcpcs'] = df['hcpcs'].astype(str).str.upper().str.strip()
        
        # --- TELESCOPE: RBCS Mapping ---
        df['rbcs_cat'] = df['hcpcs'].map(rbcs_cat_dict).fillna('Unknown')
        df['rbcs_subcat'] = df['hcpcs'].map(rbcs_subcat_dict).fillna('Unknown')
        
        # --- MICROSCOPE: Dictionary Lookups ---
        em_high = set(k for k,v in service_lookup.items() if v['sub_category'] in ['High Intensity', 'ED Visit High'])
        mri_spine = set(k for k,v in service_lookup.items() if v['sub_category'] == 'Low Value Spine')
        cataract = set(k for k,v in service_lookup.items() if v['category'] == 'Procedure' and 'Cataract' in str(v['desc']))
        svc_high_cost = set(k for k,v in service_lookup.items() if v['high_cost'] == 1)
        
        partb_all = set(partb_lookup.keys())
        partb_toradol = set(k for k,v in partb_lookup.items() if 'Toradol' in str(v['desc']))
        partb_visco = set(k for k,v in partb_lookup.items() if v['category'] == 'Viscosupplement')
        partb_antibiotic = set(k for k,v in partb_lookup.items() if v['category'] == 'Antibiotic')
        partb_high_cost = set(k for k,v in partb_lookup.items() if v['high_cost'] == 1)

        if 'tot_srvcs' in df.columns: weight = df['tot_srvcs'].fillna(0)
        elif 'tot_benes' in df.columns: weight = df['tot_benes'].fillna(0)
        else: weight = 1

        # Use Series.where(condition, other) to apply weights rapidly
        agg_dict = {
            # --- TELESCOPE (RBCS Broad Metrics) ---
            'svc_total_lines': weight,
            'svc_em_total': weight.where(df['rbcs_cat'] == 'E&M', 0),
            'svc_imaging_total': weight.where(df['rbcs_cat'] == 'Imaging', 0),
            'svc_imaging_advanced': weight.where(df['rbcs_subcat'].isin(['CT Scan', 'Magnetic Resonance', 'Nuclear']), 0),
            'svc_procedure_total': weight.where(df['rbcs_cat'] == 'Procedure', 0),
            'svc_test_total': weight.where(df['rbcs_cat'] == 'Test', 0),
            
            # --- MICROSCOPE (Clinical Targeted Metrics) ---
            'svc_em_high_intensity': weight.where(df['hcpcs'].isin(em_high), 0),
            'svc_mri_spine': weight.where(df['hcpcs'].isin(mri_spine), 0),
            'svc_cataract': weight.where(df['hcpcs'].isin(cataract), 0),
            'svc_cynical_high_cost': weight.where(df['hcpcs'].isin(svc_high_cost), 0),
            
            # --- PART B (Clinic Administered Drugs) ---
            'partb_total_claims': weight.where(df['hcpcs'].isin(partb_all), 0),
            'partb_toradol': weight.where(df['hcpcs'].isin(partb_toradol), 0),
            'partb_visco_knee': weight.where(df['hcpcs'].isin(partb_visco), 0),
            'partb_antibiotic': weight.where(df['hcpcs'].isin(partb_antibiotic), 0),
            'partb_cynical_high_cost': weight.where(df['hcpcs'].isin(partb_high_cost), 0)
        }

        grouped = pd.DataFrame(agg_dict).groupby([df['npi'], df['year']]).sum().reset_index()
        
        print(f"  [Service] Finished {fname} ({time.time() - start:.1f}s)")
        return grouped

    except Exception as e:
        print(f"  [Service] ERROR in {fname}: {e}")
        return None

# --- 3. MAIN EXECUTION BLOCK ---
if __name__ == '__main__':
    print(f"--- DUAL-LENS AGGREGATION STARTING ---")
    print(f"CPUs Available: {cpu_count()}")
    
    try:
        # Load Microscope Dicts
        df_map_drug = pd.read_csv(os.path.join(dict_dir, "drug_class_map.csv"))
        df_map_service = pd.read_csv(os.path.join(dict_dir, "service_class_map.csv"))
        map_partd = df_map_drug[df_map_drug['type'] == 'Part D'].copy()
        partb_lookup = df_map_drug[df_map_drug['type'] == 'Part B'].set_index('keyword')[['category', 'sub_category', 'high_cost', 'desc']].to_dict('index')
        service_lookup = df_map_service.set_index('hcpcs')[['category', 'sub_category', 'high_cost', 'desc']].to_dict('index')
        
        # Load Telescope Dicts
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
    
    n_cores = max(1, int(cpu_count() * 0.75))
    print(f"Using {n_cores} workers.")

    # 1. Process Part D
    print("\n--- Processing Part D (Parallel) ---")
    with Pool(n_cores) as pool:
        partd_dfs = pool.map(partial(process_partd_file, map_partd=map_partd, empirical_lookup=empirical_lookup), partd_files)
    
    df_partd_final = pd.concat([d for d in partd_dfs if d is not None]).groupby(['npi', 'year']).sum().reset_index()
    print(f"Part D Complete. Rows: {len(df_partd_final):,}")

    # 2. Process Services
    print("\n--- Processing Services (Parallel) ---")
    with Pool(n_cores) as pool:
        service_dfs = pool.map(partial(process_service_file, service_lookup=service_lookup, partb_lookup=partb_lookup, 
                                       rbcs_cat_dict=rbcs_cat_dict, rbcs_subcat_dict=rbcs_subcat_dict), service_files)
        
    df_svc_final = pd.concat([d for d in service_dfs if d is not None]).groupby(['npi', 'year']).sum().reset_index()
    print(f"Services Complete. Rows: {len(df_svc_final):,}")

    # 3. Merge
    print("\n--- Final Merge ---")
    df_final = pd.merge(df_partd_final, df_svc_final, on=['npi', 'year'], how='outer').fillna(0)
    
    output_file = os.path.join(output_dir, "cms_aggregated_clinical_measures.csv")
    df_final.to_csv(output_file, index=False)
    print(f"SUCCESS! Master Dataset Saved to: {output_file}")