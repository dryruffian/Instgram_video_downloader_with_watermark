import instaloader
from urllib.parse import urlparse
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip
from moviepy.config import change_settings
import glob
import gradio as gr
import os
import zipfile
import concurrent.futures
import logging
from tqdm import tqdm
from dataclasses import dataclass
from typing import Optional, List, Tuple
from pathlib import Path
import shutil
import tempfile
from contextlib import contextmanager
import time

# Configuration
@dataclass
class Config:
    IMAGEMAGICK_PATH = r"C:/Program Files/ImageMagick-7.1.1-Q16-HDRI/magick.exe"
    DEFAULT_WATERMARK = "@Gulhatheli"
    OUTPUT_DIR = '/Outputs'
    TEMP_DIR = "./video_processor"
    MAX_WORKERS = 4
    FONT_PATH = "./Luxinus Elegance DEMO.otf"
    VIDEO_QUALITY = {
        "codec": "libx264",
        "threads": 12,
        "preset": "slow",
        "crf": "18"
    }
    FRAME_THICKNESS_RATIO = 0.05

# Setup logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("video_processor.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Resource management
@contextmanager
def video_clip_context(*clips):
    """Context manager for safely handling video clips"""
    try:
        yield clips
    finally:
        for clip in clips:
            if clip and hasattr(clip, 'close'):
                try:
                    clip.close()
                except Exception as e:
                    logger.warning(f"Error closing clip: {e}")

class InstagramDownloader:
    def __init__(self):
        self.loader = instaloader.Instaloader(
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
        )

    @staticmethod
    def extract_shortcode(url: str) -> Optional[str]:
        """Extract shortcode from Instagram URL"""
        try:
            path = urlparse(url).path
            return path.strip("/").split("/")[-1]
        except Exception as e:
            logger.error(f"Failed to extract shortcode from URL {url}: {e}")
            return None

    def download_video(self, url: str, target_dir: Path) -> Optional[Path]:
        """Download video from Instagram URL"""
        shortcode = self.extract_shortcode(url)
        if not shortcode:
            return None

        try:
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            download_dir = Path(f"{target_dir}")
            self.loader.download_post(post, target=str(download_dir))
            
            video_files = list(download_dir.glob("*.mp4"))
            print(f"this is the file{video_files}")
            if video_files:
                return video_files[0]
            
            logger.error(f"No video file found after downloading from {url}")
            return None
            
        except Exception as e:
            logger.exception(f"Failed to download video from {url}: {e}")
            return None

class VideoProcessor:
    def __init__(self, config: Config):
        self.config = config
        change_settings({"IMAGEMAGICK_BINARY": config.IMAGEMAGICK_PATH})
        self.downloader = InstagramDownloader()
        
        # Ensure output directory exists
        self.config.OUTPUT_DIR.mkdir(exist_ok=True)
        self.config.TEMP_DIR.mkdir(exist_ok=True)

    def add_watermark(self, video_path: Path, watermark_text: str) -> Optional[Path]:
        """Add watermark to video"""
        try:
            with video_clip_context() as clips:
                # Load video
                video_clip = VideoFileClip(str(video_path))
                clips += (video_clip,)
                
                # Calculate dimensions
                W, H = video_clip.size
                frame_thickness = int(min(W, H) * self.config.FRAME_THICKNESS_RATIO)
                frame_width = W + 2 * frame_thickness
                frame_height = H + 2 * frame_thickness

                # Create frame
                frame_clip = ColorClip(
                    size=(frame_width, frame_height),
                    color=(255, 255, 255)
                ).set_duration(video_clip.duration)
                clips += (frame_clip,)

                # Create watermark
                txt_clip = TextClip(
                    watermark_text,
                    fontsize=24,
                    color="white",
                    font=str(self.config.FONT_PATH),
                ).set_duration(video_clip.duration)
                clips += (txt_clip,)

                # Position clips
                video_in_frame = video_clip.set_position('center')
                txt_clip = txt_clip.set_position(('center', 0.6), relative=True)

                # Composite
                final_clip = CompositeVideoClip(
                    [frame_clip, video_in_frame, txt_clip],
                    size=(frame_width, frame_height)
                )
                clips += (final_clip,)

                # Generate output path
                output_path = self.config.OUTPUT_DIR / f"{video_path.stem}_watermarked{video_path.suffix}"
                
                # Write video
                final_clip.write_videofile(
                    str(output_path),
                    codec=self.config.VIDEO_QUALITY['codec'],
                    threads=self.config.VIDEO_QUALITY['threads'],
                    preset=self.config.VIDEO_QUALITY['preset'],
                    ffmpeg_params=["-crf", self.config.VIDEO_QUALITY['crf']],
                    verbose=False,
                    logger=None
                )
                return output_path

        except Exception as e:
            logger.exception(f"Failed to add watermark to video {video_path}: {e}")
            return None

    def process_single_video(self, url: str, watermark_text: str) -> Optional[Path]:
        """Process a single video"""
        try:
            temp_path = Config.TEMP_DIR
            video_path = self.downloader.download_video(url, temp_path)
            
            if not video_path:
                return None
            
            
            return self.add_watermark(video_path, watermark_text)

        except Exception as e:
            logger.exception(f"Failed to process video from {url}: {e}")
            return None
        
        finally:
            shutil.rmtree(temp_path)

    def process_multiple_videos(self, urls: List[str], watermark_text: str) -> Optional[Path]:
        """Process multiple videos in parallel"""
        if not urls:
            return None

        processed_videos = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
            future_to_url = {
                executor.submit(self.process_single_video, url.strip(), watermark_text): url.strip()
                for url in urls if url.strip()
            }
            
            for future in tqdm(
                concurrent.futures.as_completed(future_to_url),
                total=len(future_to_url),
                desc="Processing videos"
            ):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        processed_videos.append(result)
                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")

        if not processed_videos:
            return None

        # Create zip file
        zip_path = self.config.OUTPUT_DIR / "watermarked_videos.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for video_path in processed_videos:
                zipf.write(video_path, video_path.name)

        return zip_path

class GradioInterface:
    def __init__(self, processor: VideoProcessor):
        self.processor = processor

    def create_interface(self):
        with gr.Blocks() as demo:
            gr.Markdown("# Khushi's Video Watermarker")

            with gr.Tab("Single Video"):
                with gr.Row():
                    with gr.Column():
                        instagram_url = gr.Textbox(label="Instagram Video URL")
                        watermark_text = gr.Textbox(
                            label="Watermark Text",
                            placeholder=Config.DEFAULT_WATERMARK
                        )
                        submit_button = gr.Button("Process Video")
                    
                    with gr.Column():
                        output_video = gr.Video(label="Watermarked Video")
                        error_text = gr.Textbox(visible=False)

                submit_button.click(
                    fn=self.process_single_video,
                    inputs=[instagram_url, watermark_text],
                    outputs=[output_video, error_text],
                )

            with gr.Tab("Batch Processing"):
                with gr.Row():
                    with gr.Column():
                        instagram_urls = gr.Textbox(
                            label="Instagram Video URLs (one per line)",
                            lines=5
                        )
                        watermark_text_batch = gr.Textbox(
                            label="Watermark Text",
                            placeholder=Config.DEFAULT_WATERMARK
                        )
                        batch_submit_button = gr.Button("Process Videos")
                    
                    with gr.Column():
                        output_zip = gr.File(label="Watermarked Videos ZIP")
                        batch_error_text = gr.Textbox(visible=False)

                batch_submit_button.click(
                    fn=self.process_multiple_videos,
                    inputs=[instagram_urls, watermark_text_batch],
                    outputs=[output_zip, batch_error_text],
                )

        return demo

    def process_single_video(self, url: str, watermark_text: str) -> Tuple[Optional[Path], str]:
        """Process single video for Gradio interface"""
        if not watermark_text:
            watermark_text = Config.DEFAULT_WATERMARK
            
        result = self.processor.process_single_video(url, watermark_text)
        if result:
            return str(result), ""
        return None, "Error processing video"

    def process_multiple_videos(self, urls: str, watermark_text: str) -> Tuple[Optional[Path], str]:
        """Process multiple videos for Gradio interface"""
        if not watermark_text:
            watermark_text = Config.DEFAULT_WATERMARK
            
        url_list = [url.strip() for url in urls.strip().splitlines() if url.strip()]
        result = self.processor.process_multiple_videos(url_list, watermark_text)
        if result:
            return str(result), ""
        return None, "Error processing videos"

def main():
    config = Config()
    processor = VideoProcessor(config)
    interface = GradioInterface(processor)
    # demo = interface.create_interface()
    # demo.launch()

if __name__ == "__main__":
    main()