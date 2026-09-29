FROM python:3.12.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY scaffold/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
COPY verification/harness.py /harness.py
COPY verification/pytest_report.py /pytest_report.py
COPY verification/trusted_report.py /verifier/trusted_report.py
