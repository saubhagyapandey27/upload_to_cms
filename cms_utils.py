import os
import requests
from io import BytesIO
from PIL import Image
import subprocess
import time

def process_image(file_bytes, mode='horizontal'):
    """
    Process image based on mode:
    - 'horizontal': Resize to 1280x720 (16:9)
    - 'square': Center crop and resize to 800x800
    Returns bytes of processed JPEG.
    """
    try:
        img = Image.open(BytesIO(file_bytes))
        
        if mode == 'square':
            # Calculate center crop dimensions
            width, height = img.size
            new_size = min(width, height)
            
            left = (width - new_size) / 2
            top = (height - new_size) / 2
            right = (width + new_size) / 2
            bottom = (height + new_size) / 2
            
            # Crop to square
            img = img.crop((left, top, right, bottom))
            
            # Resize directly to 800x800
            target_size = (800, 800)
            img = img.resize(target_size, Image.Resampling.LANCZOS)
            
        else:
            # Horizontal (16:9) - Force resize to 1280x720
            # Note: The rough code just resized, it didn't crop to aspect ratio first.
            # Assuming force resize is intended as per rough code.
            target_size = (1280, 720)
            img = img.resize(target_size, Image.Resampling.LANCZOS)
        
        # Save to bytes with compression
        out_buffer = BytesIO()
        # Convert to RGB to ensure JPEG compatibility (remove alpha channel if PNG)
        img.convert('RGB').save(out_buffer, format='JPEG', quality=60)
        
        return out_buffer.getvalue()
        
    except Exception as e:
        print(f"Image Processing Error: {e}")
        return None

def process_audio(file_bytes, original_filename, channels=1):
    """
    Convert audio to low-bitrate MP3 using ffmpeg directly.
    Target: 64kbps, Channels: 1 (Mono) or 2 (Stereo)
    Requires ffmpeg to be installed and in PATH.
    """
    try:
        ext = original_filename.split('.')[-1].lower()
        temp_in = f"temp_audio_in_{int(time.time())}.{ext}"
        temp_out = f"temp_audio_out_{int(time.time())}.mp3"
        
        with open(temp_in, "wb") as f:
            f.write(file_bytes)
            
        # ffmpeg command: -i input -b:a 64k -ac {channels} -y output
        # -y overwrites output file if exists
        cmd = [
            "ffmpeg", 
            "-i", temp_in, 
            "-b:a", "64k", 
            "-ac", str(channels), 
            "-y", 
            temp_out
        ]
        
        # Run ffmpeg, capture output to avoid spamming console
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Read back
        with open(temp_out, "rb") as f:
            processed_bytes = f.read()
            
        # Cleanup
        try:
            os.remove(temp_in)
            os.remove(temp_out)
        except:
            pass
            
        return processed_bytes
        
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg Error: {e.stderr.decode()}")
        return None
    except Exception as e:
        print(f"Audio Processing Error: {e}")
        return None

def upload_asset(api_url, api_token, file_bytes, filename):
    """
    Upload byte content as an asset.
    Endpoint: /api/assets/upload (Custom)
    """
    upload_url = f"{api_url}/api/assets/upload"
    headers = {'api-key': api_token}
    
    # MIME type guess
    mime = 'application/octet-stream'
    if filename.endswith('.jpg') or filename.endswith('.jpeg'):
        mime = 'image/jpeg'
    elif filename.endswith('.mp3'):
        mime = 'audio/mpeg'
        
    files = {
        'files[]': (filename, BytesIO(file_bytes), mime)
    }
    
    try:
        resp = requests.post(upload_url, headers=headers, files=files, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        
        # Normalize response
        if isinstance(result, dict) and 'assets' in result and result['assets']:
            return result['assets'][0]
        elif isinstance(result, list) and len(result) > 0:
            return result[0]
        elif isinstance(result, dict) and '_id' in result:
            return result
            
        return None
    except Exception as e:
        print(f"Upload Error: {e}")
        return None

def create_collection_entry(api_url, api_token, collection_name, data):
    """
    Create a general collection entry.
    Endpoint: /api/content/item/{collection_name}
    """
    endpoint = f"{api_url}/api/content/item/{collection_name}"
    headers = {
        'api-key': api_token,
        'Content-Type': 'application/json'
    }
    
    payload = {"data": data}
    
    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Entry Creation Error: {e}")
        return None
