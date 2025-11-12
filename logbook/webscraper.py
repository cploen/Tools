import requests
import getpass
import argparse
import json
import urllib.parse
import time
import os
import re
import logging
from bs4 import BeautifulSoup
from datetime import datetime

start_time = time.time()

# URLs
BASE_URL = "https://logbooks.jlab.org/"
LOGIN_URL = "https://logbooks.jlab.org/entries?destination=entries"
SEARCH_URL = "https://logbooks.jlab.org/entries"

# Set up logging configuration
logging.basicConfig(
    filename="debug.log",  # Log to a file
    level=logging.DEBUG,  # Capture all debug messages
    format="%(asctime)s - %(levelname)s - %(message)s",  # Include timestamp
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Load settings from a JSON file
def load_settings(filename="settings.json"):
    """Loads filtering rules and default parameters from a settings file."""
    try:
        with open(filename, "r") as file:
            settings = json.load(file)
            logging.debug(f"✅ Loaded settings: {settings}")  # Log output
            return settings
    except FileNotFoundError:
        print(f"⚠️ Settings file '{filename}' not found. Using default values.")
        return {}  
    except json.JSONDecodeError:
        print(f"❌ Error reading '{filename}'. Please check JSON formatting.")
        exit(1)

settings = load_settings()

# Parse command-line arguments
parser = argparse.ArgumentParser("JLab Logbook Webscraper - Search and download logbook entries.")
parser.add_argument("--quiet", action="store_true", help="Suppress terminal output and save results to a file only")
parser.add_argument("--no-download", action="store_true", help="Skip file downloads")
parser.add_argument("--debug", action="store_true", help="Enable debugging mode (includes detailed output and disables downloads)")
parser.add_argument("--filter", action="store_true", help="Enable filtering of search results based on settings.json")

parser.add_argument("--start-date", type=str, default="", help="Start date (YYYY-MM-DD)")
parser.add_argument("--end-date", type=str, default="", help="End date (YYYY-MM-DD)")
parser.add_argument("--logbook", type=str, default="", help="Logbook ID to search (HCLOG: 84, NPS: 573)")
parser.add_argument("--search", type=str, default="", help="Search keyword (Ex: 'COIN_NPS Start_Run_')")

args = parser.parse_args()

# Apply hierarchy: Flags > JSON > Default
args.start_date = args.start_date.strip() or settings.get("start_date", "2023-09-01")
args.end_date = args.end_date.strip() or settings.get("end_date", "2024-06-01")
args.logbook = args.logbook.strip() or settings.get("logbook", "84")
args.search = args.search.strip() or settings.get("search_string", "COIN_NPS Start_Run_")

# Debugging Output
print(f"🔍 Final search parameters:")
print(f"   📅 Start Date: {args.start_date}")
print(f"   📅 End Date: {args.end_date}")
print(f"   📓 Logbook: {args.logbook}")
print(f"   🔍 Search String: {args.search}")

logging.debug(f"🔍 Using search parameters: start_date={args.start_date}, end_date={args.end_date}, logbook={args.logbook}, search={args.search}")

# If the user did not manually specify a search term, override it with settings.json
if not args.search.strip():  # Catch empty strings
    args.search = settings.get("search_string", "COIN_NPS Start_Run_")
   
# Ensure debug mode forces no-download
if args.debug:
    args.no_download = True  # Debug mode should not download files
    print("🛠️ Debugging mode enabled. Downloads are disabled.")
    logging.info("Debugging mode enabled. Downloads are disabled.")

# Ensure dates are properly formatted
def validate_date(date_str):
    """Validates and formats the input date string."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")  # Check format
        return f"{date_str} 00:00"  # Convert to required format
    except ValueError:
        print(f"❌ Invalid date format: {date_str}. Use YYYY-MM-DD.")
        exit(1)  # Stop execution if date is invalid

start_date = validate_date(args.start_date)
end_date = validate_date(args.end_date)

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
if args.debug and form_build_id:
    logging.debug(f"🔹 Extracted form_build_id: {form_build_id}")
elif args.debug:
    logging.warning("⚠️ No form_build_id found. Login may fail.")

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
if args.debug and form_build_id and form_token:
    logging.debug(f"🔹 Extracted search form_build_id: {form_build_id}")
    logging.debug(f"🔹 Extracted search form_token: {form_token}")
elif args.debug:
    logging.warning("⚠️ No form_build_id or form_token found for search. Search may fail.")
    exit()

# Step 6: Define search payload
search_payload = {
    "start_date": start_date,
    "end_date": end_date,
    "logbooks[0]": args.logbook,  
    "search_str": args.search,
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
logging.debug(f"🔎 Search Payload: {search_payload}")

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

   # Load filtering settings from settings.json
    search_pattern = re.compile(settings.get("search_pattern", r"NPS: END of run\\d+"))
    exclude_keywords = settings.get("exclude_keywords", [])

    # If --filter is set, apply filtering; otherwise, keep all results
    if args.filter:
        print("✅ Filtering enabled. Applying search pattern and keyword exclusions.")
    
        # Apply regex filtering (only keep entries that match the expected pattern)
        filtered_entries = [entry for entry in entries if search_pattern.search(entry.text.strip())]

        # Apply keyword exclusion (remove entries with unwanted words)
        filtered_entries = [entry for entry in filtered_entries
                            if not any(exclude.lower() in entry.text.lower() for exclude in exclude_keywords)]

        # Stop if no valid entries remain after filtering
        if not filtered_entries:
            print("⚠️ No entries matched the refined search criteria. Exiting.")
            exit()
    else:
        print("⚠️ Filtering disabled. Processing all search results.")
        filtered_entries = entries  # Use all results without filtering 
        # Display a filtered preview of up to 5 results
       
    print("\n🔹 **Search Preview:**\n")
    preview_count = min(10, len(filtered_entries))
    for index, entry in enumerate(filtered_entries[:preview_count], start=1):
        entry_title = entry.text.strip()
        entry_url = urllib.parse.urljoin(BASE_URL, entry["href"])
        print(f"{index}. 📄 {entry_title}")
        print(f"   🔗 {entry_url}\n")

    # Ask the user if they want to continue with the download
    proceed = input("Do you want to proceed with downloading metadata files? (y/n): ").strip().lower()
    if proceed != 'y':
        print("🚫 Download canceled. Exiting script.")
        exit()
 
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
base_metadata_dir = "metadata"
os.makedirs(base_metadata_dir, exist_ok=True)

if args.no_download:
    print("🚫 Downloading stage skipped due to --no-download or --debug flag.")
    logging.info("Skipping file downloads.")
else:
    page = 0  # Start at the first page
    max_pages = 100  # Prevent infinite loops

while page < max_pages:
    print(f"🔹 Fetching page {page}...")

    # Update search payload with pagination
    search_payload["page"] = page  # Ensure the correct page number is requested

    # Encode URL with updated pagination
    encoded_search_url = f"https://logbooks.jlab.org/entries?{urllib.parse.urlencode(search_payload)}"

    # Send paginated search request
    search_response = session.get(encoded_search_url, headers=headers)

    # Check for a valid response
    if not search_response.ok:
        print(f"❌ Failed to fetch page {page}. Stopping pagination.")
        break  

    search_soup = BeautifulSoup(search_response.text, "html.parser")

    # Extract log entry titles and links
    entries = search_soup.select("a[href^='/entry/']")
    if not entries:
        print("✅ No more entries to process. Pagination complete.")
        break  # Stop if no more results

    print(f"🔹 Found {len(entries)} results on page {page}")

    for index, entry in enumerate(entries, start=1):
        entry_title = entry.text.strip()
        entry_url = urllib.parse.urljoin(BASE_URL, entry["href"])
        print(f"🔹 Processing entry {index + (page * 100)}: {entry_title}")

        # Extract run number using regex
        match = re.search(r"NPS: END of run (\d+)", entry_title, re.IGNORECASE)
        run_number = match.group(1) if match else None

        if not run_number:
            print(f"⚠️ Skipping entry {entry_title} (Run number not found)")
            continue  # Skip if no run number is detected

        # Create a folder for this run number
        run_folder_name = settings.get("output_folder_format", "NPS_END_of_run_{run_number}")
        run_folder = os.path.join(base_metadata_dir, run_folder_name.format(run_number=run_number))
        os.makedirs(run_folder, exist_ok=True)

        # Fetch log entry page
        entry_page = session.get(entry_url)
        entry_soup = BeautifulSoup(entry_page.text, "html.parser")

        # Load file types from settings.json
        file_types = settings.get("file_types", [".dat"])  # Default to .dat if missing

        # Create a selector for all file types
        file_selectors = ",".join([f"a[href$='{ext}']" for ext in file_types])

        # Find metadata files
        file_links = entry_soup.select(file_selectors)

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

    # ✅ Move to the next page AFTER all processing
    page += 1
#if total_processed == 0:
#    print("❌ Search failed! Possibly no valid results found. Server response:")
if args.debug:
    logging.debug(f"🔹 Final Response URL: {search_response.url}")
    logging.debug(search_response.text[:1000])
    # Elapsed time
    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.info(f"⏱️ Script execution time: {elapsed_time:.2f} seconds")
