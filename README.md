# Banner PDF/TIFF Converter

A tool for converting and processing banner images between PDF and TIFF formats with ICC profile support.

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Ale007XD/banner_pdf_tiff.git
cd banner_pdf_tiff
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Place ICC profiles in the profiles directory:
```bash
mkdir -p /app/profiles
# Copy your ICC profile file to /app/profiles/CoatedFOGRA39.icc
```

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Application Configuration
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# File Processing
MAX_FILE_SIZE=50MB
OUTPUT_QUALITY=95
DPI=300

# ICC Profile Settings
ICC_PROFILE_PATH=/app/profiles/CoatedFOGRA39.icc
COLOR_SPACE=CMYK

# Storage Configuration
UPLOAD_DIR=./uploads
OUTPUT_DIR=./output
TEMP_DIR=./temp

# Server Configuration (if applicable)
PORT=8000
HOST=0.0.0.0
```

## Commands

### Development Commands

```bash
# Run the application in development mode
python main.py

# Run with debug mode
python main.py --debug

# Process a single file
python converter.py --input file.pdf --output file.tiff

# Batch processing
python batch_convert.py --input-dir ./input --output-dir ./output

# Run tests
python -m pytest tests/

# Run linting
flake8 .
black .

# Generate requirements
pip freeze > requirements.txt
```

### Production Commands

```bash
# Start the production server
gunicorn main:app --bind 0.0.0.0:8000

# Background processing
celery worker -A tasks.celery --loglevel=info

# Monitor tasks
celery flower -A tasks.celery
```

## Usage

### Basic Usage

```python
from banner_converter import BannerConverter

# Initialize converter
converter = BannerConverter(icc_profile_path='/app/profiles/CoatedFOGRA39.icc')

# Convert PDF to TIFF
converter.pdf_to_tiff(
    input_file='banner.pdf',
    output_file='banner.tiff',
    dpi=300,
    quality=95
)

# Convert TIFF to PDF
converter.tiff_to_pdf(
    input_file='banner.tiff',
    output_file='banner.pdf',
    apply_icc_profile=True
)
```

### Command Line Usage

```bash
# Convert PDF to TIFF
python convert.py --format tiff --input banner.pdf --output banner.tiff --dpi 300

# Convert TIFF to PDF with ICC profile
python convert.py --format pdf --input banner.tiff --output banner.pdf --icc-profile

# Batch convert all PDFs in a directory
python convert.py --batch --input-dir ./pdfs --output-dir ./tiffs --format tiff

# Apply ICC profile to existing file
python apply_profile.py --input banner.tiff --profile /app/profiles/CoatedFOGRA39.icc
```

### API Usage (if web service)

```bash
# Upload and convert file
curl -X POST http://localhost:8000/convert \
  -F "file=@banner.pdf" \
  -F "format=tiff" \
  -F "dpi=300" \
  -F "apply_icc_profile=true"

# Check conversion status
curl http://localhost:8000/status/{job_id}

# Download converted file
curl http://localhost:8000/download/{job_id} -o converted_banner.tiff
```

## Docker Usage

### Building the Docker Image

```bash
# Build the image
docker build -t banner-converter .

# Build with specific tag
docker build -t banner-converter:v1.0.0 .
```

### Running with Docker

```bash
# Run the container
docker run -d \
  --name banner-converter \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/profiles:/app/profiles \
  banner-converter

# Run with environment file
docker run -d \
  --name banner-converter \
  --env-file .env \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/profiles:/app/profiles \
  banner-converter

# Run interactive container for debugging
docker run -it --rm \
  -v $(pwd):/app \
  banner-converter bash
```

## Docker Compose Usage

### Basic Compose Setup

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and start
docker-compose up --build -d

# Scale workers
docker-compose up --scale worker=3 -d
```

### Development with Compose

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up

# Run tests in container
docker-compose exec app python -m pytest

# Access application shell
docker-compose exec app bash

# View worker logs
docker-compose logs worker
```

### Sample docker-compose.yml structure:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
      - ./output:/app/output
      - ./profiles:/app/profiles  # ICC profiles directory
    environment:
      - ICC_PROFILE_PATH=/app/profiles/CoatedFOGRA39.icc
```

## GitHub Actions Deployment Notes

### Workflow Configuration

The project includes automated CI/CD pipelines for:

- **Testing**: Runs on every push and pull request
- **Building**: Creates Docker images for releases
- **Deployment**: Deploys to staging/production environments

### Key Deployment Steps:

1. **Environment Setup**:
   - Ensure `ICC_PROFILE_PATH` points to `/app/profiles/CoatedFOGRA39.icc`
   - Configure all required environment variables in GitHub Secrets
   - Set up Docker registry credentials

2. **ICC Profile Deployment**:
   - ICC profiles must be placed at `/app/profiles/CoatedFOGRA39.icc`
   - Ensure the profiles directory is properly mounted in containers
   - Verify file permissions allow read access

3. **Secrets Configuration**:
   ```
   DOCKER_USERNAME
   DOCKER_PASSWORD
   PRODUCTION_ENV_FILE
   ICC_PROFILE_BASE64  # Base64 encoded ICC profile for deployment
   ```

4. **Deployment Triggers**:
   - Push to `main` branch → Deploy to staging
   - Tagged releases → Deploy to production
   - Manual workflow dispatch available for emergency deployments

### Post-Deployment Verification:

```bash
# Verify ICC profile is accessible
docker exec <container> ls -la /app/profiles/CoatedFOGRA39.icc

# Test conversion with ICC profile
docker exec <container> python test_conversion.py --verify-icc

# Check application health
curl http://your-domain/health
```

## ICC Profile Placement

**Important**: The ICC profile must be placed at `/app/profiles/CoatedFOGRA39.icc`

### Local Development:
```bash
mkdir -p /app/profiles
cp your-profile.icc /app/profiles/CoatedFOGRA39.icc
```

### Docker Setup:
```bash
# Ensure the profiles directory is mounted
docker run -v $(pwd)/profiles:/app/profiles banner-converter
```

### Production Deployment:
- The ICC profile should be included in the Docker image or mounted as a volume
- Verify the file exists and has proper read permissions
- Path must be exactly `/app/profiles/CoatedFOGRA39.icc`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
