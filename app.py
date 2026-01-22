from flask import Flask, render_template, jsonify, request, Response
from mahabhumi_scraper import MahabhumiScraper
import json
import requests
import ezdxf
import io
import zipfile
import math
from PIL import Image

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

@app.route('/api/download_dxf', methods=['POST'])
def download_dxf():
    """Generates and returns an AutoCAD DXF file from plot geometries."""
    print("API: Download DXF", flush=True)
    try:
        data = request.json
        if not data or 'plots' not in data:
            return jsonify({"error": "No plot data provided"}), 400
        
        # Create a new DXF document
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        
        # Set PDMODE to make points visible (34 = Circle with X, 3 = X, 2 = +)
        # 34 is good for visibility
        doc.header['$PDMODE'] = 34
        # Set PDSIZE (0 = 5% of screen, >0 = absolute size, <0 = % of viewport)
        # We'll leave it 0 or set a small absolute size if needed, but 0 is usually fine for "screen relative"
        # or we can try setting it to a small fixed value if we knew the scale.
        # Let's stick to PDMODE for now.
        
        # Set Point Style to Circle with Cross (35)
        doc.header['$PDMODE'] = 35
        doc.header['$PDSIZE'] = 1.0 # 1 meter size
        
        # Setup layers
        doc.layers.new(name='PLOT_BOUNDARIES', dxfattribs={'color': 1}) # Red
        doc.layers.new(name='COORDINATE_LABELS', dxfattribs={'color': 2}) # Yellow
        doc.layers.new(name='PLOT_NUMBERS', dxfattribs={'color': 3}) # Green
        doc.layers.new(name='METADATA', dxfattribs={'color': 4}) # Cyan
        
        msp = doc.modelspace()
        
        all_x = []
        all_y = []
        
        for plot in data['plots']:
            label = plot.get('label', 'Unnamed Plot')
            coords = plot.get('coordinates', [])
            
            if not coords:
                continue
            
            def process_ring(ring_coords, is_hole=False):
                if not ring_coords or not isinstance(ring_coords, list): return []
                
                # Check if ring_coords is [ [lng, lat], ... ]
                if isinstance(ring_coords[0], (list, tuple)) and not isinstance(ring_coords[0][0], (list, tuple)):
                    poly_pts = [(float(p[0]), float(p[1])) for p in ring_coords]
                    if len(poly_pts) < 2: return []
                    
                    # Store for bounding box
                    for x, y in poly_pts:
                        all_x.append(x)
                        all_y.append(y)
                    
                    if poly_pts[0] != poly_pts[-1]:
                        poly_pts.append(poly_pts[0])
                    
                    # Add plot boundary
                    msp.add_lwpolyline(poly_pts, format='xy', dxfattribs={'layer': 'PLOT_BOUNDARIES'})
                    return poly_pts
                else:
                    # It's a list of rings (multipolygon or nested)
                    all_pts = []
                    for i, sub in enumerate(ring_coords):
                        pts = process_ring(sub, is_hole=(i > 0))
                        if pts: all_pts.extend(pts)
                    return all_pts

            vertices = process_ring(coords)
            
            if vertices:
                # We'll calculate text height later once we have the full bounding box
                # But for now, we'll place them and update if needed (or just use a sensible default)
                # Sensible default will be determined after processing all plots.
                pass

        # Calculate a reasonable text height based on bounding box
        if all_x and all_y:
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
            width = max_x - min_x
            height = max_y - min_y
            size = max(width, height)
            
            # If size is very small (like degrees), text height should be small
            # If size is large (like meters), text height should be larger
            # If size is large (like meters), text height should be larger
            # User requested smaller text. 
            # Previous: size * 0.01. Let's try 0.002 (0.2%)
            text_h = size * 0.002 if size > 0 else 0.1
            if text_h == 0: text_h = 0.1
            
            # Now add labels and coordinates
            for plot in data['plots']:
                label = plot.get('label', 'Unnamed Plot')
                coords = plot.get('coordinates', [])
                
                def add_labels(ring_coords, p_label, metadata):
                    if not ring_coords or not isinstance(ring_coords, list): return
                    if isinstance(ring_coords[0], (list, tuple)) and not isinstance(ring_coords[0][0], (list, tuple)):
                        poly_pts = [(float(p[0]), float(p[1])) for p in ring_coords]
                        
                        # Calculate Centroid for Label
                        xs = [p[0] for p in poly_pts]
                        ys = [p[1] for p in poly_pts]
                        cx = sum(xs) / len(xs)
                        cy = sum(ys) / len(ys)

                        # Clean label (Remove 'Gat-' if present to just show number)
                        clean_label = p_label.replace('Gat-', '')

                        # Add Plot Label at center
                        # User requested smaller survey numbers
                        msp.add_text(clean_label, dxfattribs={
                            'height': text_h * 0.8, # Reduced from 1.5
                            'insert': (cx, cy),
                            'layer': 'PLOT_NUMBERS',
                            'color': 3
                        })
                        
                        # Add explicit POINT entities at vertices for selection
                        for x, y in poly_pts:
                            msp.add_point((x, y), dxfattribs={'layer': 'COORDINATE_LABELS'})
                            
                            # Removed per-vertex text labels to reduce clutter as per user request.
                            # Coordinates can be viewed by selecting the point in CAD.
                    else:
                        for sub in ring_coords:
                            add_labels(sub, p_label, metadata)
                
                add_labels(coords, label, plot.get('owner_info', []))

        # --- WMS Image Embedding Logic ---
        # 1. Calculate Bounding Box
        if all_x and all_y:
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
            
            # Add some padding (5%)
            width = max_x - min_x
            height = max_y - min_y
            pad_x = width * 0.05
            pad_y = height * 0.05
            
            bbox = [min_x - pad_x, min_y - pad_y, max_x + pad_x, max_y + pad_y]
            
            # 2. Fetch WMS Image
            # We need the village code. We can get it from the first plot's GIS code if available,
            # or pass it from frontend. The frontend passes 'plots' list.
            # Let's try to extract it from the first plot's owner info or just use the one from the request if we had it.
            # But the /download_dxf endpoint only gets the list of coords.
            # However, we can infer the village code from the layer name if we had it, but we don't.
            # Actually, the user selects a village, so all plots are from one village.
            # We can try to guess the village code or just ask the user to pass it.
            # For now, let's try to find a GIS code in the plot data.
            village_code = None
            for p in data['plots']:
                # Check if we have giscode in the plot object (we might not if it's just coords)
                # The frontend sends: label, coordinates, owner_info.
                # It does NOT send giscode directly in the simplified object.
                # But wait, the frontend `plottedCoordinates` push does NOT include giscode.
                # We might need to update frontend to send village code.
                # OR we can just use the WMS bounds to fetch the image without layer filter?
                # No, Mahabhumi WMS usually requires a layer.
                # Actually, we can use the "VillageMap" layer or similar if generic.
                # But better to use the specific village code if possible.
                pass

            # Update: We will try to fetch the image using the bounding box.
            # The WMS URL: https://mahabhunakasha.mahabhumi.gov.in/WMS
            # Layers: We need the village code. 
            # Let's assume for now we can't get the village code easily without frontend change.
            # BUT, we can try to fetch without a specific layer or use a wildcard? Unlikely.
            # Let's look at the frontend code again. `plottedCoordinates` has `label`.
            # We really need the village code.
            # Let's Modify the frontend to send `village_code` in the request body.
            
            # Assuming we will update frontend to send 'village_code'
            village_code = request.json.get('village_code')
            
            wms_image_data = None
            if village_code:
                try:
                    # Calculate image size (max 2048px)
                    img_w = 2048
                    img_h = int(img_w * (height / width))
                    if img_h > 2048:
                        img_h = 2048
                        img_w = int(img_h * (width / height))
                        
                    wms_params = {
                        "SERVICE": "WMS",
                        "VERSION": "1.1.1",
                        "REQUEST": "GetMap",
                        "FORMAT": "image/png",
                        "TRANSPARENT": "TRUE",
                        "LAYERS": village_code,
                        "SRS": "EPSG:32643", # Assuming Zone 43N, need to be careful if it's 44N
                        # We need to know the projection. The frontend sends coords in a specific projection.
                        # `currentProj` in frontend decides this.
                        # We should probably ask frontend for the EPSG code too.
                        "STYLES": "",
                        "WIDTH": str(img_w),
                        "HEIGHT": str(img_h),
                        "BBOX": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
                    }
                    
                    # Check projection from request or default
                    epsg = request.json.get('epsg', 'EPSG:32643')
                    wms_params['SRS'] = epsg
                    
                    print(f"Fetching WMS Image for DXF: {wms_params}", flush=True)
                    resp = requests.get("https://mahabhunakasha.mahabhumi.gov.in/WMS", params=wms_params, stream=True)
                    if resp.status_code == 200:
                        wms_image_data = resp.content
                    else:
                        print(f"WMS Fetch Failed: {resp.status_code}", flush=True)
                except Exception as e:
                    print(f"WMS Error: {e}", flush=True)

            if wms_image_data:
                # Embed in DXF
                # 1. Add Image Definition
                image_def = msp.add_image_def(filename='village_map.png', size_in_pixel=(img_w, img_h))
                
                # 2. Add Image Entity
                # Position: Bottom-Left corner of BBOX
                # Size: Width and Height in map units
                msp.add_image(
                    insert=(bbox[0], bbox[1]),
                    size_in_units=(bbox[2]-bbox[0], bbox[3]-bbox[1]),
                    image_def=image_def,
                    rotation=0,
                    dxfattribs={'layer': 'MAP_IMAGE'}
                )
                
                # Move image to bottom (draw order) - ezdxf doesn't strictly support draw order manipulation easily in all viewers
                # but adding it first or last might help. We added it last here.
                # Actually, usually background should be added first? 
                # DXF draw order is usually order of entities.
                # Let's try to move it to the beginning of the modelspace if possible, or just rely on CAD layer management.
                # For now, we append it.

        # Save DXF
        out_stream = io.StringIO()
        doc.write(out_stream)
        dxf_content = out_stream.getvalue()

        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add DXF
            zip_file.writestr("mahabhumi_export.dxf", dxf_content)
            
            # Add Image if available
            if wms_image_data:
                zip_file.writestr("village_map.png", wms_image_data)
        
        zip_buffer.seek(0)
        
        return Response(
            zip_buffer,
            mimetype='application/zip',
            headers={
                'Content-Disposition': 'attachment; filename="mahabhumi_export.zip"'
            }
        )
        
    except Exception as e:
        print(f"DXF Export Error: {e}", flush=True)
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

@app.route('/api/plots/batch', methods=['POST'])
def get_plots_batch():
    """Batch API to check cache for multiple plots."""
    print("API: Batch Get Plots", flush=True)
    req_data = request.json
    village_code = req_data.get('village_code')
    plot_nos = req_data.get('plot_nos', [])
    
    if not village_code or not plot_nos:
        return jsonify({"error": "Missing parameters"}), 400
        
    # Construct GIS codes and check cache
    # We need to know the prefix (RVM/UVM) and district/taluka from somewhere.
    # Actually, the cache key is just the GIS code.
    # But we only have village_code (which is usually full 18 digit or similar?)
    # Wait, the village code in the dropdown is just the village ID part?
    # Let's check how `get_plot` constructs it.
    # `get_plot` takes: cat, dist, tal, vil_code.
    # Full GIS = Prefix + Dist + Tal + VilCode.
    # The frontend `els.vil.value` seems to be the village code.
    # But we need the full GIS code prefix to check the cache efficiently if we don't have it.
    # However, the `scraper.get_plot_coordinates` uses `full_gis_code`.
    # The cache `all_plots.json` is a list of plot objects.
    # We can search the cache by `giscode` + `plotno`.
    # Or simpler: The frontend sends the FULL GIS CODE if it has it?
    # No, the frontend only has the village code selected in the dropdown.
    # And the `get_plot` endpoint constructs the full code.
    # We need the same logic here.
    # We can accept `category`, `district`, `taluka` in the batch request too.
    
    cat = req_data.get('category', 'R')
    dist = req_data.get('district')
    tal = req_data.get('taluka')
    
    if not (dist and tal):
         return jsonify({"error": "Missing district/taluka"}), 400

    prefix = "RVM" if cat == 'R' else "UVM"
    full_gis_code_base = f"{prefix}{dist}{tal}{village_code}"
    
    found_plots = []
    missing_plots = []
    
    scraper = get_scraper()
    
    # We can optimize this by loading the cache once (it's already loaded in scraper)
    # Scraper has `all_plots` list.
    # We need to filter by giscode and plotno.
    # Indexing would be better, but iterating is okay for now if not too huge.
    # Actually, `scraper.get_plot_coordinates` checks cache.
    # But it also fetches if missing. We only want to CHECK cache.
    
    # Let's peek into scraper's cache directly or add a method to scraper.
    # Since I can't easily modify the scraper class instance method without reloading,
    # I will access `scraper.all_plots` directly if possible.
    # `all_plots` is a list of dicts.
    
    # Create a lookup for the requested village to speed up
    # This might be slow if `all_plots` is huge.
    # But `all_plots` is in memory.
    
    # Filter cache for this village first
    village_cache = [p for p in scraper.all_plots if p.get('giscode') == full_gis_code_base]
    village_map = {p['plotno']: p for p in village_cache}
    
    for plot_no in plot_nos:
        if plot_no in village_map:
            found_plots.append(village_map[plot_no])
        else:
            missing_plots.append(plot_no)
            
    return jsonify({
        "found": found_plots,
        "missing": missing_plots
    })

if __name__ == '__main__':
    print("Starting Mahabhunakasha Scraper UI...", flush=True)
    print("Open http://localhost:5002 in your browser.", flush=True)
    app.run(debug=False, port=5002, threaded=True)
