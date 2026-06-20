FROM pathwaycom/pathway:latest


# Set working directory inside container
WORKDIR /app


COPY requirements.txt .


RUN pip install -r requirements.txt

# COPY . . - Uncomment during production

EXPOSE 8000
EXPOSE 11111

RUN touch /errors.json && echo '[]' > /errors.json

CMD ["sh", "-c", "uvicorn pipeline.server:app --host 0.0.0.0 --port 8000 --reload & python -m pipeline.Error_registry.RunBookDocumentStore"]