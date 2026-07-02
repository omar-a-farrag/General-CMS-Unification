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

print("=== STARTING OUTPATIENT QUALITY HARVESTER (V4: TOTAL HARVEST) ===")

def clean_col(c): 
    return str(c).lower().replace(' ', '').replace('_', '').replace('-', '').replace('*', '')

def clean_ccn(series):
    return series.astype(str).str.replace("'", "").str.split('.').str[0].str.zfill(6)

def get_year_from_folder(folder_name):
    match = re.search(r'20[0-9]{2}', folder_name)
    return int(match.group(0)) if match else None

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
        try:
            try: df_peek = pd.read_csv(os.path.join(folder_path, f), nrows=2, encoding='utf-8-sig')
            except UnicodeDecodeError: df_peek = pd.read_csv(os.path.join(folder_path, f), nrows=2, encoding='cp1252')
            
            cols = [clean_col(c) for c in df_peek.columns]
            raw_cols = df_peek.columns.tolist()
            
            id_col_raw = next((c for c, cc in zip(raw_cols, cols) if cc in ['facilityid', 'providerid', 'providernumber']), None)
            
            # --- 1. LONG FORMAT SNIFFER ---
            if id_col_raw and 'measureid' in cols and 'score' in cols:
                try: df = pd.read_csv(os.path.join(folder_path, f), encoding='utf-8-sig')
                except: df = pd.read_csv(os.path.join(folder_path, f), encoding='cp1252')
                
                df.columns = [clean_col(c) for c in df.columns]
                df['ccn'] = clean_ccn(df[clean_col(id_col_raw)])
                df['score'] = pd.to_numeric(df['score'], errors='coerce')
                
                # A. HOPD OP metrics (ALL OF THEM)
                op_df = df[df['measureid'].astype(str).str.upper().str.contains(r'OP[\-_]?\d+[A-Z]?', case=False, na=False)]
                if not op_df.empty:
                    measures = op_df['measureid'].unique()
                    for m in measures:
                        match = re.search(r'OP[\-_]?(\d+[A-Z]?)', str(m).upper())
                        if match:
                            m_num = match.group(1).lower()
                            m_df = op_df[op_df['measureid'] == m]
                            if not m_df.empty:
                                sub = m_df.groupby('ccn')['score'].mean().reset_index().rename(columns={'score': f'hopd_op_{m_num}'})
                                if hopd_year_df.empty:
                                    hopd_year_df = sub
                                elif f'hopd_op_{m_num}' not in hopd_year_df.columns:
                                    hopd_year_df = pd.merge(hopd_year_df, sub, on='ccn', how='outer')
                                else:
                                    hopd_year_df = hopd_year_df.set_index('ccn').combine_first(sub.set_index('ccn')).reset_index()
                                hopd_found = True

                # B. ASC long metrics
                asc_df = df[df['measureid'].astype(str).str.upper().str.contains(r'ASC[\-_]?\d+', case=False, na=False)]
                if not asc_df.empty:
                    df['asc_id'] = df['ccn'].astype(str).str.strip().str.upper()
                    
                    # Extract Metadata
                    meta_dict = {}
                    if 'npi' in cols: meta_dict['npi'] = 'first'
                    if 'facilityname' in cols or 'ascname' in cols: meta_dict[next(c for c in df.columns if 'name' in c)] = 'first'
                    if 'city' in cols: meta_dict['city'] = 'first'
                    if 'state' in cols: meta_dict['state'] = 'first'
                    if 'zipcode' in cols: meta_dict['zipcode'] = 'first'
                    
                    sub_meta = df.groupby('asc_id').agg(meta_dict).reset_index() if meta_dict else pd.DataFrame({'asc_id': df['asc_id'].unique()})
                    
                    if asc_year_df.empty: asc_year_df = sub_meta
                    else: asc_year_df = asc_year_df.set_index('asc_id').combine_first(sub_meta.set_index('asc_id')).reset_index()
                    
                    measures = asc_df['measureid'].unique()
                    for m in measures:
                        match = re.search(r'ASC\-?_?(\d+)', str(m).upper())
                        if match:
                            m_num = match.group(1)
                            m_df = asc_df[asc_df['measureid'] == m]
                            if not m_df.empty:
                                sub = m_df.groupby('asc_id')['score'].mean().reset_index().rename(columns={'score': f'asc_rate_{m_num}'})
                                if f'asc_rate_{m_num}' not in asc_year_df.columns:
                                    asc_year_df = pd.merge(asc_year_df, sub, on='asc_id', how='outer')
                                else:
                                    asc_year_df = asc_year_df.set_index('asc_id').combine_first(sub.set_index('asc_id')).reset_index()
                                asc_found = True

            # --- 2. WIDE FORMAT SNIFFER ---
            asc_rate_cols = [c for c in cols if 'asc' in c and 'rate' in c]
            if asc_rate_cols:
                try: df = pd.read_csv(os.path.join(folder_path, f), encoding='utf-8-sig')
                except: df = pd.read_csv(os.path.join(folder_path, f), encoding='cp1252')
                id_cols_to_check = ['facilityid', 'providerid', 'providernumber', 'ccn', 'ascid', 'asc_id']
                id_col = next((c for c in df.columns if clean_col(c) in id_cols_to_check), None)
                
                if id_col:
                    df.columns = [clean_col(c) for c in df.columns]
                    df['asc_id'] = df[clean_col(id_col)].astype(str).str.strip().str.upper()
                    
                    # Extract Metadata
                    meta_dict = {}
                    if 'npi' in df.columns: meta_dict['npi'] = 'first'
                    if 'facilityname' in df.columns or 'ascname' in df.columns: meta_dict[next(c for c in df.columns if 'name' in c)] = 'first'
                    if 'city' in df.columns: meta_dict['city'] = 'first'
                    if 'state' in df.columns: meta_dict['state'] = 'first'
                    if 'zipcode' in df.columns: meta_dict['zipcode'] = 'first'
                    
                    asc_sub = df.groupby('asc_id').agg(meta_dict).reset_index() if meta_dict else pd.DataFrame({'asc_id': df['asc_id'].unique()})
                    
                    # Extract Rates (Use combine_first strictly to prevent duplicates)
                    for c in asc_rate_cols:
                        match = re.search(r'asc\-?_?(\d+)', c)
                        if match:
                            m_num = match.group(1)
                            col_name = f'asc_rate_{m_num}'
                            temp = df.groupby('asc_id')[c].apply(lambda x: pd.to_numeric(x, errors='coerce').mean()).reset_index(name=col_name)
                            
                            if col_name in asc_sub.columns:
                                asc_sub = asc_sub.set_index('asc_id').combine_first(temp.set_index('asc_id')).reset_index()
                            else:
                                asc_sub = pd.merge(asc_sub, temp, on='asc_id', how='outer')
                            asc_found = True
                            
                    if not asc_sub.empty and len(asc_sub.columns) > 1:
                        if asc_year_df.empty: asc_year_df = asc_sub
                        else: asc_year_df = asc_year_df.set_index('asc_id').combine_first(asc_sub.set_index('asc_id')).reset_index()

        except Exception as e: pass

    # --- YEARLY APPENDS ---
    if hopd_found and not hopd_year_df.empty:
        hopd_year_df = hopd_year_df.dropna(subset=['ccn']).drop_duplicates(subset=['ccn'])
        hopd_year_df['year'] = exp_year
        master_hopd.append(hopd_year_df)
        print("  [+] Harvested ALL HOPD Metrics (OP-1 to OP-35+)")

    if asc_found and not asc_year_df.empty:
        asc_year_df = asc_year_df.rename(columns=lambda x: 'asc_name' if 'name' in x else x)
        asc_year_df = asc_year_df.dropna(subset=['asc_id']).drop_duplicates(subset=['asc_id'])
        asc_year_df['year'] = exp_year
        master_asc.append(asc_year_df)
        print("  [+] Harvested Freestanding ASC Metrics (+ Metadata)")

# --- COMBINE AND SAVE HOPD ---
if master_hopd:
    hopd_final = pd.concat(master_hopd, ignore_index=True)
    cols = hopd_final.columns.tolist()
    cols.insert(0, cols.pop(cols.index('year')))
    cols.insert(0, cols.pop(cols.index('ccn')))
    hopd_final = hopd_final[cols]
    hopd_path = os.path.join(output_dir, "outpatient_hopd_quality_panel.csv")
    hopd_final.to_csv(hopd_path, index=False)
    print(f"\n=== COMPLETE! Saved {len(hopd_final)} records to {hopd_path} ===")

# --- COMBINE AND SAVE ASC ---
if master_asc:
    asc_final = pd.concat(master_asc, ignore_index=True)
    cols = asc_final.columns.tolist()
    cols.insert(0, cols.pop(cols.index('year')))
    cols.insert(0, cols.pop(cols.index('asc_id')))
    if 'zipcode' in asc_final.columns:
        # Prevent NAs from turning into "nan"
        asc_final['zipcode'] = asc_final['zipcode'].astype(str).str.split('.').str[0].str.split('-').str[0].str.zfill(5)
        asc_final.loc[asc_final['zipcode'] == '00nan', 'zipcode'] = np.nan
    
    asc_final = asc_final[cols]
    asc_path = os.path.join(output_dir, "outpatient_asc_quality_panel.csv")
    asc_final.to_csv(asc_path, index=False)
    print(f"=== COMPLETE! Saved {len(asc_final)} records to {asc_path} ===")