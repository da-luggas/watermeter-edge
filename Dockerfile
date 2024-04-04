# Use an official Python runtime as a parent image
FROM python:3.9-slim

RUN apt update && apt install wget -y

# Set the working directory in the container
WORKDIR /watermeter

# Copy the current directory contents into the container at /usr/src/app
COPY main.py /watermeter/main.py
RUN wget https://github.com/jomjol/AI-on-the-edge-device/raw/rolling/sd-card/config/ana-class100_0171_s1_q.tflite
RUN wget https://github.com/jomjol/AI-on-the-edge-device/raw/rolling/sd-card/config/dig-cont_0700_s3_q.tflite

RUN rm -r test
RUN rm Dockerfile

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir tflite_runtime opencv-python-headless numpy paho-mqtt

# Run script.py when the container launches
CMD ["python", "-u", "./main.py"]
