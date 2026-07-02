import os
import re
import pandas as pd

# --- SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..",".."))
hcahps_dir = os.path.join(project_root, "hcahps")

print("=== CMS QUALITY DATA INVENTORY MAPPER ===\n")

# Define the keywords that identify each dataset category across the 17 years
CATEGORIES = {
    'HAI (Infections)': ['hai', 'infection'],
    'Readmissions & Deaths': ['readmission', 'readm', 'complication', 'mortality', 'death'],
    'Timely & Effective Care': ['timely', 'effective', 'dbo_vwhqi_hosp_imm'],
    'HVBP (Value-Based Purchasing)': ['hvbp', 'value based', 'value_based'],
    'Spending & Payment': ['spending', 'payment', 'net_change', 'net change', 'drg_payment'],
    'ASC (Ambulatory Surgery)': ['ambulatory', 'asc']
}

def get_year_from_folder(folder_name):
    match = re.search(r'20[0-9]{2}', folder_name)
    return int(match.group(0)) if match else None

folders = [f for f in os.listdir(hcahps_dir) if os.path.isdir(os.path.join(hcahps_dir, f)) and ('hcahps20' in f.lower() or 'hchaps20' in f.lower())]
folders.sort()

inventory = []

for folder in folders:
    folder_year = get_year_from_folder(folder)
    if not folder_year: continue
    
    experience_year = folder_year - 1
    folder_path = os.path.join(hcahps_dir, folder)
    
    # Initialize the row for this year
    year_data = {'Folder Year': folder_year, 'Exp Year': experience_year}
    for cat in CATEGORIES:
        year_data[cat] = "---"
        
    # Scan all files in the folder
    files = os.listdir(folder_path)
    files_lower = [f.lower() for f in files]
    
    # For 2012/2013, we know a lot of data is hidden inside the MDBs
    is_mdb_year = folder_year in [2012, 2013] and any(f.endswith('.mdb') for f in files_lower)
    
    for cat, keywords in CATEGORIES.items():
        found = False
        for f_name in files_lower:
            # Look for the keywords in the filename
            if any(kw in f_name for kw in keywords):
                # Ignore state/national rollups to ensure we have facility-level data
                if 'state' not in f_name and 'national' not in f_name:
                    found = True
                    break
        
        if found:
            year_data[cat] = "YES"
        elif is_mdb_year:
            year_data[cat] = "MDB?" # Flag that it might be inside the Access DB
            
    inventory.append(year_data)

# --- OUTPUT THE MAP ---
df_inventory = pd.DataFrame(inventory)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

print("DATASET AVAILABILITY BY EXPERIENCE YEAR:")
print("-" * 100)
print(df_inventory.to_string(index=False))
print("-" * 100)
print("\nNote: 'MDB?' means the data is likely inside the raw Microsoft Access database for that year.")

# Save to CSV for easy viewing
output_csv = os.path.join(project_root,"dictionaries_and_crosswalks", "cms_quality_inventory_map.csv")
df_inventory.to_csv(output_csv, index=False)

# ==============================================================================
# ADDITION: EXPORT TO LATEX FOR APPENDIX
# ==============================================================================
# Ensure the tables directory exists
tex_dir = os.path.join(project_root, "outputs_while_cleaning", "tables")
if not os.path.exists(tex_dir): 
    os.makedirs(tex_dir)

tex_path = os.path.join(tex_dir, "appendix_quality_inventory_map.tex")
caption = "CMS Quality Inventory Map. This table tracks the cross-year availability grid mapping the physical presence of HAI, Readmissions, Mortality, and Spending data lines."

# Generate the LaTeX table string
latex_str = df_inventory.to_latex(
    index=False,
    caption=caption,
    label="tab:quality_inventory",
    escape=True,
    position="htbp"
)

# Optional: Add the same gray header styling used in your other scripts
latex_str = latex_str.replace("\\toprule", "\\toprule\n\\rowcolor{gray!10}")

with open(tex_path, 'w') as f:
    f.write(latex_str)

print(f"[+] Saved LaTeX table to: {tex_path}")