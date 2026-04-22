import requests
import base64
import os
import time

def test_extraction():
    url = "http://localhost:8000/api/extract_stamp"
    
    # Path to one of the test raw stamp images
    # We can use the test direct image
    test_img = "data/raw/stamps_raw/CV_0001.png"
    
    # Just find any test image
    if not os.path.exists(test_img):
        # Fallback search
        import glob
        files = glob.glob("data/raw/stamps_raw/*.png")
        if not files:
            print("No test images found.")
            return
        test_img = files[0]
        
    print(f"Testing with image: {test_img}")
    
    start = time.time()
    with open(test_img, "rb") as f:
        files = {"file": f}
        response = requests.post(url, files=files)
        
    print(f"Status Code: {response.status_code}")
    print(f"Time Taken: {time.time() - start:.2f}s")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Stamp Count: {data.get('count')}")
        if data.get('count', 0) > 0:
            for i, stamp in enumerate(data['stamps']):
                print(f"--- Stamp {i+1} ---")
                print(f"Coords: {stamp['coords']}")
                print(f"Confidence: {stamp['confidence']}")
                b64 = stamp['base64']
                print(f"Base64 snippet: {b64[:30]}... (Total length: {len(b64)})")
                
                # Check decoding
                header, encoded = b64.split(",", 1)
                img_data = base64.b64decode(encoded)
                out_path = f"test_result_stamp_{i}.png"
                with open(out_path, "wb") as out_f:
                    out_f.write(img_data)
                print(f"Saved decoded transparent stamp to {out_path}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_extraction()
