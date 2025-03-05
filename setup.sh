#!/bin/bash

# Set environment variables for Flask
export FLASK_APP=app.py
export FLASK_ENV=development  # Use "production" in production environments
export OLLAMA_HOST=127.0.0.1:9999

ollama  serve &

# Initialize the migration repository if it doesn't exist
if [ ! -d "migrations" ]; then
    echo "Initializing migrations..."
    flask db init
fi

# Create a migration script (based on your current models)
echo "Creating migration script..."
flask db migrate -m "Initial migration."

# Apply the migration to upgrade the database schema
echo "Upgrading database..."
flask db upgrade

# Seed the database with initial data
echo "Seeding the database..."
python seed.py

# Start the Flask backend server
echo "Starting the backend server..."
flask run
