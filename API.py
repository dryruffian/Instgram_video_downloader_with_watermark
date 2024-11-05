from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
from Insta_loader import VideoProcessor
import logging
from logging.handlers import RotatingFileHandler
from functools import wraps
import time
import uuid
import tempfile
from werkzeug.utils import secure_filename
import traceback
from pathlib import Path

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuration
class Config:
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit
    TEMP_DIRECTORY = tempfile.gettempdir()
    LOG_DIRECTORY = "logs"
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi'}
    DEFAULT_WATERMARK = '@Gulhatheli'
    IMAGEMAGICK_PATH = r"C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/magick.exe"
    OUTPUT_DIR = Path("Outputs")
    TEMP_DIR = Path(tempfile.gettempdir()) / "video_processor"
    MAX_WORKERS = 4
    FONT_PATH = Path("./Luxinus Elegance DEMO.otf")
    VIDEO_QUALITY = {
        "codec": "libx264",
        "threads": 12,
        "preset": "slow",
        "crf": "18"
    }
    FRAME_THICKNESS_RATIO = 0.05

# Ensure log directory exists
os.makedirs(Config.LOG_DIRECTORY, exist_ok=True)

# Setup logging
def setup_logging():
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        os.path.join(Config.LOG_DIRECTORY, 'app.log'),
        maxBytes=1024 * 1024,  # 1MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger

logger = setup_logging()

# Utility functions
def generate_unique_filename(extension):
    """Generate a unique filename with the given extension."""
    return f"{uuid.uuid4()}.{extension}"

def cleanup_file(filepath):
    """Safely delete a file if it exists."""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            logger.debug(f"Cleaned up file: {filepath}")
    except Exception as e:
        logger.error(f"Error cleaning up file {filepath}: {str(e)}")

def validate_url(url):
    """Basic URL validation for Instagram URLs."""
    if not url:
        return False
    return url.startswith(('http://instagram.com', 'https://instagram.com',
                          'http://www.instagram.com', 'https://www.instagram.com'))

# Decorators
def handle_errors(f):
    """Decorator to handle errors consistently."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.exception("An unhandled exception occurred")
            error_id = str(uuid.uuid4())
            return jsonify({
                'error': 'An internal error occurred',
                'error_id': error_id,
                'details': str(e) if app.debug else 'Please contact support with this error ID'
            }), 500
    return decorated_function

def retry_on_failure(max_retries=Config.MAX_RETRIES, delay=Config.RETRY_DELAY):
    """Decorator to retry operations on failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

# Routes
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

@app.route('/process_video', methods=['POST'])
@handle_errors
def process_video():
    video_processor = VideoProcessor(Config)

    """Process video endpoint with enhanced error handling and validation."""
    # Extract and validate request data
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    instagram_url = data.get('instagram_url')
    if not instagram_url:
        return jsonify({'error': 'instagram_url is required'}), 400

    if not validate_url(instagram_url):
        return jsonify({'error': 'Invalid Instagram URL'}), 400

    watermark_text = data.get('watermark_text', Config.DEFAULT_WATERMARK)
    
    # Generate a unique identifier for this processing request
    request_id = str(uuid.uuid4())
    logger.info(f"Processing video request {request_id} for URL: {instagram_url}")

    try:
        # Process the video with retry mechanism
        
        @retry_on_failure()
        def process_with_retry():
            return video_processor.process_single_video(instagram_url, watermark_text)

        output_path = process_with_retry()
        
        if not output_path or not os.path.isfile(output_path):
            logger.error(f"Video processing failed for request {request_id}")
            return jsonify({'error': 'Video processing failed'}), 500

        # Send the file and clean up
        try:
            response = send_file(
                output_path,
                as_attachment=True,
                download_name=secure_filename(os.path.basename(output_path))
            )
            
            # Register cleanup callback
            @response.call_on_close
            def cleanup():
                cleanup_file(output_path)
            
            logger.info(f"Successfully processed video request {request_id}")
            return response

        except Exception as e:
            cleanup_file(output_path)
            raise

    except Exception as e:
        logger.exception(f"Error processing video request {request_id}")
        return jsonify({
            'error': 'Video processing failed',
            'request_id': request_id,
            'details': str(e) if app.debug else 'Please contact support with this request ID'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)