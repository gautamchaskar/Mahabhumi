import requests
import json
import time

class MahabhumiScraper:
    BASE_URL = "https://mahabhunakasha.mahabhumi.gov.in/rest"
    
    def __init__(self):
        # Initialize a persistent session for cookie management
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://mahabhunakasha.mahabhumi.gov.in/27/index.html",
            "X-Requested-With": "XMLHttpRequest"
        })
        # Removed the blocking initial request to prevent server hangs on startup

    def _post(self, url, data, timeout=15):
        """
        Helper to handle the 302 cookie dance and ensure POST method is preserved.
        """
        try:
            # We don't allow automatic redirects because they often turn POST into GET (causing 405)
            response = self.session.post(url, data=data, timeout=timeout, allow_redirects=False)
            
            # Handle the 302 cookie dance if necessary
            if response.status_code == 302:
                print(f"Cookie challenge (302) on {url.split('/')[-1]} detected, retrying...", flush=True)
                response = self.session.post(url, data=data, timeout=timeout)
                
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"POST Error to {url}: {e}", flush=True)
            raise

    def _fetch_level(self, level, codes):
        """
        Generic method to fetch dropdown levels with 302 cookie handling.
        """
        url = f"{self.BASE_URL}/VillageMapService/ListsAfterLevelGeoref"
        payload = {
            "state": "27",
            "level": str(level),
            "codes": codes,
            "hasmap": "true"
        }
        
        try:
            print(f"POST Request to: {url} with codes: {codes}", flush=True)
            response = self._post(url, payload)
            
            print(f"Success: Level {level}", flush=True)
            return response.json()
        except Exception as e:
            print(f"Error fetching level {level}: {e}", flush=True)
            return []

    def fetch_districts(self, category='R'):
        """
        Fetches the list of districts for a given category.
        Category: 'R' (Rural) or 'U' (Urban)
        """
        print(f"Fetching Districts for Category: {category}...")
        # Level 1 request requires just the category code
        codes = f"{category}," 
        data = self._fetch_level(1, codes)
        
        # The response is a list of lists. The first list contains the districts.
        if data and len(data) > 0:
            return data[0]
        return []

    def fetch_talukas(self, district_code, category='R'):
        """
        Fetches talukas for a specific district.
        """
        print(f"Fetching Talukas for District: {district_code}...")
        # Level 2 requires "Category,DistrictCode,"
        codes = f"{category},{district_code},"
        data = self._fetch_level(2, codes)
        
        if data and len(data) > 0:
            return data[0] # The API returns the list in the first element
        return []

    def fetch_villages(self, district_code, taluka_code, category='R'):
        """
        Fetches villages for a specific taluka.
        """
        print(f"Fetching Villages for Taluka: {taluka_code}...")
        # Level 3 requires "Category,DistrictCode,TalukaCode,"
        codes = f"{category},{district_code},{taluka_code},"
        data = self._fetch_level(3, codes)
        
        if data and len(data) > 0:
            return data[0]
        return []

    def get_plot_coordinates(self, giscode, plot_number):
        """
        Fetches geometry for a specific plot.
        """
        url = f"{self.BASE_URL}/MapInfo/getPlotInfo"
        params = {
            "giscode": giscode,
            "plotno": plot_number,
            "state": "27"
        }
        print(f"Fetching Plot Coordinates: {giscode} - {plot_number}...", flush=True)
        
        try:
            # Send POST request to fetch plot details
            response = self._post(url, params)
            response.raise_for_status()
            data = response.json()
            if "the_geom" in data:
                print(f"Plot {plot_number} Found!")
                # Parse the 'info' string which contains Owner Name, Area, etc.
                # Example format:
                # Survey No. : 100\nTotal Area : 1.01\n...
                if "info" in data and data["info"]:
                    info_text = data["info"]
                    parsed_records = []
                    
                    # Split by the separator line
                    chunks = info_text.split('---------------------------------')
                    
                    for chunk in chunks:
                        if not chunk.strip():
                            continue
                            
                        record = {}
                        lines = chunk.strip().split('\n')
                        for line in lines:
                            if ':' in line:
                                key, val = line.split(':', 1)
                                record[key.strip()] = val.strip()
                        
                        if record:
                            parsed_records.append(record)
                    
                    data['parsed_records'] = parsed_records

                # Rewrite infoLinks to use our local proxy
                if "infoLinks" in data and data["infoLinks"]:
                    # Handle both variants and relative paths
                    data["infoLinks"] = data["infoLinks"].replace("../signplotreport.jsp", "/api/report")
                    data["infoLinks"] = data["infoLinks"].replace("signplotreport.jsp", "/api/report")
                    data["infoLinks"] = data["infoLinks"].replace("signplotreportpublic.jsp", "/api/report")
                    
            # The raw data is already in 'data', so no extra work needed here.
            # Just ensuring we return it.
            return data
        except Exception as e:
            print(f"Error fetching plot {plot_number}: {e}")
            return None

    def fetch_plot_list(self, district_code, taluka_code, village_code, category='R'):
        """
        Fetches the list of available plot numbers for a village.
        """
        url = f"{self.BASE_URL}/VillageMapService/kidelistFromGisCodeMH"
        
        # Construct logedLevels (GIS Code for Village)
        # Format: RVM/UVM (3) + District(2) + Taluka(2) + VillageCode(18)
        prefix = "RVM" if category == 'R' else "UVM"
        gis_code = f"{prefix}{district_code}{taluka_code}{village_code}"
        
        params = {
            "state": "27",
            "logedLevels": gis_code
        }
        
        print(f"Fetching Plot List for GIS Code: {gis_code}...")
        
        try:
            response = self.session.post(url, data=params, timeout=15) # Found to be POST by subagent
            response.raise_for_status()
            print(f"Success: Plot List Fetched ({len(response.json())} plots)")
            # Returns a list of strings: ["1", "2", "10", ...]
            return response.json()
        except Exception as e:
            print(f"Error fetching plot list: {e}")
            return []

    def fetch_village_boundaries(self, giscode, max_plots=9999):
        """
        Fetches geometries for all plots in a village (limited to max_plots for performance).
        Returns a list of dicts with plot_no and geometry.
        """
        print(f"Fetching village boundaries for {giscode}...", flush=True)
        
        # Extract components from giscode
        # Format: RVM2502272500020303690000 -> prefix(3) + district(2) + taluka(2) + village(18)
        prefix = giscode[:3]
        district = giscode[3:5]
        taluka = giscode[5:7]
        village = giscode[7:]
        category = 'R' if prefix == 'RVM' else 'V'
        
        # Get list of all plots
        plot_list = self.fetch_plot_list(district, taluka, village, category)
        
        if not plot_list:
            print("No plots found in village", flush=True)
            return []
        
        # Limit to max_plots to avoid timeout
        plots_to_fetch = plot_list[:max_plots]
        print(f"Fetching geometries for {len(plots_to_fetch)} plots (limited from {len(plot_list)} total)...", flush=True)
        
        boundaries = []
        for plot_no in plots_to_fetch:
            try:
                plot_data = self.get_plot_coordinates(giscode, plot_no)
                if plot_data and 'the_geom' in plot_data:
                    boundaries.append({
                        'plot_no': plot_no,
                        'geometry': plot_data['the_geom']
                    })
            except Exception as e:
                print(f"Error fetching plot {plot_no}: {e}", flush=True)
                continue
        
        print(f"Successfully fetched {len(boundaries)} plot boundaries", flush=True)
        return boundaries

def save_metadata(data, filename="metadata.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved metadata to {filename}")

if __name__ == "__main__":
    scraper = MahabhumiScraper()
    
    # 1. Fetch Districts
    districts = scraper.fetch_districts()
    print(f"Found {len(districts)} districts.")
    
    # Example: Process only the first district to demonstrate
    if districts:
        first_dist = districts[0]
        dist_code = first_dist['code']
        dist_name = first_dist['value']
        print(f"Processing District: {dist_name} ({dist_code})")
        
        # 2. Fetch Talukas for this district
        talukas = scraper.fetch_talukas(dist_code)
        print(f"  Found {len(talukas)} talukas.")
        
        if talukas:
            first_tal = talukas[0]
            tal_code = first_tal['code']
            tal_name = first_tal['value']
            print(f"  Processing Taluka: {tal_name} ({tal_code})")
            
            # 3. Fetch Villages for this taluka
            villages = scraper.fetch_villages(dist_code, tal_code)
            print(f"    Found {len(villages)} villages.")
            
            if villages:
                first_village = villages[0]
                vil_code_raw = first_village['code']
                vil_name = first_village['value']
                
                print(f"    Target Village: {vil_name} ({vil_code_raw})")
                
                full_gis_code = f"RVM{dist_code}{tal_code}{vil_code_raw}"
                print(f"    Constructed GIS Code: {full_gis_code}")
                
                # 4. Try to fetch a plot
                plot_data = scraper.get_plot_coordinates(full_gis_code, "1")
                if plot_data and 'the_geom' in plot_data:
                    print("    Successfully fetched plot 1 geometry!")
                else:
                    print("    No geometry found for plot 1.")

    # Save the district list for reference
    save_metadata(districts, "districts.json")
