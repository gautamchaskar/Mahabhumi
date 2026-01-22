import os
import json
import ezdxf
import re
import math

OUTPUT_FILE = "mahabhumi_all_plots.dxf"

def parse_wkt_rings(wkt):
    """
    Parses WKT (MULTIPOLYGON/POLYGON) and returns a list of rings.
    Each ring is a list of (x, y) tuples.
    """
    matches = re.findall(r'\(([\d\.\s,]+)\)', wkt)
    
    rings = []
    for m in matches:
        pairs = m.strip().split(',')
        ring_coords = []
        for pair in pairs:
            parts = pair.strip().split()
            if len(parts) >= 2:
                try:
                    x = float(parts[0])
                    y = float(parts[1])
                    ring_coords.append((x, y))
                except:
                    pass
        if ring_coords:
            rings.append(ring_coords)
    return rings

def calculate_polygon_properties(coords):
    """
    Calculates the centroid and approximate bounding box size of a polygon.
    Uses the signed area method for centroid.
    """
    n = len(coords)
    if n < 3:
        # Fallback for lines/points
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]
        return (sum(xs)/n, sum(ys)/n), 0, 0

    area = 0.0
    cx = 0.0
    cy = 0.0
    
    # Ensure closed polygon for calculation
    pts = coords[:]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i+1]
        cross = (x0 * y1 - x1 * y0)
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
        
    area = area * 0.5
    if area == 0:
         xs = [p[0] for p in coords]
         ys = [p[1] for p in coords]
         return (sum(xs)/n, sum(ys)/n), 0, 0
         
    cx = cx / (6.0 * area)
    cy = cy / (6.0 * area)
    
    # Bounding box dimensions
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    
    return (cx, cy), width, height

def generate_dxf():
    # Get all plots from single cache file
    cache_file = "cache/all_plots.json"
    if not os.path.exists(cache_file):
        print(f"Cache file {cache_file} not found.")
        return

    try:
        with open(cache_file, 'r') as f:
            plots_data = json.load(f)
    except Exception as e:
        print(f"Error reading cache file: {e}")
        return

    print(f"Processing {len(plots_data)} plots from cache...")
    
    doc = ezdxf.new('R2010')
    
    # Set Point Style to Circle with Cross (35)
    doc.header['$PDMODE'] = 35
    # Set Point Size (absolute units). 
    doc.header['$PDSIZE'] = 0.5 
    
    doc.layers.new(name='PLOT_BOUNDARIES', dxfattribs={'color': 1}) # Red
    doc.layers.new(name='PLOT_LABELS', dxfattribs={'color': 7})     # White/Black
    doc.layers.new(name='COORDINATE_LABELS', dxfattribs={'color': 252}) # Gray (faint)
    
    msp = doc.modelspace()
    
    for data in plots_data:
        try:
            plot_no = data.get('plotno', 'Unknown')
            wkt = data.get('the_geom', '')
            
            if not wkt:
                continue
                
            rings = parse_wkt_rings(wkt)
            
            if not rings:
                continue
            
            # Draw each ring
            for ring_coords in rings:
                # 1. Draw Boundary
                msp.add_lwpolyline(ring_coords, format='xy', dxfattribs={'layer': 'PLOT_BOUNDARIES', 'closed': True})

                # 2. Add Points and Coordinate Labels
                for x, y in ring_coords:
                     # Point entity
                     msp.add_point((x, y), dxfattribs={'layer': 'PLOT_BOUNDARIES', 'color': 1})
                     
                     # Coordinate Label (Small, faint)
                     # Format: "X, Y"
                     label = f"{x:.2f},{y:.2f}"
                     msp.add_text(label, dxfattribs={
                        'height': 0.2, # Fixed small size for coords
                        'insert': (x + 0.2, y + 0.2), 
                        'layer': 'COORDINATE_LABELS',
                        'color': 252
                     })

                # 3. Add Plot Label (Survey Number)
                # Calculate centroid and size
                (cx, cy), width, height = calculate_polygon_properties(ring_coords)
                
                # Dynamic text sizing
                # Aim for text to be about 20% of the smaller dimension of the plot
                # But clamp between min and max values to avoid invisible or huge text
                min_dim = min(width, height) if width > 0 and height > 0 else 1.0
                text_h = min_dim * 0.2
                
                # Clamping
                if text_h < 0.5: text_h = 0.5
                if text_h > 5.0: text_h = 5.0
                
                msp.add_text(f"{plot_no}", dxfattribs={
                    'height': text_h,
                    'insert': (cx, cy),
                    'layer': 'PLOT_LABELS',
                    'color': 7,
                    'halign': 1, # Center
                    'valign': 1, # Middle
                    'align_point': (cx, cy) 
                })

        except Exception as e:
            print(f"Error processing plot: {e}")

    doc.saveas(OUTPUT_FILE)
    print(f"Successfully generated {OUTPUT_FILE} with {len(plots_data)} plots.")
    print(f"Absolute path: {os.path.abspath(OUTPUT_FILE)}")

if __name__ == "__main__":
    generate_dxf()
