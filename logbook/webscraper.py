import requests
import getpass
import argparse
import json
import urllib.parse
import time
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime

start_time = time.time()

# URLs
BASE_URL = "https://logbooks.jlab.org/"
LOGIN_URL = "https://logbooks.jlab.org/entries?destination=entries"
SEARCH_URL = "https://logbooks.jlab.org/entries"

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--quiet", action="store_true", help="Suppress terminal output and save results to a file only")
args = parser.parse_args()

# Get username & password securely
USERNAME = input("Enter your JLab username: ")
PASSWORD = getpass.getpass("Enter your JLab password: ")

# Start a session
session = requests.Session()

# Step 1: Fetch login page to get `form_build_id`
login_page = session.get(BASE_URL)
soup = BeautifulSoup(login_page.text, "html.parser")

# Extract form_build_id for login
form_build_input = soup.find("input", {"name": "form_build_id"})
form_build_id = form_build_input["value"] if form_build_input else None

# Debugging
if form_build_id:
    print(f"🔹 Extracted form_build_id: {form_build_id}")
else:
    print("⚠️ No form_build_id found. Login may fail.")

# Step 2: Define login payload
login_payload = {
    "name": USERNAME,
    "pass": PASSWORD,
    "form_build_id": form_build_id,
    "form_id": "user_login_block",
    "op": "Log in"
}

# Step 3: Send login request
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": BASE_URL,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://logbooks.jlab.org",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

response = session.post(LOGIN_URL, data=login_payload, headers=headers)

# Step 4: Check if login was successful
if response.ok and "logout" in response.text.lower():
    print("✅ Login successful!")
else:
    print("❌ Login failed! The website may require additional fields.")
    exit()

# Step 5: Fetch the search page to get `form_build_id` and `form_token`
search_page = session.get(SEARCH_URL)
soup = BeautifulSoup(search_page.text, "lxml")

# Extract new form_build_id and form_token for the search form
form_build_input = soup.find("input", {"name": "form_build_id"})
form_token_input = soup.find("input", {"name": "form_token"})

form_build_id = form_build_input["value"] if form_build_input else None
form_token = form_token_input["value"] if form_token_input else None

# Debugging
if form_build_id and form_token:
    print(f"🔹 Extracted search form_build_id: {form_build_id}")
    print(f"🔹 Extracted search form_token: {form_token}")
else:
    print("⚠️ No form_build_id or form_token found for search. Search may fail.")
    exit()

# Step 6: Define search payload
search_payload = {
    "start_date": "2023-09-01 00:00",
    "end_date": "2024-06-01 00:00",
    "logbooks[0]": "84",  
    "search_str": "COIN_NPS Start_Run_",  
    "group_by": "SHIFT",
    "listing_format": "table",
    "entries_per_page": "100",
    "form_build_id": form_build_id,
    "form_token": form_token,
    "form_id": "elog_form_advanced_filters",
    "op": "Submit"
}

# Encode the parameters correctly for a GET request
encoded_search_url = f"https://logbooks.jlab.org/entries?{urllib.parse.urlencode(search_payload)}"

# Step 7: Send the search request
search_response = session.get(encoded_search_url, headers=headers)

# Step 8: Check for successful search request and parse search results
if search_response.ok:
    print("✅ Search request successful!")
    search_soup = BeautifulSoup(search_response.text, "html.parser")

    # Extract log entry titles and links
    entries = search_soup.select("a[href^='/entry/']")[:100]
    print(f"🔹 Found {len(entries)} results")

    # Stop if no entries are found
    if not entries:
        print("✅ All entries processed successfully! No more results to fetch.")
        exit()  # Exit cleanly

    print(f"🔹 Found {len(entries)} results")
    
    # Save all results to a file
    with open("logbook_results.txt", "w") as file:
        for entry in entries:
            file.write(f"{entry.text.strip()} - {BASE_URL}{entry['href']}\n")

    # If --quiet flag is set, do not print to terminal
    if args.quiet:
        print("✅ Full results saved to logbook_results.txt")
    else:
        print("\n".join([f"📄 Log Entry: {entry.text.strip()} - {BASE_URL}{entry['href']}" for entry in entries[:10]]))

    # Step 9: Extract & Download Metadata Files
# Directory where all metadata folders will be stored
base_metadata_dir = "metadata_files"
os.makedirs(base_metadata_dir, exist_ok=True)

import os
import re
import requests
import urllib.parse
from bs4 import BeautifulSoup

# Set base directory for metadata files
base_metadata_dir = "metadata_files"
os.makedirs(base_metadata_dir, exist_ok=True)

page = 0  # Start at the first page
while True:  # Loop until no more pages exist
    print(f"🔹 Fetching page {page}...")

    # Update search payload with pagination
    search_payload["page"] = page  # Add the page parameter

    # Encode URL with updated pagination
    encoded_search_url = f"https://logbooks.jlab.org/entries?{urllib.parse.urlencode(search_payload)}"

    # Send paginated search request
    search_response = session.get(encoded_search_url, headers=headers)

    # Check for a valid response
    if not search_response.ok:
        print(f"❌ Failed to fetch page {page}. Stopping pagination.")
        break  # Exit the loop if the request fails

    search_soup = BeautifulSoup(search_response.text, "html.parser")

    # Extract log entry titles and links
    entries = search_soup.select("a[href^='/entry/']")
    if not entries:
        print("✅ No more entries to process. Pagination complete.")
        break  # Stop if there are no more entries

    print(f"🔹 Found {len(entries)} results on page {page}")

    for index, entry in enumerate(entries, start=1):
        entry_title = entry.text.strip()
        entry_url = urllib.parse.urljoin(BASE_URL, entry["href"])
        print(f"🔹 Processing entry {index}/{len(entries)} on page {page}: {entry_title}")

        # Extract run number using regex
        match = re.search(r"Start_Run_(\d+)", entry_title)
        run_number = match.group(1) if match else None

        if not run_number:
            print(f"⚠️ Skipping entry {entry_title} (Run number not found)")
            continue  # Skip if no run number is detected

        # Create a folder for this run number
        run_folder = os.path.join(base_metadata_dir, f"COIN_NPS_Start_Run_{run_number}")
        os.makedirs(run_folder, exist_ok=True)

        # Fetch log entry page
        entry_page = session.get(entry_url)
        entry_soup = BeautifulSoup(entry_page.text, "html.parser")

        # Find metadata files (.dat and .results)
        file_links = entry_soup.select("a[href$='.dat'], a[href$='.results']")
        if not file_links:
            print(f"⚠️ No metadata files found for Run {run_number}. Skipping download.")
            continue  # Skip if no files are found

        for file_link in file_links:
            file_href = file_link["href"]  # Extract relative file path
            file_url = urllib.parse.urljoin(BASE_URL, file_href)  # Ensure full URL
            file_name = file_url.split("/")[-1]  # Extract filename

            print(f"📥 Downloading: {file_name} from {file_url}")

            # Download the file
            file_response = session.get(file_url, stream=True)
            if file_response.status_code == 200:
                file_path = os.path.join(run_folder, file_name)  # Save inside run folder
                with open(file_path, "wb") as file:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        file.write(chunk)
                print(f"✅ Saved: {file_path}")
            else:
                print(f"❌ Failed to download {file_name}")

    # Move to the next page
    page += 1

else:
    print("❌ Search failed! Server response:")
    print(f"🔹 Final Response URL: {search_response.url}")
    print(search_response.text[:1000])

# Step 10: Elapsed time
end_time = time.time()
elapsed_time = end_time - start_time
print(f"⏱️ Script execution time: {elapsed_time:.2f} seconds")
