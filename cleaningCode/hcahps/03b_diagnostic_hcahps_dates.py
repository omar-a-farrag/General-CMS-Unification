import os
import pandas as pd
import numpy as np
import re
import warnings

# Suppress warnings for clean console output
warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

# --- SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..",".."))
hcahps_dir = os.path.join(project_root, "hcahps")

print("=== HCAHPS SURVEY DATES DIAGNOSTIC ===\n")

def clean_col_name(c): 
    return str(c).lower().replace(' ', '').replace('_', '')

folders = [f for f in os.listdir(hcahps_dir) if os.path.isdir(os.path.join(hcahps_dir, f)) and ('hcahps20' in f.lower() or 'hchaps20' in f.lower())]
folders.sort()

results = []

for folder in folders:
    match = re.search(r'20[0-9]{2}', folder)
    if not match: continue
    folder_year = int(match.group(0))
    experience_year = folder_year - 1
    
    folder_path = os.path.join(hcahps_dir, folder)
    
    start_date = "Not Found"
    end_date = "Not Found"
    source_file = "None"
    
    # 1. Gather Candidate Files (HCAHPS or Measure Dates)
    candidate_files = []
    for f in os.listdir(folder_path):
        f_lower = f.lower()
        if f.endswith('.csv'):
            if 'hcahps' in f_lower or 'measure' in f_lower or 'date' in f_lower:
                # Ignore states/footnotes to speed up the scan
                if 'state' not in f_lower and 'footnote' not in f_lower:
                    candidate_files.append(f)
                    
    # Sort to prioritize HCAHPS files or specific Measure Dates files
    candidate_files.sort(key=lambda x: ('hcahps' in x.lower(), 'date' in x.lower()), reverse=True)
    
    # 2. Hunt for Date Columns
    for f in candidate_files:
        filepath = os.path.join(folder_path, f)
        try:
            # Only read the first 1000 rows to make the scan lightning fast
            df = pd.read_csv(filepath, nrows=1000, encoding='utf-8-sig')
        except UnicodeDecodeError:
            try: df = pd.read_csv(filepath, nrows=1000, encoding='cp1252')
            except: continue
        except: continue
            
        cols = {clean_col_name(c): c for c in df.columns}
        
        # Check if start/end dates exist
        start_col, end_col = None, None
        for c in cols.keys():
            if 'startdate' in c: start_col = cols[c]
            if 'enddate' in c: end_col = cols[c]
            
        if start_col and end_col:
            # Clean out missing values and footnotes
            valid_starts = df[start_col].astype(str).replace(['Not Available', 'nan', 'NaN', 'N/A'], np.nan).dropna()
            valid_ends = df[end_col].astype(str).replace(['Not Available', 'nan', 'NaN', 'N/A'], np.nan).dropna()
            
            if not valid_starts.empty and not valid_ends.empty:
                # Get the most common date (mode) to bypass any weird row-level quirks
                start_date = valid_starts.mode()[0]
                end_date = valid_ends.mode()[0]
                source_file = f
                break # Dates found! Move to the next folder.
                
    results.append({
        'Folder Year': folder_year,
        'Experience Year': experience_year,
        'Start Date': start_date,
        'End Date': end_date,
        'Source File': source_file
    })
    
    # Print real-time progress
    print(f"[{folder_year} / Exp: {experience_year}] {start_date} TO {end_date}  (Source: {source_file})")

# --- OUTPUT SUMMARY ---
print("\n" + "="*70)
print("=== FINAL DATES SUMMARY ===")
print("="*70)

df_results = pd.DataFrame(results)

# Format the console output so it looks like a clean table
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print(df_results.to_string(index=False))

# Save for your records
output_csv = os.path.join(project_root,"dictionaries_and_crosswalks", "hcahps_survey_dates_summary.csv")
df_results.to_csv(output_csv, index=False)
print(f"\n[+] Saved summary table to: {output_csv}")

# ==============================================================================
# ADDITION: EXPORT TO LATEX FOR APPENDIX
# ==============================================================================
# Ensure the tables directory exists
tex_dir = os.path.join(project_root, "outputs_while_cleaning", "tables")
if not os.path.exists(tex_dir): 
    os.makedirs(tex_dir)

tex_path = os.path.join(tex_dir, "appendix_hcahps_survey_dates.tex")
caption = "HCAHPS Survey Dates Summary. This table audits the exact data collection start and end dates extracted from files across all years to validate the accuracy of the Experience Year Shift."

# Generate the LaTeX table string
latex_str = df_results.to_latex(
    index=False,
    caption=caption,
    label="tab:survey_dates",
    escape=True,
    position="htbp"
)

# Optional: Add the same gray header styling used in your other scripts
latex_str = latex_str.replace("\\toprule", "\\toprule\n\\rowcolor{gray!10}")

with open(tex_path, 'w') as f:
    f.write(latex_str)

print(f"[+] Saved LaTeX table to: {tex_path}")