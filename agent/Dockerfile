FROM python:3.11-slim

WORKDIR /app
COPY agent/src /app/agent/src

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/agent/src
RUN pip install --no-cache-dir 'psycopg[binary]>=3.2,<4'
EXPOSE 8090

CMD ["python", "-m", "incident_agent.server"]
