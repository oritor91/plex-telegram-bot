# Use the official Python base image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

RUN apt-get update; \ 
    apt-get install -y gcc vim

# Install the required packages
RUN pip install --upgrade pip;\
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Command to run the bot
CMD ["python", "-m", "telegram_media_bot.bot"]
