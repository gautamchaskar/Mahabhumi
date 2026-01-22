from mahabhumi_scraper import MahabhumiScraper
import json

def test_fetch_plots():
    """
    Test script to verify the sequence of API calls required to fetch plot lists.
    Demonstrates the level-based navigation (District -> Taluka -> Village -> Plots).
    """
    scraper = MahabhumiScraper()
    
    # We need a valid village code to test.
    # Level 1: Rural
    districts = scraper.fetch_districts('R')
    if not districts:
        print("Failed to fetch districts")
        return

    # Pick first district (e.g. Akola)
    dist = districts[0] 
    print(f"District: {dist['value']} ({dist['code']})")

    # Pick first taluka
    talukas = scraper.fetch_talukas(dist['code'], 'R')
    if not talukas:
         print("Failed to fetch talukas")
         return
    tal = talukas[0]
    print(f"Taluka: {tal['value']} ({tal['code']})")
    
    # Pick first village
    villages = scraper.fetch_villages(dist['code'], tal['code'], 'R')
    if not villages:
        print("Failed to fetch villages")
        return
    vil = villages[0]
    print(f"Village: {vil['value']} ({vil['code']})")

    # TEST LEVEL 5
    # Hypothesis: Level 5 with "R,Dist,Tal,Vil,VM," returns plots
    print("\n--- Testing Level 5 (Plots?) ---")
    # Added "VM" (Village Map) to the codes
    codes_l5 = f"R,{dist['code']},{tal['code']},{vil['code']},VM,"
    
    try:
        plots = scraper._fetch_level(5, codes_l5)
        if plots:
            print(f"Success! Found {len(plots)} items.")
            print("First 5 items:")
            print(json.dumps(plots[:5], indent=2))
        else:
            print("Level 5 returned empty list.")
    except Exception as e:
        print(f"Level 5 request failed: {e}")

if __name__ == "__main__":
    test_fetch_plots()
