# One image for backend, worker and migrate (D27). Compose picks the command.
FROM python:3.13.17-slim-trixie

# Logs show up at once in `docker compose logs` (no waiting in a buffer),
# and Python doesn't write .pyc cache files into the image.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Packages first. Docker reuses this layer until requirements.txt changes,
# so a code change doesn't reinstall every package.
COPY requirements.txt .
RUN pip install -r requirements.txt

# A normal user with no special rights, so the app never runs as root.
RUN useradd --create-home parley

# Then the code. It stays owned by root, so the app can read it but not change it.
COPY . .

USER parley

EXPOSE 8000
# A list (not one string), so uvicorn itself is the main program and gets
# `docker stop`'s signal. --forwarded-allow-ips "*": trust the real browser IP
# that Nginx passes on, safe because only Parley's network can reach port 8000 (D27).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
