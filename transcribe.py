import os
import sys
import warnings
import shutil
import subprocess

# Suppress warnings
warnings.filterwarnings("ignore")

# Configure FFmpeg for Windows - Priority 1: imageio-ffmpeg
ffmpeg_exe = None
try:
    import imageio_ffmpeg
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    if os.path.exists(ffmpeg_path):
        ffmpeg_exe = ffmpeg_path
        os.environ['FFMPEG_BINARY'] = ffmpeg_path
        os.environ['PATH'] = os.path.dirname(ffmpeg_path) + os.pathsep + os.environ.get('PATH', '')
        print(f"✅ Using FFmpeg from imageio-ffmpeg: {ffmpeg_path}")
except Exception as e:
    print(f"Note: imageio-ffmpeg setup attempted: {e}")

# Priority 2: Try Windows 'where' command
if not ffmpeg_exe:
    try:
        result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, shell=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            ffmpeg_bin = result.stdout.strip().split('\n')[0]
            if os.path.exists(ffmpeg_bin):
                ffmpeg_exe = ffmpeg_bin
                os.environ['FFMPEG_BINARY'] = ffmpeg_bin
                os.environ['PATH'] = os.path.dirname(ffmpeg_bin) + os.pathsep + os.environ.get('PATH', '')
                print(f"✅ Using FFmpeg from Windows PATH: {ffmpeg_bin}")
    except Exception as e:
        pass

# Priority 3: System shutil.which()
if not ffmpeg_exe:
    ffmpeg_bin = shutil.which('ffmpeg')
    if ffmpeg_bin and os.path.exists(ffmpeg_bin):
        ffmpeg_exe = ffmpeg_bin
        os.environ['FFMPEG_BINARY'] = ffmpeg_bin
        print(f"✅ Using system FFmpeg: {ffmpeg_bin}")

# Priority 4: Common installation paths on Windows
if not ffmpeg_exe:
    common_paths = [
        r'C:\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
    ]
    for path in common_paths:
        if os.path.exists(path):
            ffmpeg_exe = path
            os.environ['FFMPEG_BINARY'] = path
            os.environ['PATH'] = os.path.dirname(path) + os.pathsep + os.environ.get('PATH', '')
            print(f"✅ Found FFmpeg at: {path}")
            break

if not ffmpeg_exe:
    print("⚠️  Warning: Could not locate FFmpeg. Please install it:")
    print("   Option 1: choco install ffmpeg")
    print("   Option 2: Download from https://www.gyan.dev/ffmpeg/builds/")
else:
    print(f"FFmpeg configured: {ffmpeg_exe}")

try:
    import whisper
except Exception as e:
    print(f"Error loading Whisper: {e}")
    raise

# Load Whisper model lazily (on first use)
model = None

def transcribe_audio(audio_file_path, transcribes_folder):
    """
    Transcribe audio file using OpenAI Whisper model
    
    Args:
        audio_file_path: Full path to the audio file
        transcribes_folder: Folder to save the transcription text file
    
    Returns:
        Dictionary with transcribed text and status
    """
    global model
    
    try:
        # Verify audio file exists
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        # Ensure FFmpeg is available before proceeding
        if not ffmpeg_exe:
            raise RuntimeError('FFmpeg not found. Install with: choco install ffmpeg OR download from https://www.gyan.dev/ffmpeg/builds/')
        
        # Verify FFmpeg is accessible and working
        try:
            result = subprocess.run([ffmpeg_exe, '-version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                raise RuntimeError(f'FFmpeg test failed with return code {result.returncode}')
        except subprocess.TimeoutExpired:
            raise RuntimeError('FFmpeg timeout - may not be installed correctly')
        except FileNotFoundError:
            raise RuntimeError(f'FFmpeg not found at: {ffmpeg_exe}')
        
        # Load model on first use (lazy loading)
        if model is None:
            print("Loading Whisper model (base)... This may take a moment on first run.")
            model = whisper.load_model("base")
        
        # Transcribe the audio
        print(f"Transcribing: {os.path.basename(audio_file_path)}")
        print(f"Using FFmpeg: {ffmpeg_exe}")
        
        # Pass ffmpeg path explicitly to Whisper
        result = model.transcribe(
            audio_file_path, 
            language="en",
            fp16=False  # Disable fp16 to avoid compatibility issues
        )
        transcribed_text = result['text'].strip()
        
        # Get the filename without extension
        filename = os.path.basename(audio_file_path)
        filename_without_ext = os.path.splitext(filename)[0]
        
        # Create transcription text file
        txt_filename = f"{filename_without_ext}.txt"
        txt_filepath = os.path.join(transcribes_folder, txt_filename)
        
        # Ensure the transcribes folder exists
        os.makedirs(transcribes_folder, exist_ok=True)
        
        # Save transcription to text file
        with open(txt_filepath, "w", encoding="utf-8") as file:
            file.write(transcribed_text)
        
        print(f"✅ Transcription saved to: {txt_filepath}")
        
        return {
            'success': True,
            'text': transcribed_text,
            'filename': txt_filename,
            'filepath': txt_filepath
        }
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Transcription error: {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': error_msg,
            'text': None
        }

