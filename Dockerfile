# Use official Python image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Ensure the logs directory exists
RUN mkdir -p /app/logs


# Run the Flask app
CMD ["sh", "-c", "python -u discord_bot.py"]
