# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install FFmpeg and other dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    python3-dev \
    libboost-python-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install required Python packages
RUN pip install --no-cache-dir \
    websockets \
    asyncio \
    opencv-python \
    numpy \
    pillow \
    av  # PyAV for FFmpeg integration

# Copy the project files into the container
COPY main.py /app/
COPY tello_bridge /app/tello_bridge/

# Copy the H264 decoder native library from tello_Video
COPY tello_Video/h264decoder/Linux/libh264decoder.so /usr/local/lib/python3.9/site-packages/

# Create symbolic link as required by some systems
RUN ln -sf /usr/local/lib/python3.9/site-packages/libh264decoder.so /usr/local/lib/python3.9/site-packages/libh264decoder.so.0

# Make the module accessible to Python
RUN echo "/usr/local/lib/python3.9/site-packages" > /usr/local/lib/python3.9/site-packages/h264decoder.pth

# Create an empty __init__.py in the site-packages directory to make Python recognize it as a package
RUN touch /usr/local/lib/python3.9/site-packages/__init__.py

# Make sure scripts are executable
RUN chmod +x /app/main.py

# Define the command to run your script
CMD ["python", "main.py"]
