# Use the official Python 3.8 slim image as the base image
FROM python:3.8-slim

# Set the working directory within the container
WORKDIR /app
# Copy the necessary files and directories into the container
RUN pip freeze > requirements.txt
COPY ./requirements.txt /app

# Upgrade pip and install Python dependencies
RUN pip3 install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# copy all src files
COPY /src /app

# Expose port 5000 for the Flask application
EXPOSE 80

# Define the command to run the Flask application using Gunicorn
CMD ["gunicorn", "application:app", "-b", "0.0.0.0:80", "-w", "4"]