import os
import pandas as pd
import numpy as np
import re
import warnings

warnings.filterwarnings("ignore")

# --- SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..")) 
hcahps_dir = os.path.join(project_root, "hcahps")
output_dir = os.path.join(hcahps_dir, "harmonized")

if not os.path.exists(output_dir): os.makedirs(output_dir)

print("=== STARTING OUTPATIENT QUALITY HARVESTER (V9: EXTENDED DEMOGRAPHICS) ===")

def clean_col(c): 
    return str(c).lower().replace(' ', '').replace('_', '').replace('-', '').replace('*', '')

def clean_ccn(series):
    return series.astype(str).str.replace("'", "").str.split('.').str[0].str.zfill(6)

def get_year_from_folder(folder_name):
    match = re.search(r'20[0-9]{2}', folder_name)
    return int(match.group(0)) if match else None

def clean_cms_score(val):
    if pd.isna(val): return np.nan
    s = str(val).lower().strip()
    if s in ['not available', 'n/a', 'not applicable', 'no data']: return np.nan
    if 'out of' in s: return float(s.split('out of')[0].strip())
    if s == 'below average': return 1.0
    if s == 'average': return 2.0
    if s == 'above average': return 3.0
    s = re.sub(r'[,\%\$\s]', '', s)
    try: return float(s)
    except: return np.nan

def standardize_measure_id(val):
    s = str(val).upper()
    match = re.search(r'(OP|ASC)[^0-9]*([0-9]+)([A-Z]*)', s)
    if match: return f"{match.group(1)}_{int(match.group(2))}{match.group(3)}"
    return s

folders = [f for f in os.listdir(hcahps_dir) if os.path.isdir(os.path.join(hcahps_dir, f)) and ('hcahps20' in f.lower() or 'hchaps20' in f.lower())]
folders.sort()

master_hopd = []
master_asc = []

for folder in folders:
    folder_year = get_year_from_folder(folder)
    if not folder_year: continue
    exp_year = folder_year - 1
    
    print(f"\nProcessing {folder} (Exp Year: {exp_year})...")
    folder_path = os.path.join(hcahps_dir, folder)
    
    hopd_year_df = pd.DataFrame(columns=['ccn'])
    asc_year_df = pd.DataFrame(columns=['asc_id'])
    
    files = os.listdir(folder_path)
    csv_files = [f for f in files if f.endswith('.csv') and 'state' not in f.lower() and 'national' not in f.lower()]
    
    hopd_found = False
    asc_found = False
    
    for f in csv_files:
        f_clean = f.lower().replace(' ', '').replace('_', '').replace('-', '')
        try:
            try: df_peek = pd.read_csv(os.path.join(folder_path, f), nrows=2, encoding='utf-8-sig')
            except UnicodeDecodeError: df_peek = pd.read_csv(os.path.join(folder_path, f), nrows=2, encoding='cp1252')
            
            raw_cols = df_peek.columns.tolist()
            cols = [clean_col(c) for c in raw_cols]
            
            id_col_raw = next((c for c in raw_cols if clean_col(c) in ['facilityid', 'providerid', 'providernumber', 'ccn', 'ascid', 'asc_id']), None)
            
            if not id_col_raw: continue
            
            try: df = pd.read_csv(os.path.join(folder_path, f), encoding='utf-8-sig')
            except: df = pd.read_csv(os.path.join(folder_path, f), encoding='cp1252')
            
            df.columns = cols
            
            # ---------------------------------------------------------
            # FACILITY TYPE ROUTING 
            # ---------------------------------------------------------
            is_asc_file = False
            if 'asc' in str(id_col_raw).lower() or 'asc' in f_clean or 'ambulatory' in f_clean:
                is_asc_file = True
            elif any('asc' in c and 'rate' in c for c in cols):
                is_asc_file = True
                
            id_target = 'asc_id' if is_asc_file else 'ccn'
            
            df[id_target] = clean_ccn(df[clean_col(id_col_raw)])
            if is_asc_file: df['asc_id'] = df['asc_id'].str.upper()

            # =========================================================
            # 0. DEMOGRAPHICS SNIFFER (ZIP, City, State)
            # =========================================================
            demo_mapping = {}
            for c in cols:
                if 'zip' in c and 'zipcode' not in demo_mapping.values(): demo_mapping[c] = 'zipcode'
                elif 'city' in c and 'city' not in demo_mapping.values(): demo_mapping[c] = 'city'
                elif 'state' in c and 'state' not in demo_mapping.values(): demo_mapping[c] = 'state'
            
            if demo_mapping:
                demo_sub = df[[id_target] + list(demo_mapping.keys())].copy()
                demo_sub.rename(columns=demo_mapping, inplace=True)
                
                if 'zipcode' in demo_sub.columns:
                    demo_sub['zipcode'] = demo_sub['zipcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace('nan', '')
                    demo_sub['zipcode'] = demo_sub['zipcode'].apply(lambda x: x.zfill(5) if len(x) > 0 else np.nan)
                
                demo_sub = demo_sub.dropna(how='all', subset=demo_mapping.values()).drop_duplicates(subset=[id_target])
                
                if is_asc_file:
                    if asc_year_df.empty or len(asc_year_df.columns) == 1: asc_year_df = demo_sub
                    else: asc_year_df = asc_year_df.set_index('asc_id').combine_first(demo_sub.set_index('asc_id')).reset_index()
                else:
                    if hopd_year_df.empty or len(hopd_year_df.columns) == 1: hopd_year_df = demo_sub
                    else: hopd_year_df = hopd_year_df.set_index('ccn').combine_first(demo_sub.set_index('ccn')).reset_index()

            # =========================================================
            # 1. OAS CAHPS SNIFFER
            # =========================================================
            oas_mapping = {}
            for c in raw_cols: 
                c_lower_text = str(c).lower().strip()
                if "patients recommending the facility linear mean score" in c_lower_text:
                    oas_mapping[clean_col(c)] = 'oas_recmnd_linear'
                elif "rating of the facility linear mean score" in c_lower_text:
                    oas_mapping[clean_col(c)] = 'oas_rating_linear'
                elif "rating of 9 or 10" in c_lower_text: 
                    oas_mapping[clean_col(c)] = 'oas_rating_9_10'
                elif "definitely recommend" in c_lower_text and "yes" in c_lower_text: 
                    oas_mapping[clean_col(c)] = 'oas_recmnd_dy'

            if oas_mapping:
                df_oas = df.rename(columns=oas_mapping)
                for col in oas_mapping.values():
                    if col in df_oas.columns:
                        df_oas[col] = pd.to_numeric(df_oas[col].astype(str).replace(['Not Available', 'N/A'], np.nan), errors='coerce')
                        
                oas_cols = [id_target] + [col for col in oas_mapping.values() if col in df_oas.columns]
                oas_sub = df_oas[oas_cols].groupby(id_target).mean().reset_index()
                
                if is_asc_file:
                    if asc_year_df.empty: asc_year_df = oas_sub
                    else: asc_year_df = asc_year_df.set_index('asc_id').combine_first(oas_sub.set_index('asc_id')).reset_index()
                    asc_found = True
                    print(f"  [+] Harvested ASC OAS CAHPS from {f}")
                else:
                    if hopd_year_df.empty: hopd_year_df = oas_sub
                    else: hopd_year_df = hopd_year_df.set_index('ccn').combine_first(oas_sub.set_index('ccn')).reset_index()
                    hopd_found = True
                    print(f"  [+] Harvested HOPD OAS CAHPS from {f}")

            # =========================================================
            # 2. TARGETED METRICS (LONG FORMAT)
            # =========================================================
            measure_col = next((c for c in cols if 'measureid' in c), None)
            score_col = next((c for c in cols if 'score' in c or 'measureresponse' in c), None)
            
            if measure_col and score_col:
                target_ops = ['OP_3', 'OP_8', 'OP_17', 'OP_18', 'OP_22', 'OP_26', 'OP_37D', 'OP_37E', 'OP_40', 'ASC_1', 'ASC_2', 'ASC_3', 'ASC_4']
                df['std_measure'] = df[measure_col].apply(standardize_measure_id)
                df_target = df[df['std_measure'].isin(target_ops)].copy()
                
                if not df_target.empty:
                    df_target['clean_score'] = df_target[score_col].apply(clean_cms_score)
                    pivot_targets = df_target.pivot_table(index=id_target, columns='std_measure', values='clean_score', aggfunc='mean').reset_index()
                    
                    if is_asc_file:
                        if asc_year_df.empty: asc_year_df = pivot_targets
                        else: asc_year_df = asc_year_df.set_index('asc_id').combine_first(pivot_targets.set_index('asc_id')).reset_index()
                        asc_found = True
                    else:
                        if hopd_year_df.empty: hopd_year_df = pivot_targets
                        else: hopd_year_df = hopd_year_df.set_index('ccn').combine_first(pivot_targets.set_index('ccn')).reset_index()
                        hopd_found = True
                    print(f"  [+] Harvested Targeted Metrics from {f}")

            # =========================================================
            # 3. WIDE FORMAT: OP-26 VOLUME
            # =========================================================
            vol_cols = ['gastrointestinal', 'eye', 'nervoussystem', 'musculoskeletal', 'skin', 'genitourinary', 'cardiovascular', 'respiratory', 'other']
            avail_cols = [c for c in vol_cols if c in cols]
            
            if len(avail_cols) >= 3:
                for c in avail_cols:
                    df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '').replace(['notavailable', 'n/a'], np.nan), errors='coerce')
                
                df['clean_score'] = df[avail_cols].sum(axis=1, min_count=1)
                pivot_vol = df[[id_target, 'clean_score']].groupby(id_target).mean().reset_index()
                pivot_vol.rename(columns={'clean_score': 'OP_26'}, inplace=True)
                
                if is_asc_file:
                    if asc_year_df.empty: asc_year_df = pivot_vol
                    else: asc_year_df = asc_year_df.set_index('asc_id').combine_first(pivot_vol.set_index('asc_id')).reset_index()
                    asc_found = True
                else:
                    if hopd_year_df.empty: hopd_year_df = pivot_vol
                    else: hopd_year_df = hopd_year_df.set_index('ccn').combine_first(pivot_vol.set_index('ccn')).reset_index()
                    hopd_found = True
                print(f"  [+] Harvested OP-26 Procedure Volumes from {f}")

            # =========================================================
            # 4. LEGACY WIDE ASC FORMATS
            # =========================================================
            asc_rate_cols = [c for c in cols if 'asc' in c and 'rate' in c]
            if asc_rate_cols and is_asc_file:
                for c in asc_rate_cols:
                    match = re.search(r'asc\-?_?(\d+)', c)
                    if match:
                        m_num = match.group(1)
                        col_name = f'ASC_{m_num}'
                        temp = df.groupby(id_target)[c].apply(lambda x: pd.to_numeric(x, errors='coerce').mean()).reset_index(name=col_name)
                        
                        if asc_year_df.empty: asc_year_df = temp
                        else: asc_year_df = asc_year_df.set_index('asc_id').combine_first(temp.set_index('asc_id')).reset_index()
                        asc_found = True
                print(f"  [+] Harvested Legacy Wide ASC Metrics from {f}")

        except Exception as e: 
            pass

    # --- YEARLY APPENDS ---
    if hopd_found and not hopd_year_df.empty:
        hopd_year_df = hopd_year_df.dropna(subset=['ccn']).drop_duplicates(subset=['ccn'])
        hopd_year_df['year'] = exp_year
        master_hopd.append(hopd_year_df)

    if asc_found and not asc_year_df.empty:
        asc_year_df = asc_year_df.dropna(subset=['asc_id']).drop_duplicates(subset=['asc_id'])
        asc_year_df['year'] = exp_year
        master_asc.append(asc_year_df)

# --- COMBINE AND SAVE ---
if master_hopd:
    hopd_final = pd.concat(master_hopd, ignore_index=True)
    cols = hopd_final.columns.tolist()
    cols.insert(0, cols.pop(cols.index('year')))
    cols.insert(0, cols.pop(cols.index('ccn')))
    hopd_final = hopd_final[cols]
    hopd_path = os.path.join(output_dir, "outpatient_hopd_quality_panel.csv")
    hopd_final.to_csv(hopd_path, index=False)
    print(f"\n=== COMPLETE! Saved {len(hopd_final)} records to {hopd_path} ===")

if master_asc:
    asc_final = pd.concat(master_asc, ignore_index=True)
    cols = asc_final.columns.tolist()
    cols.insert(0, cols.pop(cols.index('year')))
    cols.insert(0, cols.pop(cols.index('asc_id')))
    asc_final = asc_final[cols]
    asc_path = os.path.join(output_dir, "outpatient_asc_quality_panel.csv")
    asc_final.to_csv(asc_path, index=False)
    print(f"=== COMPLETE! Saved {len(asc_final)} records to {asc_path} ===")
