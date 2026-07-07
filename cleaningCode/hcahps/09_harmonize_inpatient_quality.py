import os
import pandas as pd
import numpy as np
import re
import warnings

try:
    import pyodbc
    HAS_PYODBC = True
except ImportError:
    HAS_PYODBC = False

warnings.filterwarnings("ignore")

# --- SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..")) 
hcahps_dir = os.path.join(project_root, "hcahps")
output_dir = os.path.join(hcahps_dir, "harmonized")

if not os.path.exists(output_dir): os.makedirs(output_dir)

print("=== STARTING INPATIENT QUALITY HARVESTER (V5: LEGACY DB + DEMOGRAPHICS) ===")

def clean_ccn(series):
    return series.astype(str).str.replace("'", "").str.split('.').str[0].str.zfill(6)

def clean_col(c): 
    return str(c).lower().replace(' ', '').replace('_', '').replace('-', '')

def get_year_from_folder(folder_name):
    match = re.search(r'20[0-9]{2}', folder_name)
    return int(match.group(0)) if match else None

folders = [f for f in os.listdir(hcahps_dir) if os.path.isdir(os.path.join(hcahps_dir, f)) and ('hcahps20' in f.lower() or 'hchaps20' in f.lower())]
folders.sort()

master_panel = []

for folder in folders:
    folder_year = get_year_from_folder(folder)
    if not folder_year: continue
    exp_year = folder_year - 1
    
    print(f"\nProcessing {folder} (Exp Year: {exp_year})...")
    folder_path = os.path.join(hcahps_dir, folder)
    year_df = pd.DataFrame(columns=['ccn'])
    
    files = os.listdir(folder_path)
    
    # ==========================================================
    # 1. DTA EXTRACTION (Earliest Years: 2007-2010 Mortality)
    # ==========================================================
    dta_mort_files = [f for f in files if f.endswith('.dta') and 'mortality' in f.lower() and 'hosp' in f.lower()]
    if dta_mort_files:
        try:
            raw_mort = pd.read_stata(os.path.join(folder_path, dta_mort_files[0]))
            raw_mort.columns = [clean_col(c) for c in raw_mort.columns]
            
            if 'providernumber' in raw_mort.columns:
                raw_mort['ccn'] = clean_ccn(raw_mort['providernumber'])
                rate_col = next((c for c in raw_mort.columns if 'mortality' in c and 'rate' in c), None)
                
                if rate_col:
                    raw_mort['mort_rate'] = pd.to_numeric(raw_mort[rate_col], errors='coerce')
                    mort_df = pd.DataFrame()
                    
                    for cond in ['AMI', 'Heart Attack', 'HF', 'Heart Failure', 'PN', 'Pneumonia']:
                        cond_col = next((c for c in raw_mort.columns if 'condition' in c or 'measurename' in c), None)
                        if cond_col:
                            cond_df = raw_mort[raw_mort[cond_col].astype(str).str.contains(cond, case=False)]
                            if not cond_df.empty:
                                cond_tag = 'ami' if ('ami' in cond.lower() or 'attack' in cond.lower()) else ('hf' if ('hf' in cond.lower() or 'failure' in cond.lower()) else 'pn')
                                sub = cond_df[['ccn', 'mort_rate']].rename(columns={'mort_rate': f'mortality_rate_{cond_tag}'})
                                sub = sub.groupby('ccn').mean().reset_index() 
                                
                                if mort_df.empty: 
                                    mort_df = sub
                                elif f'mortality_rate_{cond_tag}' not in mort_df.columns:
                                    mort_df = pd.merge(mort_df, sub, on='ccn', how='outer')
                                else:
                                    mort_df = mort_df.set_index('ccn').combine_first(sub.set_index('ccn')).reset_index()

                    if not mort_df.empty:
                        year_df = pd.merge(year_df, mort_df, on='ccn', how='outer')
                        print("  [+] Harvested Mortality Rates (DTA)")
        except Exception as e: print(f"  [!] DTA Error: {e}")

    # ==========================================================
    # 2. MDB EXTRACTION (Middle Years: 2011-2012)
    # ==========================================================
    is_mdb_year = folder_year in [2012, 2013] and any(f.endswith('.mdb') for f in files)
    if is_mdb_year and HAS_PYODBC:
        mdb_file = [f for f in files if f.endswith('.mdb')][0]
        conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + os.path.join(folder_path, mdb_file) + ';'
        try:
            conn = pyodbc.connect(conn_str)
            tables = [t.table_name for t in conn.cursor().tables(tableType='TABLE')]
            
            # Extract RRP
            rrp_table = next((t for t in tables if 'readm' in t.lower() and 'reduction' in t.lower()), None)
            if rrp_table:
                raw_rrp = pd.read_sql(f'SELECT * FROM {rrp_table}', conn)
                raw_rrp.columns = [clean_col(c) for c in raw_rrp.columns]
                if 'providernumber' in raw_rrp.columns:
                    raw_rrp['ccn'] = clean_ccn(raw_rrp['providernumber'])
                    raw_rrp['excess_ratio'] = pd.to_numeric(raw_rrp['excessreadmissionratio'], errors='coerce')
                    rrp_df = pd.DataFrame()
                    for cond in ['AMI', 'HF', 'PN']:
                        cond_df = raw_rrp[raw_rrp['measurename'].astype(str).str.contains(cond, case=False)]
                        if not cond_df.empty:
                            sub = cond_df[['ccn', 'excess_ratio']].rename(columns={'excess_ratio': f'rrp_excess_ratio_{cond.lower()}'})
                            sub = sub.groupby('ccn').mean().reset_index()
                            if rrp_df.empty: rrp_df = sub
                            else: rrp_df = pd.merge(rrp_df, sub, on='ccn', how='outer')
                    if not rrp_df.empty:
                        year_df = pd.merge(year_df, rrp_df, on='ccn', how='outer')
                        print("  [+] Harvested Readmissions (MDB)")
                        
            # Extract Mortality
            mort_table = next((t for t in tables if 'mortality' in t.lower() and 'state' not in t.lower() and 'national' not in t.lower()), None)
            if mort_table:
                raw_mort = pd.read_sql(f'SELECT * FROM {mort_table}', conn)
                raw_mort.columns = [clean_col(c) for c in raw_mort.columns]
                if 'providernumber' in raw_mort.columns:
                    raw_mort['ccn'] = clean_ccn(raw_mort['providernumber'])
                    rate_col = next((c for c in raw_mort.columns if 'mortality' in c and 'rate' in c), None)
                    if rate_col:
                        raw_mort['mort_rate'] = pd.to_numeric(raw_mort[rate_col], errors='coerce')
                        mort_df = pd.DataFrame()
                        for cond in ['AMI', 'Heart Attack', 'HF', 'Heart Failure', 'PN', 'Pneumonia']:
                            cond_df = raw_mort[raw_mort['measurename'].astype(str).str.contains(cond, case=False)]
                            if not cond_df.empty:
                                cond_tag = 'ami' if 'ami' in cond.lower() or 'attack' in cond.lower() else ('hf' if 'hf' in cond.lower() or 'failure' in cond.lower() else 'pn')
                                sub = cond_df[['ccn', 'mort_rate']].rename(columns={'mort_rate': f'mortality_rate_{cond_tag}'})
                                sub = sub.groupby('ccn').mean().reset_index() 
                                if mort_df.empty: 
                                    mort_df = sub
                                elif f'mortality_rate_{cond_tag}' not in mort_df.columns:
                                    mort_df = pd.merge(mort_df, sub, on='ccn', how='outer')
                                else:
                                    mort_df = mort_df.set_index('ccn').combine_first(sub.set_index('ccn')).reset_index()
                        if not mort_df.empty:
                            year_df = pd.merge(year_df, mort_df, on='ccn', how='outer')
                            print("  [+] Harvested Mortality Rates (MDB)")
                            
            conn.close()
        except Exception as e: print(f"  [!] MDB Error: {e}")

    # ==========================================================
    # 3. CSV COLUMN SNIFFER (Modern Years)
    # ==========================================================
    csv_files = [f for f in files if f.endswith('.csv') and 'state' not in f.lower() and 'national' not in f.lower()]
    
    for f in csv_files:
        f_lower = f.lower()
        try:
            try: df_peek = pd.read_csv(os.path.join(folder_path, f), nrows=2, encoding='utf-8-sig')
            except UnicodeDecodeError: df_peek = pd.read_csv(os.path.join(folder_path, f), nrows=2, encoding='cp1252')
            
            raw_cols = df_peek.columns.tolist()
            cols = [clean_col(c) for c in raw_cols]
            id_col_raw = next((c for c in raw_cols if clean_col(c) in ['facilityid', 'providerid', 'providernumber', 'ccn']), None)
            
            if not id_col_raw: continue 
            
            try: df = pd.read_csv(os.path.join(folder_path, f), encoding='utf-8-sig')
            except: df = pd.read_csv(os.path.join(folder_path, f), encoding='cp1252')
            
            df.columns = cols
            df['ccn'] = clean_ccn(df[clean_col(id_col_raw)])

            # =========================================================
            # 0. DEMOGRAPHICS SNIFFER (ZIP, City, State)
            # =========================================================
            demo_mapping = {}
            for c in cols:
                if 'zip' in c and 'zipcode' not in demo_mapping.values(): demo_mapping[c] = 'zipcode'
                elif 'city' in c and 'city' not in demo_mapping.values(): demo_mapping[c] = 'city'
                elif 'state' in c and 'state' not in demo_mapping.values(): demo_mapping[c] = 'state'
            
            if demo_mapping:
                demo_sub = df[['ccn'] + list(demo_mapping.keys())].copy()
                demo_sub.rename(columns=demo_mapping, inplace=True)
                
                if 'zipcode' in demo_sub.columns:
                    demo_sub['zipcode'] = demo_sub['zipcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace('nan', '')
                    demo_sub['zipcode'] = demo_sub['zipcode'].apply(lambda x: x.zfill(5) if len(x) > 0 else np.nan)
                
                demo_sub = demo_sub.dropna(how='all', subset=demo_mapping.values()).drop_duplicates(subset=['ccn'])
                if not demo_sub.empty:
                    if year_df.empty or len(year_df.columns) == 1: year_df = demo_sub
                    else: year_df = year_df.set_index('ccn').combine_first(demo_sub.set_index('ccn')).reset_index()

            # =========================================================
            # 1. HVBP SCORES (Agnostic to file name changes)
            # =========================================================
            if 'hvbp' in f_lower:
                score_cols = [c for c in df.columns if 'score' in c or 'totalperformance' in c]
                if score_cols:
                    hvbp_sub = df[['ccn'] + score_cols].copy()
                    for col in score_cols:
                        hvbp_sub[col] = pd.to_numeric(hvbp_sub[col].astype(str).replace(['notavailable', 'n/a', 'none', 'notapplicable'], np.nan), errors='coerce')
                    
                    hvbp_sub.columns = ['ccn'] + [re.sub(r'[^a-z0-9_]', '', c.replace('score', '_score')) for c in score_cols]
                    hvbp_sub = hvbp_sub.dropna(axis=1, how='all')
                    
                    if len(hvbp_sub.columns) > 1:
                        hvbp_sub = hvbp_sub.groupby('ccn').mean().reset_index()
                        year_df = year_df.set_index('ccn').combine_first(hvbp_sub.set_index('ccn')).reset_index()
                        print(f"  [+] Harvested HVBP Scores from {f}")

            # =========================================================
            # 2. PAYMENT & VALUE
            # =========================================================
            elif 'payment_and_value' in f_lower or 'payment - hospital' in f_lower or 'payment and value' in f_lower:
                id_col = next((c for c in df.columns if 'paymentmeasureid' in c), None)
                cat_col = next((c for c in df.columns if 'paymentcategory' in c), None)
                if id_col and cat_col:
                    pay_sub = df[['ccn', id_col, cat_col]].copy()
                    pay_pivot = pay_sub.pivot_table(index='ccn', columns=id_col, values=cat_col, aggfunc=lambda x: ' '.join(set(x.dropna()))).reset_index()
                    year_df = year_df.set_index('ccn').combine_first(pay_pivot.set_index('ccn')).reset_index()
                    print(f"  [+] Harvested Payment Categories from {f}")

            # =========================================================
            # 3. SPENDING (MSPB)
            # =========================================================
            elif 'spending' in f_lower and 'hospital' in f_lower:
                score_col = next((c for c in df.columns if 'score' in c and 'footnote' not in c), None)
                if score_col:
                    mspb_sub = df[['ccn', score_col]].copy()
                    mspb_sub['mspb_score'] = pd.to_numeric(mspb_sub[score_col].astype(str).replace(['notavailable', 'n/a'], np.nan), errors='coerce')
                    mspb_sub = mspb_sub.groupby('ccn')['mspb_score'].mean().reset_index()
                    year_df = year_df.set_index('ccn').combine_first(mspb_sub.set_index('ccn')).reset_index()
                    print(f"  [+] Harvested MSPB Scores from {f}")

            # =========================================================
            # 4. READMISSIONS & HAC & MORTALITY (LONG FORMAT)
            # =========================================================
            if 'excessreadmissionratio' in cols:
                df['excess_ratio'] = pd.to_numeric(df['excessreadmissionratio'], errors='coerce')
                rrp_df = pd.DataFrame()
                for cond in ['AMI', 'HF', 'PN']:
                    cond_df = df[df['measurename'].astype(str).str.contains(cond, case=False)]
                    if not cond_df.empty:
                        sub = cond_df.groupby('ccn')['excess_ratio'].mean().reset_index().rename(columns={'excess_ratio': f'rrp_excess_ratio_{cond.lower()}'})
                        if rrp_df.empty: rrp_df = sub
                        else: rrp_df = rrp_df.set_index('ccn').combine_first(sub.set_index('ccn')).reset_index()
                if not rrp_df.empty:
                    year_df = year_df.set_index('ccn').combine_first(rrp_df.set_index('ccn')).reset_index()
                    print("  [+] Harvested Readmissions (CSV)")
                    
            if 'totalhacscore' in cols:
                hac_df = df[['ccn']].copy()
                hac_df['hac_total_score'] = pd.to_numeric(df['totalhacscore'], errors='coerce')
                hac_df = hac_df.dropna(subset=['hac_total_score']).drop_duplicates(subset=['ccn'])
                if not hac_df.empty:
                    year_df = year_df.set_index('ccn').combine_first(hac_df.set_index('ccn')).reset_index()
                    print("  [+] Harvested HAC Penalties (CSV)")

            if 'measureid' in cols and 'score' in cols:
                df['score'] = pd.to_numeric(df['score'].astype(str).replace(['notavailable', 'n/a'], np.nan), errors='coerce')
                
                # Backup MSPB catch
                mspb_df = df[df['measureid'].astype(str).str.contains('MSPB', case=False)]
                if not mspb_df.empty:
                    mspb_sub = mspb_df.groupby('ccn')['score'].mean().reset_index().rename(columns={'score': 'mspb_score'})
                    if 'mspb_score' not in year_df.columns:
                        year_df = year_df.set_index('ccn').combine_first(mspb_sub.set_index('ccn')).reset_index()
                        print("  [+] Harvested MSPB Scores (CSV)")
                    
                mort_df = pd.DataFrame()
                for cond in ['AMI', 'HF', 'PN']:
                    cond_df = df[df['measureid'].astype(str).str.contains(f'MORT_30_{cond}', case=False, na=False)]
                    if not cond_df.empty:
                        sub = cond_df.groupby('ccn')['score'].mean().reset_index().rename(columns={'score': f'mortality_rate_{cond.lower()}'})
                        if mort_df.empty: mort_df = sub
                        else: mort_df = mort_df.set_index('ccn').combine_first(sub.set_index('ccn')).reset_index()
                if not mort_df.empty:
                    year_df = year_df.set_index('ccn').combine_first(mort_df.set_index('ccn')).reset_index()
                    print("  [+] Harvested Mortality Rates (CSV)")

        except Exception as e: 
            pass

    year_df = year_df.dropna(subset=['ccn']).drop_duplicates(subset=['ccn'])
    if len(year_df.columns) > 1:
        year_df['year'] = exp_year
        master_panel.append(year_df)
    else:
        print("  [-] No quality metrics found for this year.")

if master_panel:
    final_df = pd.concat(master_panel, ignore_index=True)
    cols = final_df.columns.tolist()
    cols.insert(0, cols.pop(cols.index('year')))
    cols.insert(0, cols.pop(cols.index('ccn')))
    final_df = final_df[cols]
    save_path = os.path.join(output_dir, "inpatient_quality_panel.csv")
    final_df.to_csv(save_path, index=False)
    print(f"\n=== COMPLETE! Saved {len(final_df)} records to {save_path} ===")
