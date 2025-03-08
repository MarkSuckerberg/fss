FROM python:3-slim

WORKDIR /usr/src/fss

VOLUME /usr/src/fss/data

COPY . .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt


ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "gunicorn", "--bind=0.0.0.0:8000", "app:app"]

EXPOSE 8000
