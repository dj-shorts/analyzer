# Docker Usage Guide

Complete guide for running DJ Shorts Analyzer in Docker containers.

## 🐳 Quick Start

```bash
# Build the image
docker build -t dj-shorts/analyzer:latest .

# Run analyzer on a video
docker run --rm \
  -v $(pwd)/data:/data \
  dj-shorts/analyzer:latest \
  analyzer /data/video.mp4 --clips 3 --export-video
```

## 📦 Building the Image

### Basic Build

```bash
docker build -t dj-shorts/analyzer:latest .
```

### Build with specific tag

```bash
docker build -t dj-shorts/analyzer:v0.4.0 .
```

### Build options

```bash
# Build without cache
docker build --no-cache -t dj-shorts/analyzer:latest .

# Build with progress output
docker build --progress=plain -t dj-shorts/analyzer:latest .

# Build for specific platform
docker build --platform linux/amd64 -t dj-shorts/analyzer:latest .
```

## 🚀 Running the Container

### Basic Usage

```bash
# Show help
docker run --rm dj-shorts/analyzer:latest

# Analyze a video
docker run --rm \
  -v /path/to/videos:/data \
  dj-shorts/analyzer:latest \
  analyzer /data/video.mp4 --clips 3
```

### With Video Export

```bash
docker run --rm \
  -v $(pwd)/data:/data \
  -v $(pwd)/clips:/clips \
  dj-shorts/analyzer:latest \
  analyzer /data/video.mp4 --clips 6 --export-video
```

### With All Options

```bash
docker run --rm \
  -v $(pwd)/data:/data \
  -v $(pwd)/clips:/clips \
  dj-shorts/analyzer:latest \
  analyzer /data/video.mp4 \
    --clips 6 \
    --with-motion \
    --align-to-beat \
    --export-video \
    --metrics /data/metrics.txt
```

### Interactive Mode

```bash
# Run shell inside container
docker run --rm -it \
  -v $(pwd)/data:/data \
  dj-shorts/analyzer:latest \
  /bin/bash

# Then run analyzer commands
analyzer /data/video.mp4 --clips 3
```

## 📊 Volume Mounting

### Required Volumes

- **Input videos**: Mount directory with video files
  ```bash
  -v /path/to/videos:/data
  ```

- **Output clips**: Mount directory for exported clips
  ```bash
  -v /path/to/output:/clips
  ```

### Optional Volumes

- **Metrics output**:
  ```bash
  -v /path/to/metrics:/metrics
  ```

- **Custom config**:
  ```bash
  -v /path/to/config:/config
  ```

## 🔍 Image Information

### Image Size

The multi-stage build produces an optimized image:
- **Builder stage**: ~1.5GB (discarded)
- **Runtime stage**: ~800-900MB
- **Compressed**: ~300-400MB

### Image Layers

```
1. Base: python:3.11-slim (~150MB)
2. System deps: ffmpeg, libraries (~200MB)
3. Python deps: numpy, librosa, opencv (~400MB)
4. Application code (~50MB)
```

### Inspect Image

```bash
# Show image details
docker inspect dj-shorts/analyzer:latest

# Show image history
docker history dj-shorts/analyzer:latest

# Show image size
docker images dj-shorts/analyzer
```

## 🔒 Security

### Non-Root User

Container runs as non-root user `analyzer` (UID 999):

```dockerfile
USER analyzer
```

### Read-Only Filesystem

Run with read-only root filesystem:

```bash
docker run --rm \
  --read-only \
  -v $(pwd)/data:/data \
  -v /tmp:/tmp \
  dj-shorts/analyzer:latest \
  analyzer /data/video.mp4 --clips 3
```

### Resource Limits

Limit container resources:

```bash
docker run --rm \
  --memory="4g" \
  --cpus="2" \
  -v $(pwd)/data:/data \
  dj-shorts/analyzer:latest \
  analyzer /data/video.mp4 --clips 3
```

## 🏥 Health Checks

Container includes built-in health check:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' <container_id>

# View health logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' <container_id>
```

Health check runs every 30 seconds and verifies:
- Python can import analyzer module
- All dependencies are available

## 🐛 Troubleshooting

### Build Failures

**Problem**: `uv sync` fails
```bash
# Solution: Update uv.lock
uv lock --upgrade
docker build --no-cache -t dj-shorts/analyzer:latest .
```

**Problem**: ffmpeg not found
```bash
# Solution: Verify system dependencies in Dockerfile
docker run --rm -it dj-shorts/analyzer:latest /bin/bash
which ffmpeg
```

### Runtime Failures

**Problem**: Permission denied
```bash
# Solution: Check volume permissions
ls -la /path/to/data
chmod -R 755 /path/to/data
```

**Problem**: Out of memory
```bash
# Solution: Increase memory limit
docker run --rm --memory="8g" ...
```

**Problem**: Module not found
```bash
# Solution: Verify PYTHONPATH
docker run --rm dj-shorts/analyzer:latest python -c "import sys; print(sys.path)"
```

## 📈 Performance Tips

### 1. Use Volume Caching

```bash
# Cache pip packages (faster rebuilds)
docker build --cache-from dj-shorts/analyzer:latest -t dj-shorts/analyzer:latest .
```

### 2. Pre-download Videos

Download videos to local disk before running analyzer:

```bash
yt-dlp -o "data/video.mp4" "https://youtube.com/watch?v=VIDEO_ID"
docker run --rm -v $(pwd)/data:/data dj-shorts/analyzer:latest analyzer /data/video.mp4
```

### 3. Parallel Processing

Run multiple containers for batch processing:

```bash
for video in data/*.mp4; do
  docker run --rm -d \
    -v $(pwd)/data:/data \
    -v $(pwd)/clips:/clips \
    dj-shorts/analyzer:latest \
    analyzer "/data/$(basename $video)" --clips 3 --export-video
done
```

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
- name: Build Docker image
  run: docker build -t dj-shorts/analyzer:${{ github.sha }} .

- name: Test Docker image
  run: |
    docker run --rm dj-shorts/analyzer:${{ github.sha }} --help
    
- name: Push to registry
  run: |
    docker tag dj-shorts/analyzer:${{ github.sha }} ghcr.io/dj-shorts/analyzer:latest
    docker push ghcr.io/dj-shorts/analyzer:latest
```

## 🌐 Registry

### GitHub Container Registry

```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Tag
docker tag dj-shorts/analyzer:latest ghcr.io/dj-shorts/analyzer:latest

# Push
docker push ghcr.io/dj-shorts/analyzer:latest

# Pull
docker pull ghcr.io/dj-shorts/analyzer:latest
```

### Docker Hub

```bash
# Login
docker login

# Tag
docker tag dj-shorts/analyzer:latest djshorts/analyzer:latest

# Push
docker push djshorts/analyzer:latest
```

## 📚 Advanced Usage

### Custom Entrypoint

```bash
docker run --rm \
  --entrypoint python \
  dj-shorts/analyzer:latest \
  -m analyzer.cli --help
```

### Debug Mode

```bash
docker run --rm -it \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -v $(pwd)/src:/app/src \
  dj-shorts/analyzer:latest \
  /bin/bash
```

### With Docker Compose

See [MONITORING.md](./MONITORING.md) for Docker Compose setup with Prometheus and Grafana.

## 🔗 Related Documentation

- [Monitoring Setup](./MONITORING.md) - Docker Compose with metrics
- [Setup Guide](./SETUP.md) - Installation and configuration
- [README](../README.md) - General project information

