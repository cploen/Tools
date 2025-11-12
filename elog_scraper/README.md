 In the spirit of portability, I built a tool to automatically back up ELOG entries, including metadata, full text, and attachments.

Basic Usage:
Run from the command line:
python3 elog_scraper.py --dest /your/target/folder

Folder will be created if necessary.  You'll be prompted for your JLab username and password.

Library Dependencies:
- Standard libraries: 
    •    os, re, time, json, argparse, getpass
    •    datetime, unicodedata, logging
    •    urllib.parse
- Nonstandard:
$ pip install requests beautifulsoup4 python-slugify

Features:
- logs in via HTTPS
- stores a session cookie for each scrape
- each entry saved to a folder like: 185_Fri_Sep_12_2025_Christine_BcmCalibrationVsFaradayCupResults/ 
- saves full body text as entry_XXXX.txt
- downloads attachments and saves in attachments/ folder inside each entry
- saves structured metadata for each entry like:
{
    "ID": "185",
    "Date": "Fri Sep 12 12:00:31 2025",
    "Author": "Christine",
    "Author Email": "cploen@jlab.org",
    "Category": "Normalization (inc beam and target)",
    "Status": "On-going",
    "Subject": "BCM Calibration vs Faraday Cup Results",
    "Text": "entry_185.txt",
    "Attachments": [
        {
            "filename": "FCUP_BCMs_NPS_RG1Aelog.pdf",
            "url": "https://hallcweb.jlab.org/elogs/nps-rg1a-analysis/250912_120413/FCUP_BCMs_NPS_RG1Aelog.pdf",
            "mimetype": "application/pdf",
            "size": 1889281
        }
    ]
}
- skips entries that already exist locally, based on folder name.
- Handles malformed or inconsistent ELOG pages gracefully.

Output Summary Log:
After each run, a .log file is saved to your current directory with a name like:
    20251107_1030_elog_scrape.log
It includes:
- A run summary (number of entries saved)
- Any warnings (e.g. failed downloads or decoding issues)

Current Target:
- Default is  https://hallcweb.jlab.org/elogs/NPS-RG1a-Analysis/
- Change "ELOG_FOLDER" inside the script to back up other experiments.

Let me know if you need some help or have suggestions! 

-- Christine
