# -----------------------------------------------------------
# ELOG Scraper Script
# Author: Christine Ploen (cploen@jlab.org)
# Created: 2025-11-07
#
# This script was developed to assist with backing up Hall C ELOG
# entries (metadata, text, and attachments) for the NPS-RG1a-Analysis log.
# Feel free to reuse, adapt, or improve it for your own analysis needs.
#
# No license required — please cite or acknowledge if substantially reused.
# -----------------------------------------------------------

import requests
import getpass
import argparse
import json
import urllib.parse
import time
import os
import re
import logging
import unicodedata
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
from slugify import slugify

# -------------------------
# Choose experimental ELOG
# -------------------------
ELOG_FOLDER = "NPS-RG1a-Analysis"  # Swap for other experiments

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
logging.basicConfig(
    filename=f"{timestamp}_elog_scrape.log",
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

parser = argparse.ArgumentParser(description="ELOG backup tool")
parser.add_argument(
    "--dest", type=str, required=True, help="Destination folder to save entries"
)
args = parser.parse_args()

TOP_DIR = args.dest
DEST_DIR = os.path.join(TOP_DIR, ELOG_FOLDER)
os.makedirs(DEST_DIR, exist_ok=True)
print(f"📁 Destination directory: {DEST_DIR}")

first_entry_id = None
last_entry_id = None
num_entries_saved = 0

# -------------------------
# Login config
# -------------------------
BASE_URL = "https://hallcweb.jlab.org/elogs/"
ELOG_URL = urljoin(BASE_URL, ELOG_FOLDER + "/")

username = input("Enter your JLab username: ")
password = getpass.getpass("Enter your JLab password: ")

session = requests.Session()
payload = {"uname": username, "upassword": password, "remember": "1", "redir": ""}
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Referer": ELOG_URL,
    "Origin": "https://hallcweb.jlab.org",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Login POST
login_response = session.post(
    ELOG_URL, files=payload, headers=headers, allow_redirects=True
)
response = login_response
soup = BeautifulSoup(response.text, "html.parser")

login_failed = "Please login" in login_response.text or soup.find(
    "input", {"name": "uname"}
)

if login_response.status_code == 200 and not login_failed:
    print("✅ Login to hallcweb.jlab.org successful!")
    print("🍪 Session cookies:", session.cookies.get_dict())
    print("📄 Page title:", soup.title.string.strip())
else:
    print(f"❌ Login failed! Status code: {login_response.status_code}")
    print("📄 Page title:", soup.title.text if soup.title else "No title")
    print(login_response.text[:200])
    exit(1)


# -------------------------
# Helper: make folder name with slug
# -------------------------
def make_folder_name(entry_number, date_str, author, subject, max_length=40):
    import re
    from datetime import datetime

    # Try parsing the ELOG-style date first
    try:
        date = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y")
        formatted_date = date.strftime("%a_%b_%d_%Y")  # e.g. Wed_Oct_29_2025
    except ValueError:
        formatted_date = date_str.replace(" ", "_")  # fallback if parsing fails

    # Clean author name (first word, capitalized)
    author_clean = author.strip().split()[0].capitalize()

    # Clean subject: remove filler words, capitalize keywords
    words = re.findall(r"\b\w+\b", subject)
    subject_clean = "".join(
        w.capitalize()
        for w in words
        if w.lower()
        not in {
            "the",
            "in",
            "on",
            "at",
            "of",
            "a",
            "an",
            "and",
            "to",
            "for",
            "with",
            "by",
            "but",
        }
    )

    subject_clean = subject_clean[:max_length]

    return f"{entry_number}_{formatted_date}_{author_clean}_{subject_clean}"


# -------------------------
# Step 2: Parse all entries with pagination
# -------------------------
page_url = ELOG_URL
page_number = 1

while True:
    print(f"\n📄 Scraping page {page_number}: {page_url}")
    response = session.get(page_url)
    soup = BeautifulSoup(response.text, "html.parser")

    entry_table = None
    for i, table in enumerate(soup.find_all("table")):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
        if "ID" in headers and "Subject" in headers:
            entry_table = table
            break

    if not entry_table:
        print("❌ Could not find elog entry table.")
        break

    rows = entry_table.find_all("tr")
    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
    print(f"🧠 Table headers: {headers}")

    os.makedirs(DEST_DIR, exist_ok=True)
    print("\n📂 Creating folders for entries on this page:\n")
    for row in rows[1:]:  # All rows except header
        try:
            cols = row.find_all("td")
            if not cols:
                continue
            while len(cols) < 9:
                cols.append(BeautifulSoup("<td></td>", "html.parser").td)

            entry_id = cols[0].get_text(strip=True) or "UNKNOWN_ID"
            timestamp_raw = cols[1].get_text(strip=True) or "UNKNOWN_TIMESTAMP"
            author = (
                cols[2].get_text(strip=True).split()[0]
                if cols[2].get_text(strip=True)
                else "UNKNOWN"
            )
            author_email = cols[3].get_text(strip=True) or ""
            category = cols[4].get_text(strip=True) or ""
            status = cols[5].get_text(strip=True) or ""
            subject = cols[6].get_text(strip=True) or ""

            # Convert date string
            try:
                dt = datetime.strptime(timestamp_raw, "%a %b %d %H:%M:%S %Y")
                timestamp_str = dt.strftime("%Y-%m-%d_%H-%M-%S")
            except Exception as e:
                print(f"⚠️ Failed to parse date for entry {entry_id}: {e}")
                timestamp_str = "unknown"

            # Make folder
            folder_name = make_folder_name(entry_id, timestamp_raw, author, subject)
            folder_path = os.path.join(DEST_DIR, folder_name)
            # ✅ Skip if already downloaded
            if os.path.exists(folder_path):
                print(f"⏭️ Skipping entry {entry_id}: folder already exists")
                continue
            # Track saved range
            if first_entry_id is None:
                first_entry_id = entry_id
            last_entry_id = entry_id
            num_entries_saved += 1

            os.makedirs(folder_path, exist_ok=True)

            # -------------------------
            # Download full entry text
            # -------------------------
            try:
                detail_url = (
                    f"https://hallcweb.jlab.org/elogs/nps-rg1a-analysis/{entry_id}"
                )
                response = session.get(detail_url)
                entry_soup = BeautifulSoup(response.text, "html.parser")

                body_tag = entry_soup.find("pre") or entry_soup.find(
                    "div", class_="content"
                )
                if body_tag and body_tag.get_text(strip=True):
                    body_text = body_tag.get_text(strip=True)
                else:
                    td_tags = entry_soup.find_all("td")
                    if td_tags:
                        longest_td = max(
                            td_tags, key=lambda tag: len(tag.get_text(strip=True))
                        )
                        body_text = longest_td.get_text(strip=True, separator="\n")
                    else:
                        body_text = "(No body text found)"
                body_text = re.sub(r"[\u200B\u200C\u200D\uFEFF]", "", body_text)
                body_text = unicodedata.normalize("NFKC", body_text)

                # Supplemental links / passcodes
                link_texts, passcode_lines = [], []
                for a_tag in entry_soup.find_all("a", href=True):
                    href = a_tag["href"].strip()
                    text = a_tag.get_text(strip=True)
                    if any(
                        bad in href
                        for bad in ["cmd=", "mailto:", "../", "elog.psi.ch", "?id="]
                    ):
                        continue
                    if href.startswith("http"):
                        markdown_link = (
                            f"[{text}]({href})" if text and text not in href else href
                        )
                        link_texts.append(markdown_link)

                for line in entry_soup.get_text(separator="\n").splitlines():
                    if "passcode" in line.lower():
                        passcode_lines.append(line.strip())

                if link_texts or passcode_lines:
                    body_text += "\n\n---\n📎 Supplemental content:\n"
                    if link_texts:
                        body_text += "\nLinks:\n" + "\n".join(link_texts)
                    if passcode_lines:
                        body_text += "\n\nPasscodes:\n" + "\n".join(passcode_lines)

                text_file_path = os.path.join(folder_path, f"entry_{entry_id}.txt")
                with open(text_file_path, "w", encoding="utf-8") as f:
                    f.write(body_text)
                print(f"📝 Saved text to {text_file_path}")

            except Exception as e:
                print(f"⚠️ Failed to fetch/save entry {entry_id} text: {e}")
                logging.warning(f"Failed to fetch entry {entry_id}: {e}", exc_info=True)
                continue  # Skip rest of processing if text download fails

            # -------------------------
            # Attachments
            # -------------------------
            attachments, seen_urls = [], set()
            attachment_tags = entry_soup.find_all("a", href=True)
            attachments_dir = None

            for a_tag in attachment_tags:
                href = a_tag["href"].strip()
                filename = a_tag.get_text(strip=True) or os.path.basename(href)
                full_url = urljoin(detail_url, href)
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                if not any(
                    href.lower().endswith(ext)
                    for ext in [
                        ".pdf",
                        ".txt",
                        ".csv",
                        ".root",
                        ".dat",
                        ".jpg",
                        ".png",
                        ".zip",
                    ]
                ):
                    continue
                if any(
                    bad in href
                    for bad in ["cmd=", "mailto:", "elog.psi.ch", "?id=", "../"]
                ):
                    continue

                if attachments_dir is None:
                    attachments_dir = os.path.join(folder_path, "attachments")
                    os.makedirs(attachments_dir, exist_ok=True)

                sanitized_filename = filename.replace("/", "_") or os.path.basename(
                    href
                )
                filepath = os.path.join(attachments_dir, sanitized_filename)

                try:
                    print(f"⬇️  Downloading: {full_url}")
                    file_resp = session.get(full_url, stream=True)
                    file_resp.raise_for_status()
                    with open(filepath, "wb") as f:
                        for chunk in file_resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    attachments.append(
                        {
                            "filename": sanitized_filename,
                            "url": full_url,
                            "mimetype": file_resp.headers.get("Content-Type"),
                            "size": int(file_resp.headers.get("Content-Length", 0)),
                        }
                    )
                except Exception as e:
                    print(f"❌ Failed to download {full_url}: {e}")
                    logging.warning(f"Attachment failed for entry {entry_id}: {e}")

            # -------------------------
            # Metadata
            # -------------------------
            metadata = {
                "ID": entry_id,
                "Date": timestamp_raw,
                "Author": author,
                "Author Email": author_email,
                "Category": category,
                "Status": status,
                "Subject": subject,
                "Text": f"entry_{entry_id}.txt",
                "Attachments": attachments,
            }

            metadata_path = os.path.join(folder_path, "metadata.json")
            try:
                with open(metadata_path, "w", encoding="utf-8") as json_file:
                    json.dump(metadata, json_file, indent=4, ensure_ascii=False)
                print(f"📄 Saved metadata to {metadata_path}")
            except Exception as e:
                print(f"⚠️ Failed to save metadata for entry {entry_id}: {e}")
                logging.warning(f"Metadata save failed: {e}")

        except Exception as e:
            print(f"❌ Failed to process entry on page {page_number}: {e}")
            logging.warning(f"Failed to process entry: {e}", exc_info=True)
            continue

    # Look for "Next" page
    next_link = soup.find("a", string="Next")
    if next_link and next_link.has_attr("href"):
        page_url = urljoin(ELOG_URL, next_link["href"])
        page_number += 1
        time.sleep(1.5)
    else:
        print("✅ Reached last page.")
        break

# -------------------------
# Final summary log
# -------------------------
logging.warning("✅ Scrape completed successfully.")
if num_entries_saved > 0:
    logging.warning(f"📝 Saved {num_entries_saved} new entries.")
    logging.warning(f"📌 Entry range: {first_entry_id} → {last_entry_id}")
else:
    logging.warning("📎 No new entries were saved.")

logging.warning(f"📂 Output folder: {DEST_DIR}")
logging.warning(f"🗓️  Run Timestamp: {timestamp}")

for handler in logging.root.handlers:
    handler.flush()
