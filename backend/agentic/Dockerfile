# Use a lightweight Python base image
FROM pytorch/pytorch


# Set working directory inside container
WORKDIR /app

# Copy project dependencies
COPY requirements.txt .

# Install Python dependencies (if file exists)
RUN pip install --no-cache-dir -r requirements.txt



EXPOSE 5333

CMD ["uvicorn", "agentic.app:app", "--host", "0.0.0.0", "--port", "5333", "--reload"]

