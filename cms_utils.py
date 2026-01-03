import os
import requests
from io import BytesIO
from PIL import Image
from pydub import AudioSegment
import time

# Utility functions for CMS Dashboard associated with Cockpit CMS v2

def process_image(file_bytes, mode='horizontal'):
    """
    Process image based on mode.
    Returns: Bytes of processed JPEG
    """
    try:
        img = Image.open(BytesIO(file_bytes))
        
        if mode == 'square':
            # Center Crop & Square
            width, height = img.size
            new_size = min(width, height)
            left = (width - new_size) / 2
            top = (height - new_size) / 2
            right = (width + new_size) / 2
            bottom = (height + new_size) / 2
            img = img.crop((left, top, right, bottom))
            target_size = (800, 800)
        else:
            # Horizontal (Stretch/Squash to 16:9)
            target_size = (1280, 720)
            
        # Resize
        img_resized = img.resize(target_size, Image.Resampling.LANCZOS)
        
        # Save compressed
        out_buffer = BytesIO()
        img_resized.convert('RGB').save(out_buffer, format='JPEG', quality=60)
        return out_buffer.getvalue()
        
    except Exception as e:
        print(f"Image Processing Error: {e}")
        return None

def process_audio(file_bytes, original_filename, channels=1):
    """
    Convert audio to low-bitrate MP3.
    Target: 64kbps
    Channels: 1 (Mono) or 2 (Stereo)
    """
    try:
        # Pydub requires a file path or file-like object.
        # We'll save the input bytes to a temp file to let pydub/ffmpeg handle it.
        # This is safer for format detection.
        ext = original_filename.split('.')[-1].lower()
        temp_in = f"temp_audio_in_{int(time.time())}.{ext}"
        temp_out = f"temp_audio_out_{int(time.time())}.mp3"
        
        with open(temp_in, "wb") as f:
            f.write(file_bytes)
            
        audio = AudioSegment.from_file(temp_in)
        
        # Export as low quality MP3
        # Bitrate: 64k
        audio.set_channels(channels).export(temp_out, format="mp3", bitrate="64k")
        
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
