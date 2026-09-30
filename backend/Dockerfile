# Start from a small, official Python image rather than a full OS —
# smaller image, faster to build and push.
FROM python:3.12-slim

# Everything from here on happens inside /app in the container.
WORKDIR /app

# Copy just the requirements file first and install from it before
# copying the rest of the code. Docker caches each step — this way,
# if you only change your code (not your dependencies) later, Docker
# skips reinstalling everything from scratch.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the actual application code.
COPY . .

# Document that this container listens on port 8000 (informational —
# doesn't actually open the port by itself, see the Nebius endpoint
# setup in step 5).
EXPOSE 8000

# The command that runs when the container starts. 0.0.0.0 (not
# 127.0.0.1) is required here — it means "accept connections from
# anywhere," which is what lets traffic from outside the container
# actually reach it.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]