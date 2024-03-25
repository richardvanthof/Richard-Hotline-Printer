# Use the official Python 3.8 slim image as the base image
FROM python:3.12-slim


# Set the working directory within the container
WORKDIR /app

# Copy the necessary files and directories into the container
COPY ./requirements.txt /app

# Upgrade pip and install Python dependencies
RUN pip3 install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# copy all src files
COPY . /app

# Expose port 8000 for the Flask application
EXPOSE 8000

# Define the command to run the Flask application using Gunicorn
CMD ["waitress-serve", "--port=8000", "init:app"]