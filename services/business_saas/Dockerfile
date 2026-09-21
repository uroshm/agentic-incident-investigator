FROM python:3.11-slim

WORKDIR /app
COPY services /app/services

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV BUSINESS_SAAS_HOST=0.0.0.0
EXPOSE 8080

CMD ["python", "-m", "services.business_saas.server"]
