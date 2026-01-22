import requests

def test_get():
    url = "https://mahabhunakasha.mahabhumi.gov.in/rest/VillageMapService/kidelistFromGisCodeMH"
    # Using the same GIS code from the failed run
    params = {
        "state": "27",
        "logedLevels": "RVM2502272500020303690000"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://mahabhunakasha.mahabhumi.gov.in/27/index.html"
    }
    
    print(f"Testing GET to {url}...")
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Success! Response preview:")
            print(resp.text[:200])
        else:
            print("Failed.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_get()
