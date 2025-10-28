FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend_controller.py .
COPY socket_handlers.py .

CMD ["python", "backend_controller.py"]
