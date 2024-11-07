

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