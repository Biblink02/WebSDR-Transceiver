FROM python:3.12-slim
WORKDIR /app
COPY backend-controller/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend-controller/*.py ./
COPY shared/iq_protocol.py ./
USER 65532:65532
EXPOSE 8080
ENV PORT=8080
CMD ["python", "backend_controller.py"]
