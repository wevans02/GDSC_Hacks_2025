# ---- Base Stage: Use a slim and secure Python base image ----
# Using a specific version is better for reproducibility.
FROM python:3.11-slim-bullseye AS base

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# ---- Build Stage: Install dependencies ----
# This leverages Docker's layer caching. This step only re-runs if
# requirements.txt changes, speeding up subsequent builds.
FROM base AS builder

# Install build tools needed for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# Copy only the requirements file to cache the dependency layer
COPY requirements.txt .

# Install the Python dependencies
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# ---- Final Stage: Create the production image ----
# This stage creates the final, lean image.
FROM base AS final

# Copy the installed wheels from the builder stage`
COPY --from=builder /app/wheels /wheels

# Install the dependencies from the wheels without needing build tools
RUN pip install --no-cache /wheels/*

# Create a non-root user for security
RUN useradd --create-home appuser
USER appuser

# Set the working directory for the non-root user
WORKDIR /home/appuser/app

# Copy the application code into the container
COPY . .

# Expose the port the app will run on.
# We'll use 8080 as a common alternative to 5000.
EXPOSE 8080

# The command to run the application using Waitress.
# --host=0.0.0.0 makes the server accessible from outside the container.
# app:app refers to the 'app' object in the 'app.py' file.
CMD ["gunicorn", "--worker-class", "gevent", "--workers=4", "--bind=0.0.0.0:8080", "app:app"]

# docker run \
#     --detach \
#     --name bylaw-api \
#     --restart always \
#     --env-file ./.env \
#     -p 8080:8080 \
#     --cpus="2.0" \
#     --memory="4g" \
#     bylaw-rag-api