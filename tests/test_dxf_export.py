import json
import ezdxf
import io

def test_dxf_generation():
    # Mock data similar to what the frontend sends
    data = {
        'plots': [
            {
                'label': 'Gat-1',
                'coordinates': [
                    [73.85, 18.52],
                    [73.86, 18.52],
                    [73.86, 18.53],
                    [73.85, 18.53],
                    [73.85, 18.52]
                ]
            }
        ]
    }
    
    # Simulate the logic in app.py
    doc = ezdxf.new('R2010')
    doc.layers.new(name='PLOT_BOUNDARIES', dxfattribs={'color': 1})
    doc.layers.new(name='COORDINATE_LABELS', dxfattribs={'color': 2})
    doc.layers.new(name='PLOT_NUMBERS', dxfattribs={'color': 3})
    
    msp = doc.modelspace()
    all_x, all_y = [], []
    
    for plot in data['plots']:
        label = plot['label']
        coords = plot['coordinates']
        
        poly_pts = [(float(p[0]), float(p[1])) for p in coords]
        for x, y in poly_pts:
            all_x.append(x)
            all_y.append(y)
        
        msp.add_lwpolyline(poly_pts, format='xy', dxfattribs={'layer': 'PLOT_BOUNDARIES'})
    
    if all_x and all_y:
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        size = max(max_x - min_x, max_y - min_y)
        text_h = size * 0.01 if size > 0 else 0.1
        
        for plot in data['plots']:
            poly_pts = [(float(p[0]), float(p[1])) for p in plot['coordinates']]
            # Plot Number
            msp.add_text(plot['label'], dxfattribs={
                'height': text_h * 1.5,
                'insert': poly_pts[0],
                'layer': 'PLOT_NUMBERS'
            })
            # Coordinates
            for x, y in poly_pts[:-1]:
                msp.add_text(f"({x:.6f}, {y:.6f})", dxfattribs={
                    'height': text_h * 0.7,
                    'insert': (x, y + text_h),
                    'layer': 'COORDINATE_LABELS'
                })
                msp.add_point((x, y), dxfattribs={'layer': 'COORDINATE_LABELS'})

    # Verify content
    out_stream = io.StringIO()
    doc.write(out_stream)
    content = out_stream.getvalue()
    
    print(f"DXF Content Length: {len(content)}")
    print("Found Layers:")
    for layer in doc.layers:
        print(f" - {layer.dxf.name}")
        
    # Check for polyline and text entities
    entities = list(msp)
    print(f"Total entities: {len(entities)}")
    
    polylines = [e for e in entities if e.dxftype() == 'LWPOLYLINE']
    texts = [e for e in entities if e.dxftype() == 'TEXT']
    points = [e for e in entities if e.dxftype() == 'POINT']
    
    print(f"Polylines: {len(polylines)}")
    print(f"Texts: {len(texts)}")
    print(f"Points: {len(points)}")
    
    assert len(polylines) == 1
    # 1 plot label + 4 vertex coordinates = 5 texts
    assert len(texts) == 5
    assert len(points) == 4
    
    print("Test passed!")

if __name__ == "__main__":
    test_dxf_generation()
