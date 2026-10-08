FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY стенд/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home runner
COPY . /app
USER 10001
CMD ["uvicorn","стенд.сервер:app","--host","0.0.0.0","--port","8080","--no-access-log"]
