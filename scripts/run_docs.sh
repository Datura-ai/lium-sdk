#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define a name for your Docker image
IMAGE_NAME="celium-sdk-docs"

# Define the port to map from the host to the container
HOST_PORT=8080
CONTAINER_PORT=8080

# Build the Docker image
# The . at the end specifies the build context (current directory)
echo "Building Docker image: $IMAGE_NAME..."
docker build -t $IMAGE_NAME .

echo "Docker image built successfully: $IMAGE_NAME"

# Run the Docker container
# -d: Run container in detached mode (in the background)
# -p: Publish a container's port(s) to the host (hostPort:containerPort)
# --rm: Automatically remove the container when it exits
echo "Running Docker container $IMAGE_NAME on port $HOST_PORT..."
docker run -d -p $HOST_PORT:$CONTAINER_PORT --rm $IMAGE_NAME

echo "Celium SDK documentation website is running on http://localhost:$HOST_PORT"
echo "To stop the container, run: docker ps (to find the container ID) and then docker stop <container_id>"
