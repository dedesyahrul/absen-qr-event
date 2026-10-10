FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/app ./app
COPY docs/all-participants.md /input/all-participants.md
