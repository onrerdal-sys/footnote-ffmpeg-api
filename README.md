# Footnote FFmpeg API

Bu API The Footnote projesinin video rendering servisidir.

## Deploy (Render.com)

1. GitHub'da yeni repo oluştur: `footnote-ffmpeg-api`
2. Bu klasörün içeriğini repo'ya yükle
3. Render.com → New Web Service
4. Repo'yu bağla
5. Environment: Docker
6. Instance: Standard ($25/ay - 2GB RAM)
7. Deploy

## Endpoints

### GET /health
Health check endpoint.

Response:
```json
{
  "status": "healthy",
  "ffmpeg": "ffmpeg version 4.4...",
  "fonts_available": true
}
```

### POST /render-video
Video render endpoint.

Request:
```json
{
  "title": "Video Title",
  "images": ["url1", "url2", "url3"],
  "voiceover_url": "https://...",
  "music_url": "https://...",
  "subtitles": [
    {"start": 0, "end": 5, "text": "Subtitle text"}
  ],
  "duration_per_image": 5
}
```

Response: MP4 video file

## Local Testing

```bash
docker build -t footnote-ffmpeg .
docker run -p 5000:5000 footnote-ffmpeg
```

Test:
```bash
curl http://localhost:5000/health
```
