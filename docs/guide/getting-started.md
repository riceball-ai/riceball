# Getting Started

## Requirements

- Docker & Docker Compose
- Python 3.10+ (if not using Docker)
- Node.js 18+ (if not using Docker)

## Quick Start (All-in-One Docker)

> **Note**: This setup is for **preview and testing purposes only**. Please use with caution in production environments.

Run RiceBall with a single command using our All-in-One Docker image (includes SQLite & Local Storage):

```bash
docker run -d \
  -p 8000:8000 \
  -v riceball_storage:/app/storage \
  --name riceball \
  ghcr.io/riceball-ai/riceball:all-in-one-latest
```

Visit [http://localhost:8000](http://localhost:8000) to start using RiceBall.

Default Admin Credentials:
- Email: `admin@admin.com`
- Password: `admin123456`

## Production Deployment (Source Code)

For production environments requiring PostgreSQL and S3, you can deploy from source:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/riceball-ai/riceball.git
   cd riceball
   ```

2. **Configure Environment Variables**:
   Copy the backend example configuration file:
   ```bash
   cp backend/.env.example backend/.env
   ```
   You can modify the configuration in `backend/.env` as needed (e.g., database password, API keys).

3. **Start Services**:
   Start all services (backend, frontend, database) using Docker Compose:
   ```bash
   docker compose -f docker-compose.prod.yml up
   ```
   The container will automatically run database migrations, initialize system configuration, and create a default superuser upon startup.

4. **Access the Application**:
   Open your browser and visit [http://localhost:3000](http://localhost:3000) to start using RiceBall.

   Default Admin Credentials:
   - Email: `admin@admin.com`
   - Password: `admin123456`

## Using Just (Optional)

If you have [Just](https://github.com/casey/just) installed, you can use the following shortcut commands:

- Start development environment: `just dev`
