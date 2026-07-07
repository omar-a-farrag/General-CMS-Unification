import os
import pandas as pd
import glob

# Set this to your actual HCAHPS root directory
hcahps_dir = r"C:\Users\omarf\Dropbox\personal_files_omar_farrag\Research\general_cms_data\hcahps"

# We will check an older year and a newer year to see how the columns drift
check_years = ["hcahps2008","hcahps2009","hcahps2010","hcahps2011","hcahps2012",
               "hcahps2013", "hcahps2014","hcahps2015","hcahps2016","hcahps2017",
              "hcahps2018","hcahps2019", "hcahps2020", "hcahps2021","hcahps2022",
              "hcahps2023","hcahps2024","hcahps2025"] 

# Keywords to find the exact files you want
target_files = [
    "hvbp", "payment", "medicare hospital spending", "outpatient procedures volume", 
    "timely and effective", "outpatient imaging", "structural measures"
]

# Name of the output text file
output_file = r"C:\Users\omarf\Dropbox\personal_files_omar_farrag\Research\general_cms_data\outputs_while_cleaning\dictionaries\scheme_sniffer_report.txt"

# Open the file for writing with UTF-8 encoding to prevent text errors
with open(output_file, "w", encoding="utf-8") as f:
    for yr in check_years:
        yr_path = os.path.join(hcahps_dir, yr)
        if not os.path.exists(yr_path): continue
        
        # Adding file=f redirects the output from the console into the text file
        print(f"\n{'='*80}\nSCANNING FOLDER: {yr}\n{'='*80}", file=f)
        
        all_csvs = glob.glob(os.path.join(yr_path, "*.csv"))
        
        for csv_file in all_csvs:
            filename = os.path.basename(csv_file).lower()
            if any(keyword in filename for keyword in target_files):
                try:
                    # Read just the first row to get the column headers
                    df = pd.read_csv(csv_file, nrows=1, encoding='utf-8-sig')
                except UnicodeDecodeError:
                    df = pd.read_csv(csv_file, nrows=1, encoding='cp1252')
                
                print(f"\nFILE: {os.path.basename(csv_file)}", file=f)
                print(f"COLUMNS: {list(df.columns)}", file=f)

print(f"Done! Report saved to {os.path.abspath(output_file)}")
