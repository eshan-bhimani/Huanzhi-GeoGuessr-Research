import os
import sys
import csv
import requests

# Add parent directory to path to allow importing constants
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import google_api_key

def main():
    csv_path = "BenchmarkDataset.csv"
    val_dir = "val"
    
    if not os.path.exists(val_dir):
        os.makedirs(val_dir)
        print(f"Created directory: {val_dir}")

    locations = []
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row['Latitude'])
                lng = float(row['Longitude'])
                locations.append((lat, lng))
            except (ValueError, KeyError):
                continue

    total = len(locations)
    print(f"Validating {total} locations from {csv_path}...")

    stats = {
        "ok": 0,
        "missing": 0,
        "error": 0
    }

    for i, (lat, lng) in enumerate(locations):
        entry_num = i + 1
        print(f"[{entry_num}/{total}] Checking {lat}, {lng}...", end=" ", flush=True)

        # 1. Metadata API Request
        meta_url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lng}&key={google_api_key}"
        try:
            meta_resp = requests.get(meta_url).json()
            status = meta_resp.get("status")
            pano_id = meta_resp.get("pano_id", "NO_PANO")
            
            # 2. Static API Request (Save Image) - ALWAYS save if possible
            img_url = f"https://maps.googleapis.com/maps/api/streetview?size=640x640&location={lat},{lng}&key={google_api_key}"
            
            if status == "OK":
                img_name = f"entry_{entry_num}_OK_{lat}_{lng}.jpg"
            else:
                img_name = f"entry_{entry_num}_{status}_{lat}_{lng}.jpg"
                
            img_path = os.path.join(val_dir, img_name)
            
            img_data = requests.get(img_url).content
            with open(img_path, 'wb') as img_file:
                img_file.write(img_data)

            if status == "OK":
                print(f"OK (Pano: {pano_id})")
                stats["ok"] += 1
            elif status == "ZERO_RESULTS":
                print("MISSING (Zero Results)")
                stats["missing"] += 1
            else:
                print(f"ERROR: {status}")
                stats["error"] += 1
        except Exception as e:
            print(f"EXCEPTION: {e}")
            stats["error"] += 1

    print("\n--- Validation Summary ---")
    print(f"Total Locations: {total}")
    print(f"Successfully Validated (Saved): {stats['ok']}")
    print(f"Missing (No Street View): {stats['missing']}")
    print(f"Errors/API Failures: {stats['error']}")

if __name__ == "__main__":
    main()
