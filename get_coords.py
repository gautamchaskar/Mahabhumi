import requests
import json

# Configuration
BASE_URL = "https://mahabhunakasha.mahabhumi.gov.in/27/rest/MapInfo"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded" 
}

def get_plot_coordinates(giscode, plot_number):
    """
    Fetches the polygon geometry for a given plot.
    
    Args:
        giscode (str): The 25-digit GIS code (Prefix + District + Taluka + Village).
                       Example construction: 'RVM' + Dist(05) + Tal(02) + Vil(270500020047510000)
        plot_number (str): The plot number to search for.
        
    Returns:
        str: WKT (Well-Known Text) geometry string or None if failed.
    """
    url = f"{BASE_URL}/getPlotInfo"
    
    # Payload
    # The application sends data as query parameters
    params = {
        "giscode": giscode,
        "plotno": plot_number,
        "state": "27"
    }
    
    try:
        print(f"Fetching data for Plot {plot_number}...")
        response = requests.post(url, headers=HEADERS, params=params)
        response.raise_for_status()
        
        # content-type might be text/html but body is json
        try:
            data = response.json()
        except json.JSONDecodeError:
            print("Failed to parse JSON response")
            print(response.text)
            return None
        
        if "the_geom" in data:
            print(f"Plot {plot_number} Found!")
            print("-" * 30)
            print("Geometry (WKT):")
            print(data["the_geom"])
            print("-" * 30)
            return data["the_geom"]
        else:
            print("Geometry not found in response.")
            # Check for error messages or empty results
            print("Response:", data)
            return None
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

# Example Usage
if __name__ == "__main__":
    # Example: District Akola (05), Taluka Akot (02), Village Akolkhed
    # Note: You can find these codes in the HTML or by inspecting the 'value' of dropdowns on the site.
    GIS_CODE = "RVM0502270500020047510000"
    PLOT_NO = "100"

    get_plot_coordinates(GIS_CODE, PLOT_NO)
