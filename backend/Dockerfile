FROM python:3.11-slim
WORKDIR /srv/backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ARG REQS=requirements.txt
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r ${REQS}
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
