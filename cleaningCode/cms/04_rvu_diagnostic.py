import os
import pandas as pd
import warnings

# Suppress openpyxl warnings about default styling
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# --- SETUP PATHS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", "..")) 
rvu_dir = os.path.join(project_root, "rvu")
output_file = os.path.join(project_root, "outputs_while_cleaning", "dictionaries", "rvu_schema_report.txt")

years_to_scan = range(2013, 2024)

print(f"Scanning RVU directories from 2013 to 2023 in: {rvu_dir}")

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("=================================================================\n")
    f.write("CMS PFS RVU DIAGNOSTIC REPORT (2013-2023)\n")
    f.write("=================================================================\n\n")

    for year in years_to_scan:
        folder_name = f"{year}_rvu"
        folder_path = os.path.join(rvu_dir, folder_name)
        
        f.write(f"\n{'='*65}\n")
        f.write(f"YEAR: {year} | FOLDER: {folder_name}\n")
        f.write(f"{'='*65}\n")
        
        if not os.path.exists(folder_path):
            f.write(f"[!] Folder not found: {folder_path}\n")
            continue
            
        files = os.listdir(folder_path)
        
        # 1. Report all files in the directory
        f.write("ALL FILES IN FOLDER:\n")
        for file in files:
            f.write(f"  - {file}\n")
            
        # 2. Filter for readable data files (Excel / CSV)
        data_files = [file for file in files if file.endswith(('.xlsx', '.csv', '.xls')) and not file.startswith('~')]
        
        f.write("\nDATA PREVIEWS (First 15 rows to locate headers):\n")
        f.write("-" * 65 + "\n")
        
        for file in data_files:
            file_path = os.path.join(folder_path, file)
            f.write(f"\n--> PEEKING INSIDE: {file}\n")
            
            try:
                if file.endswith('.csv'):
                    df = pd.read_csv(file_path, nrows=15, encoding='utf-8-sig')
                else:
                    # Read Excel (nrows=15 is not natively supported in all pandas/openpyxl versions easily, 
                    # so we read a chunk or head)
                    df = pd.read_excel(file_path, engine='openpyxl').head(15)
                
                # Convert the dataframe to a string representation to write to the text file
                df_str = df.to_string(index=False)
                f.write(f"{df_str}\n")
                
            except Exception as e:
                f.write(f"  [!] Could not read {file}: {e}\n")

print(f"\nDone! Diagnostic report saved to: {output_file}")