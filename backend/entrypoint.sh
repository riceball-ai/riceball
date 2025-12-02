#!/bin/sh

# Container startup entry script
# Execute database migrations, initialize system configuration, create default superuser

set -e  # Exit immediately on error

echo "🚀 Starting application initialization..."

# 1. Execute database migrations
echo "📦 Running database migrations..."

alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully"
else
    echo "❌ Database migrations failed"
    exit 1
fi

# 2. Initialize system configuration
echo "⚙️  Initializing system configuration..."

python scripts/init_system_config.py

if [ $? -eq 0 ]; then
    echo "✅ System configuration initialized successfully"
else
    echo "❌ System configuration initialization failed"
    exit 1
fi

# 3. Create default superuser (if environment variables are provided)
echo "👤 Creating default superuser..."

SUPERUSER_EMAIL=admin@admin.com SUPERUSER_PASSWORD=admin123456 python scripts/create_superuser.py

if [ $? -eq 0 ]; then
    echo "✅ Default superuser created/updated successfully"
else
    echo "⚠️  Warning: Default superuser creation failed, you may need to create one manually"
fi

echo "✨ Application initialization completed!"

# 4. Start the application
echo "🌟 Starting the application..."

exec "$@"