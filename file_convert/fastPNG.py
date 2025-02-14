import os
import argparse
import time
import datetime
import shutil
from pdf2image import convert_from_path
from tqdm import tqdm
from multiprocessing import Pool, cpu_count

# Try importing PDFPageCountError, otherwise define a fallback
try:
    from pdf2image.exceptions import PDFPageCountError
except ImportError:
    class PDFPageCountError(Exception):
        """Fallback error class if pdf2image doesn't provide PDFPageCountError."""
        pass

# Function to read filenames from a text file
def read_filenames(filename_list):
    """Reads a list of filenames from a text file."""
    with open(filename_list, "r") as file:
        return [line.strip() for line in file if line.strip()]

# Function to check if a PDF is valid
def check_pdf(pdf_path):
    """Attempts to read the page count of a PDF to verify it is not corrupted."""
    try:
        _ = len(convert_from_path(pdf_path, dpi=10))  # Low DPI for fast check
        return None  # No error
    except PDFPageCountError as e:
        return f"ERROR: Unable to process {pdf_path}. PDF might be corrupted. Skipping.\n{str(e)}\n"
    except Exception as e:
        return f"ERROR: Unexpected failure while processing {pdf_path}. Skipping.\n{str(e)}\n"

# Function to check disk space before processing
def check_disk_space(required_gb=10):
    """Check if at least 'required_gb' of free space is available."""
    total, used, free = shutil.disk_usage("/")
    free_gb = free / (1024**3)
    if free_gb < required_gb:
        print(f"⚠️ WARNING: Low disk space! Only {free_gb:.2f} GB free.")
        return False
    return True

# Function to convert a single PDF and rename output images
def convert_pdf(pdf_info):
    """Converts a PDF file to PNG images using multiprocessing, with error handling."""
    pdf_path, filenames, dpi = pdf_info
    pdf_dir = os.path.dirname(pdf_path)
    
    # Check if PNGs already exist
    all_pngs_exist = all(os.path.exists(os.path.join(pdf_dir, filenames[i])) for i in range(len(filenames)))
    if all_pngs_exist:
        print(f"⏩ Skipping already processed PDF: {pdf_path}")
        return  # Skip this PDF

    start_time = time.time()  # Start timing
    try:
        images = convert_from_path(pdf_path, dpi=dpi, fmt="png", thread_count=cpu_count())
        for i, image in enumerate(images):
            filename = filenames[i] if i < len(filenames) else f"default_page_{i+1}.png"
            image.save(os.path.join(pdf_dir, filename), "PNG")

        end_time = time.time()
        print(f"✅ Processed {pdf_path} in {end_time - start_time:.2f} sec")

    except PDFPageCountError:
        log_error(f"ERROR: Skipping corrupt PDF {pdf_path}")
    except Exception as e:
        log_error(f"ERROR: Unexpected failure in {pdf_path}: {str(e)}")

# Function to log errors to a file

def log_error(message, log_file=None):
    """Logs errors with timestamps, auto-generating a unique log file if not specified."""
    if log_file is None:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_file = f"error_log_{timestamp}.txt"

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_message = f"[{timestamp}] {message}\n"
    print(full_message)
    with open(log_file, "a") as f:
        f.write(full_message)


# Function to batch check PDFs inside subdirectories using multiprocessing
def batch_check_pdfs(parent_dir, num_workers):
    """Checks all PDFs inside 'COIN_NPS_50k_replay_*/' directories in parallel without converting them."""
    start_time = time.time()
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = f"error_log_{timestamp}.txt"  # ✅ Generate timestamped log file

    run_dirs = sorted([os.path.join(parent_dir, d) for d in os.listdir(parent_dir) 
                       if os.path.isdir(os.path.join(parent_dir, d)) and d.startswith("COIN_NPS_50k_replay_")])

    pdf_files = [os.path.join(run_dir, f) for run_dir in run_dirs for f in os.listdir(run_dir) if f.endswith(".pdf")]
    print(f"🔍 Checking {len(pdf_files)} PDFs for errors using {num_workers} cores...\n")

    with Pool(num_workers) as pool:
        results = list(tqdm(pool.imap_unordered(check_pdf, pdf_files), total=len(pdf_files), desc="Checking PDFs"))

    with open(log_filename, "w") as log_file:  # ✅ Now uses the timestamped log file
        for error_msg in results:
            if error_msg:
                log_error(error_msg, log_file=log_filename)

    print("\n✅ PDF check complete!")
    print(f"📄 Check '{log_filename}' for any corrupted PDFs.")
    print(f"⏳ Total Execution Time: {time.time() - start_time:.2f} seconds")

# Function to batch convert PDFs inside subdirectories using multiprocessing
def batch_convert(parent_dir, filename_list, dpi, num_workers):
    """Processes PDFs inside 'COIN_NPS_50k_replay_*/' directories in parallel, skipping already processed ones."""
    if not check_disk_space(10):  # Require at least 10GB free
        print("⚠️ Not enough space! Exiting to prevent failures.")
        exit(1)

    start_time = time.time()
    run_dirs = sorted([os.path.join(parent_dir, d) for d in os.listdir(parent_dir) 
                       if os.path.isdir(os.path.join(parent_dir, d)) and d.startswith("COIN_NPS_50k_replay_")])

    filenames = read_filenames(filename_list)
    pdf_files = [os.path.join(run_dir, f) for run_dir in run_dirs for f in os.listdir(run_dir) if f.endswith(".pdf")]

    print(f"📄 Processing {len(pdf_files)} PDFs at {dpi} DPI using {num_workers} cores...\n")

    with Pool(num_workers) as pool:
        pool.map(convert_pdf, [(pdf, filenames, dpi) for pdf in pdf_files])

    print("\n✅ Conversion complete!")
    print(f"⏳ Total Execution Time: {time.time() - start_time:.2f} seconds")

# Command-line argument parser
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fast batch convert or check PDFs inside subdirectories using multiprocessing.")
    parser.add_argument("parent_dir", type=str, help="Parent directory containing 'COIN_NPS_50k_replay_*' subdirectories.")
    parser.add_argument("filename_list", type=str, nargs="?", default=None, help="Text file with list of output filenames (only needed for conversion).")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for conversion (default: 300).")
    parser.add_argument("--num-workers", type=int, default=cpu_count(), help="Number of parallel workers (default: max cores).")
    parser.add_argument("--check-only", action="store_true", help="Only check PDFs for corruption, do not convert.")

    args = parser.parse_args()

    if args.check_only:
        batch_check_pdfs(args.parent_dir, args.num_workers)
    else:
        batch_convert(args.parent_dir, args.filename_list, args.dpi, args.num_workers)
