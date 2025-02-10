import os
import csv
import re
from collections import defaultdict

# Define the base directory where COIN_NPS_Start_Run_* folders are located
base_dir = "/w/hallc-scshelf2102/nps/cploen/metadata_files/"
search_dir = os.path.join(base_dir, "COIN")  # Fixed missing parenthesis

# Directory to store CSV files (at the same level as COIN)
output_dir = os.path.join(os.path.dirname(base_dir), "FA250_Config")
os.makedirs(output_dir, exist_ok=True)

# Dictionary to store runs grouped by FA250 config
config_groups = defaultdict(list)

# Pattern to extract run number from folder name
run_pattern = re.compile(r'COIN_NPS_Start_Run_(\d{4})')

# Loop through all folders in COIN directory
for folder in os.listdir(search_dir):
    match = run_pattern.match(folder)
    if match:
        run_number = int(match.group(1))  # Convert to integer for proper sorting
        file_path = os.path.join(search_dir, folder, "nps-vme1.dat")  # Fixed incorrect path
        
        if os.path.isfile(file_path):
            with open(file_path, "r") as f:
                lines = f.readlines()
                
                # Extract FA250 Config line
                for line in lines:
                    if line.startswith("# FA250 Config:"):
                        fa250_config = line.split(": ")[-1].strip()
                        config_groups[fa250_config].append(run_number)
                        break

# Save each group to a separate CSV file
for config, runs in config_groups.items():
    # Sort run numbers in numerical order
    runs.sort()

    # Create a filename based on the config path
    config_name = config.replace("/", "_").replace(".", "_").replace(" ", "_")
    csv_filename = os.path.join(output_dir, f"FA250_Config_{config_name}.csv")    

    with open(csv_filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Run Number", "FA250 Config"])
        for run in runs:
            writer.writerow([run, config])

    print(f"Saved: {csv_filename}")
