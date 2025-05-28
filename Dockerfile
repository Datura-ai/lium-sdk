# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy pyproject.toml (and lock file if applicable)
COPY . .
# If you use Poetry, you might also want to copy poetry.lock and use poetry install
# COPY poetry.lock ./

# Install project and dependencies from pyproject.toml
# This command assumes your pyproject.toml is set up for a standard build.
# If you have specific extras for documentation (e.g., [docs]), you might use:
RUN pip install --no-cache-dir .[docs]
RUN pip install --no-cache-dir .

# Bundle app source
COPY . .

# Expose the port the app runs on (if your docs site is served)
# Update this port if your documentation server uses a different one
EXPOSE 8080

# Command to run the app / serve docs
# Replace this with your actual command to build and serve the documentation.
# For example, if using MkDocs: CMD ["mkdocs", "serve", "-a", "0.0.0.0:8000"]
# Or for Sphinx, you might need a custom script or two steps (build then serve)
# CMD [ "your_command_to_serve_docs" ]
CMD ["mkdocs", "serve", "--dev-addr", "0.0.0.0:8080"]