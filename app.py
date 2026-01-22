from flask import Flask, render_template, jsonify, request, Response
from mahabhumi_scraper import MahabhumiScraper
import json
import requests

app = Flask(__name__)
# Global scraper instance
_scraper = None

def get_scraper():
    """Initializes and returns a singleton instance of the MahabhumiScraper."""
    global _scraper
    if _scraper is None:
        print("Initializing Scraper...")
        print("Initializing Scraper...", flush=True)
        _scraper = MahabhumiScraper()
        print("Scraper Initialized.", flush=True)
    return _scraper

@app.route('/')
def index():
    """Renders the main dashboard page."""
    print("INDEX HIT", flush=True)
    return render_template('index.html')

@app.route('/api/districts')
def get_districts():
    """API endpoint to fetch the list of districts for Maharashtra."""
    print("API: Districts", flush=True)
    category = request.args.get('category', 'R')
    districts = get_scraper().fetch_districts(category)
    return jsonify(districts)

@app.route('/api/talukas/<district_code>')
def get_talukas(district_code):
    """API endpoint to fetch talukas for a specific district."""
    print(f"API: Talukas {district_code}", flush=True)
    category = request.args.get('category', 'R')
    talukas = get_scraper().fetch_talukas(district_code, category)
    return jsonify(talukas)

@app.route('/api/villages/<district_code>/<taluka_code>')
def get_villages(district_code, taluka_code):
    """API endpoint to fetch villages for a specific taluka."""
    print(f"API: Villages {district_code}/{taluka_code}", flush=True)
    category = request.args.get('category', 'R')
    villages = get_scraper().fetch_villages(district_code, taluka_code, category)
    return jsonify(villages)

@app.route('/api/plots/<district_code>/<taluka_code>/<village_code>')
def get_plot_list(district_code, taluka_code, village_code):
    """API endpoint to fetch the list of survey/plot numbers for a village."""
    print(f"API: Plots {district_code}/{taluka_code}/{village_code}", flush=True)
    category = request.args.get('category', 'R')
    plots = get_scraper().fetch_plot_list(district_code, taluka_code, village_code, category)
    # Sort plots numerically if possible, otherwise string sort
    try:
        plots.sort(key=lambda x: int(x) if x.isdigit() else float(x) if x.replace('.','',1).isdigit() else x)
    except:
        plots.sort()
    return jsonify(plots)

@app.route('/api/wms')
def proxy_wms():
    """Proxies WMS requests to avoid CORS"""
    print("API: WMS Proxy", flush=True)
    wms_url = "https://mahabhunakasha.mahabhumi.gov.in/WMS"
    params = request.args.to_dict()
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mahabhunakasha.mahabhumi.gov.in/27/index.html"
        }
        
        # Ensure we request PNG and Transparency
        if 'FORMAT' not in params:
             params['FORMAT'] = 'image/png'
        
        # Force transparency parameters
        params['TRANSPARENT'] = 'TRUE'
        params['transparent'] = 'true' # sending both to be safe
             
        resp = requests.get(wms_url, params=params, headers=headers, stream=True)
        # We don't raise for status immediately to pass through error images if any
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/report')
def proxy_report():
    """Proxies Map Report (JSP) requests using the scraper's session"""
    print("API: Report Proxy", flush=True)
    # The user provided signplotreportpublic.jsp as the working public URL
    base_report_url = "https://mahabhunakasha.mahabhumi.gov.in/signplotreportpublic.jsp"
    
    params = request.args.to_dict()
    
    try:
        # Use the scraper's session to preserve cookies
        scraper = get_scraper()
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mahabhunakasha.mahabhumi.gov.in/27/index.html"
        }
        resp = scraper.session.get(base_report_url, params=params, headers=headers, timeout=20)
        
        # Rewrite any absolute URLs in the response to their base if needed?
        # Usually these JSPs return HTML or redirect to a PDF.
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        print(f"Report Proxy Error: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/village_boundaries/<giscode>')
def get_village_boundaries(giscode):
    """Fetches all plot boundaries for a village"""
    print(f"API: Village Boundaries for {giscode}", flush=True)
    try:
        boundaries = get_scraper().fetch_village_boundaries(giscode, max_plots=9999)
        return jsonify(boundaries)
    except Exception as e:
        print(f"Error fetching village boundaries: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/download_village_map/<giscode>')
def download_village_map(giscode):
    """Downloads the complete village map from government WMS as an image"""
    print(f"API: Download Village Map for {giscode}", flush=True)
    
    try:
        # First, get a sample of plot boundaries to calculate the bounding box
        scraper = get_scraper()
        boundaries = scraper.fetch_village_boundaries(giscode, max_plots=10)
        
        if not boundaries:
            return jsonify({"error": "No plot data found for this village"}), 404
        
        # Calculate bounding box from the sample plots
        import re
        min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')
        
        for plot in boundaries:
            # Extract coordinates from WKT geometry
            geom = plot['geometry']
            # Parse coordinates from MULTIPOLYGON or POLYGON
            coords = re.findall(r'([\d.]+)\s+([\d.]+)', geom)
            for x_str, y_str in coords:
                x, y = float(x_str), float(y_str)
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
        
        # Add 10% padding to the bounding box
        padding_x = (max_x - min_x) * 0.1
        padding_y = (max_y - min_y) * 0.1
        bbox = f"{min_x - padding_x},{min_y - padding_y},{max_x + padding_x},{max_y + padding_y}"
        
        print(f"Calculated BBOX: {bbox}", flush=True)
        
        wms_url = "https://mahabhunakasha.mahabhumi.gov.in/WMS"
        
        # WMS GetMap request parameters for village map
        params = {
            'SERVICE': 'WMS',
            'VERSION': '1.1.1',
            'REQUEST': 'GetMap',
            'LAYERS': 'VILLAGE_MAP',
            'STYLES': 'VILLAGE_MAP',
            'FORMAT': 'image/png',
            'TRANSPARENT': 'TRUE',
            'WIDTH': '2048',
            'HEIGHT': '2048',
            'SRS': 'EPSG:32643',  # UTM Zone 43N
            'BBOX': bbox,
            'gis_code': giscode,
            'state': '27'
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://mahabhunakasha.mahabhumi.gov.in/27/index.html"
        }
        
        # Get the map image
        resp = requests.get(wms_url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        
        # Return as downloadable file
        return Response(
            resp.content,
            mimetype='image/png',
            headers={
                'Content-Disposition': f'attachment; filename="village_map_{giscode}.png"'
            }
        )
        
    except Exception as e:
        print(f"Error downloading village map: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/plot')
def get_plot():
    """API endpoint to fetch detailed information and geometry for a specific plot."""
    print("API: Get Plot Info", flush=True)
    # Expecting parameters: category, district, taluka, village, plot_no
    # We need to construct the GIS code.
    # Format: Prefix(RVM/UVM) + District(2) + Taluka(2) + VillageCode(18)
    
    cat = request.args.get('category', 'R')
    dist = request.args.get('district')
    tal = request.args.get('taluka')
    vil_code = request.args.get('village_code') # This is the code from the village dropdown
    plot_no = request.args.get('plot_no')
    
    if not (dist and tal and vil_code and plot_no):
         return jsonify({"error": "Missing parameters"}), 400

    prefix = "RVM" if cat == 'R' else "UVM" 
    
    # Construct GIS Code
    full_gis_code = f"{prefix}{dist}{tal}{vil_code}"
    
    data = get_scraper().get_plot_coordinates(full_gis_code, plot_no)
    
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "Plot not found or API error"}), 404

if __name__ == '__main__':
    print("Starting Mahabhunakasha Scraper UI...", flush=True)
    print("Open http://localhost:5002 in your browser.", flush=True)
    app.run(debug=False, port=5002, threaded=True)
