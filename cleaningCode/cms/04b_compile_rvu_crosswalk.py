import os
import pandas as pd
import numpy as np
import re

# --- SETUP PATHS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..")) 
rvu_dir = os.path.join(project_root, "rvu")
output_dir = os.path.join(project_root, "crosswalks")

if not os.path.exists(output_dir): os.makedirs(output_dir)

print("=== STARTING CMS PFS RVU MASTER COMPILATION ===")

master_rvu_list = []
years = range(2013, 2024)

for year in years:
    folder_name = f"{year}_rvu"
    folder_path = os.path.join(rvu_dir, folder_name)
    
    if not os.path.exists(folder_path):
        print(f"[!] Warning: Folder for {year} missing. Skipping.")
        continue
        
    # Dynamically find the main PPRRVU CSV file
    files = os.listdir(folder_path)
    target_file = next((f for f in files if f.upper().startswith("PPRRVU") and f.endswith(".csv")), None)
    
    if not target_file:
        print(f"[!] Warning: No PPRRVU CSV found in {folder_name}. Skipping.")
        continue
        
    file_path = os.path.join(folder_path, target_file)
    print(f"Processing {year} using file: {target_file}...")
    
    # Read raw lines to find the dynamic header row index containing 'HCPCS'
    header_idx = None
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f_obj:
        for idx, line in enumerate(f_obj):
            if "HCPCS" in line:
                header_idx = idx
                break
                
    if header_idx is None:
        print(f"  [!] Hard Error: Could not locate HCPCS header row in {target_file}!")
        continue
        
# Read the full file now using the discovered header row
    try:
        df_raw = pd.read_csv(file_path, skiprows=header_idx, encoding='utf-8')
    except UnicodeDecodeError:
        df_raw = pd.read_csv(file_path, skiprows=header_idx, encoding='cp1252')
        
    # Standardize column headers to clean snake_case strings
    df_raw.columns = [str(c).strip().upper().replace(" ", "_").replace("-", "_") for c in df_raw.columns]
    
    # Map the variable target columns based on their index alignment
    # Index 0 = HCPCS, Index 1 = MOD, Index 5 = WORK, Index 6 = NON-FAC PE, Index 8 = FAC PE, Index 10 = MP
    col_mapping = {
        df_raw.columns[0]: 'hcpcs',
        df_raw.columns[1]: 'mod',
        df_raw.columns[5]: 'work_rvu',
        df_raw.columns[6]: 'non_fac_pe_rvu',
        df_raw.columns[8]: 'fac_pe_rvu',
        df_raw.columns[10]: 'mp_rvu'
    }
    
    df_clean = df_raw[list(col_mapping.keys())].rename(columns=col_mapping)
    
    # Strip whitespace from keys and force strings
    df_clean['hcpcs'] = df_clean['hcpcs'].astype(str).str.strip().str.upper()
    df_clean['mod'] = df_clean['mod'].astype(str).str.strip().str.upper()
    df_clean['mod'] = df_clean['mod'].replace(['NAN', 'NONE', ''], np.nan)
    
    # Clean numeric fields (remove commas, force spaces/text to NaN, then fill with 0.0)
    num_cols = ['work_rvu', 'non_fac_pe_rvu', 'fac_pe_rvu', 'mp_rvu']
    for col in num_cols:
        df_clean[col] = df_clean[col].astype(str).str.replace(",", "").str.strip()
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0.0)
        
    # Filter out rows where HCPCS code is missing or empty text artifacts
    df_clean = df_clean[df_clean['hcpcs'].str.len() > 0]
    df_clean = df_clean[~df_clean['hcpcs'].isin(['NAN', 'HCPCS'])]
    
    # Assign the panel year anchor
    df_clean['year'] = int(year)
    
    # Ensure strict column ordering
    df_clean = df_clean[['hcpcs', 'mod', 'year', 'work_rvu', 'non_fac_pe_rvu', 'fac_pe_rvu', 'mp_rvu']]
    
    # Dedup keys to guarantee relational integrity during early merges
    df_clean = df_clean.drop_duplicates(subset=['hcpcs', 'mod'], keep='first')
    
    master_rvu_list.append(df_clean)
    print(f"  > Successfully harvested {len(df_clean)} clinical codes for {year}")

# --- COMBINE AND EXPORT ---
if master_rvu_list:
    final_crosswalk = pd.concat(master_rvu_list, ignore_index=True)
    save_path = os.path.join(output_dir, "cms_pfs_rvu_crosswalk.csv")
    final_crosswalk.to_csv(save_path, index=False)
    print(f"\n=== SUCCESS! Saved {len(final_crosswalk)} rows to crosswalk: {save_path} ===")
else:
    print("\n[!] Error: No data rows compiled.")