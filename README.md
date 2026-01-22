# Mahabhunakasha Coordinate Extractor

This folder contains a Python script and documentation for extracting plot coordinates (geometry) from the Mahabhunakasha website.

## Files

- `get_coords.py`: The Python script to fetch the data.
- `README.md`: This file.

## How to Use

1. **Install Dependencies**:
   You need the `requests` library.

   ```bash
   pip install requests
   ```

2. **Run the Script**:
   ```bash
   python3 get_coords.py
   ```

## How it Works

The website uses a REST API endpoint `getPlotInfo` which returns the geometry in WKT (Well-Known Text) format.

**API Endpoint**: `https://mahabhunakasha.mahabhumi.gov.in/27/rest/MapInfo/getPlotInfo`

### Constructing the GIS Code

To fetch a specific village's data, you need the **GIS Code**. It is a 25-character string constructed as follows:

`[Prefix] + [DistrictCode] + [TalukaCode] + [VillageCode]`

- **Prefix**: `RVM`
- **DistrictCode**: 2 digits (e.g., Akola = `05`)
- **TalukaCode**: 2 digits (e.g., Akot = `02`)
- **VillageCode**: 18 digits (e.g., Akolkhed = `270500020047510000`)

**Example**: `RVM` + `05` + `02` + `270500020047510000` = `RVM0502270500020047510000`

### Coordinate System

The returned coordinates are in a **Projected Coordinate System** (likely UTM Zone 43N for Maharashtra). If you need GPS coordinates (Lat/Long), you can use the `getExtentGeoref` endpoint to get the bounding box in WGS84, or use a library like `pyproj` to transform the WKT coordinates.
