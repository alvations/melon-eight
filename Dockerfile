# Container image for hosting the game (works as-is on Hugging Face Spaces
# with the Docker SDK, which expects the app on port 7860).
FROM python:3.11-slim

# Hugging Face Spaces runs containers as a non-root user (uid 1000).
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HOST=0.0.0.0 \
    PORT=7860

WORKDIR /app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

EXPOSE 7860

# IMPORTANT: a single worker. Game state (and each corridor's answer) lives in
# memory in one process; multiple workers would split that state and break runs.
# Threads give plenty of concurrency for this lightweight app.
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:7860", "app:app"]
