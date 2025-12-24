from flask import Flask, request, jsonify, send_file
import subprocess
import os
import uuid
import requests
from PIL import Image

app = Flask(__name__)

def download_file(url, output_path):
    """Download file from URL"""
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path

def create_subtitle_file(text_segments, output_path):
    """Create SRT subtitle file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(text_segments, 1):
            start_time = segment.get('start', (i-1)*5)
            end_time = segment.get('end', i*5)
            text = segment.get('text', '')
            
            f.write(f"{i}\n")
            f.write(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}\n")
            f.write(f"{text}\n\n")
    return output_path

def format_srt_time(seconds):
    """Convert seconds to SRT time format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        ffmpeg_version = result.stdout.split('\n')[0]
        return jsonify({
            "status": "healthy",
            "ffmpeg": ffmpeg_version,
            "fonts_available": True
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/render-video', methods=['POST'])
def render_video():
    """Main video rendering endpoint"""
    job_id = str(uuid.uuid4())[:8]
    temp_dir = f"/tmp/footnote_{job_id}"
    
    try:
        os.makedirs(temp_dir, exist_ok=True)
        
        data = request.json
        
        # Parameters
        images = data.get('images', [])
        voiceover_url = data.get('voiceover_url')
        music_url = data.get('music_url')
        subtitle_segments = data.get('subtitles', [])
        duration_per_image = int(data.get('duration_per_image', 5))
        video_title = data.get('title', 'The Footnote Video')
        
        print(f"[{job_id}] Starting render with {len(images)} images")
        
        # Download voiceover
        voice_file = f"{temp_dir}/voice.mp3"
        if voiceover_url:
            print(f"[{job_id}] Downloading voiceover...")
            download_file(voiceover_url, voice_file)
        
        # Download music
        music_file = f"{temp_dir}/music.mp3"
        if music_url:
            print(f"[{job_id}] Downloading music...")
            download_file(music_url, music_file)
        
        # Download and prepare images
        image_files = []
        for idx, img_url in enumerate(images):
            img_file = f"{temp_dir}/img_{idx:03d}.jpg"
            print(f"[{job_id}] Downloading image {idx+1}/{len(images)}...")
            download_file(img_url, img_file)
            
            # Resize to 1920x1080 with PIL
            with Image.open(img_file) as img:
                img = img.convert('RGB')
                img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
                img.save(img_file, 'JPEG', quality=95)
            
            image_files.append(img_file)
        
        # Create subtitle file
        subtitle_file = None
        if subtitle_segments:
            subtitle_file = f"{temp_dir}/subtitles.srt"
            print(f"[{job_id}] Creating subtitle file...")
            create_subtitle_file(subtitle_segments, subtitle_file)
        
        # Build FFmpeg filter
        total_duration = len(images) * duration_per_image
        
        # Video filter
        filter_complex = []
        
        for i in range(len(image_files)):
            filter_complex.append(
                f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                f"fade=t=in:st=0:d=0.5,fade=t=out:st={duration_per_image-0.5}:d=0.5[v{i}]"
            )
        
        # Concat videos
        concat_inputs = ''.join([f'[v{i}]' for i in range(len(image_files))])
        filter_complex.append(f"{concat_inputs}concat=n={len(image_files)}:v=1:a=0[video_base]")
        
        # Add subtitles
        if subtitle_file:
            subtitle_style = "FontName=DejaVu Sans,FontSize=32,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Bold=1,MarginV=40"
            filter_complex.append(f"[video_base]subtitles={subtitle_file}:force_style='{subtitle_style}'[video]")
        else:
            filter_complex.append("[video_base]null[video]")
        
        # Audio mixing
        if voiceover_url and music_url:
            filter_complex.append("[1:a]volume=1.0[voice]")
            filter_complex.append("[2:a]volume=0.25[music]")
            filter_complex.append("[voice][music]amix=inputs=2:duration=first[audio]")
            audio_inputs = ['-i', voice_file, '-i', music_file]
        elif voiceover_url:
            filter_complex.append("[1:a]volume=1.0[audio]")
            audio_inputs = ['-i', voice_file]
        else:
            audio_inputs = []
        
        filter_str = ';'.join(filter_complex)
        
        # Output file
        output_file = f"{temp_dir}/final_video.mp4"
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg', '-y',
            # Input images
            *[item for img in image_files for item in ['-loop', '1', '-t', str(duration_per_image), '-i', img]],
            # Audio inputs
            *audio_inputs,
            # Filter
            '-filter_complex', filter_str,
            # Map outputs
            '-map', '[video]'
        ]
        
        if voiceover_url or music_url:
            cmd.extend(['-map', '[audio]'])
        
        # Encoding settings
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-profile:v', 'high',
            '-level', '4.0',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-t', str(total_duration)
        ])
        
        if voiceover_url or music_url:
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', '192k',
                '-ar', '44100'
            ])
        
        cmd.append(output_file)
        
        print(f"[{job_id}] Running FFmpeg...")
        
        # Execute FFmpeg
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        
        if result.returncode != 0:
            print(f"[{job_id}] FFmpeg error: {result.stderr}")
            return jsonify({
                "error": "FFmpeg rendering failed",
                "job_id": job_id,
                "stderr": result.stderr[-2000:]
            }), 500
        
        # Check output file
        if not os.path.exists(output_file):
            return jsonify({
                "error": "Output file not created",
                "job_id": job_id
            }), 500
        
        file_size = os.path.getsize(output_file)
        print(f"[{job_id}] Video created successfully! Size: {file_size / 1024 / 1024:.2f} MB")
        
        # Return video file
        return send_file(
            output_file,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=f"{video_title.replace(' ', '_')}_{job_id}.mp4"
        )
        
    except subprocess.TimeoutExpired:
        return jsonify({
            "error": "Rendering timeout (15 minutes)",
            "job_id": job_id
        }), 504
    
    except Exception as e:
        print(f"[{job_id}] Error: {str(e)}")
        return jsonify({
            "error": str(e),
            "job_id": job_id
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
