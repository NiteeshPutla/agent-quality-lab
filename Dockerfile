FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home app
COPY --chown=app:app . .
RUN mkdir -p /app/var && chown app:app /app/var
USER 10001
EXPOSE 8765
CMD ["uvicorn", "platform_lab.api:app", "--host", "0.0.0.0", "--port", "8765"]
