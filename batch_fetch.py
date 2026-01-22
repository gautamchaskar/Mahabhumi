from mahabhumi_scraper import MahabhumiScraper
import sys

def batch_fetch():
    # Disable auto-save for performance
    scraper = MahabhumiScraper(auto_save=False)
    
    # Default: Sakore Village (from previous logs)
    # RVM2502272500020303690000
    # District: 25 (Pune), Taluka: 02 (Ambegaon), Village: 272500020303690000
    
    print("--- Mahabhumi Batch Fetcher ---")
    print("This script will fetch all plots for a village and cache them.")
    
    # Hardcoded for convenience based on user context, but could be interactive
    default_gis_code = "RVM2502272500020303690000"
    
    gis_code = input(f"Enter GIS Code (default: {default_gis_code}): ").strip()
    if not gis_code:
        gis_code = default_gis_code
        
    try:
        workers = int(input("Enter number of threads (default: 20): ").strip() or "20")
    except:
        workers = 20
        
    print(f"Starting batch fetch for {gis_code} with {workers} workers...")
    
    boundaries = scraper.fetch_village_boundaries(gis_code, max_plots=9999, max_workers=workers)
    
    print("Saving cache to disk...")
    scraper.save_cache()
    
    print(f"Done! Fetched {len(boundaries)} plots.")
    print(f"Cache is populated in {scraper.CACHE_FILE}")

if __name__ == "__main__":
    batch_fetch()
