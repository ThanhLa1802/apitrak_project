FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared package outside /app so volume mounts cannot shadow it
COPY shared/ /packages/shared/
ENV PYTHONPATH=/packages

COPY django-core/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY django-core/ .

RUN DJANGO_SETTINGS_MODULE=config.settings.development \
    SECRET_KEY=build-placeholder \
    DATABASE_URL=postgis://x:x@localhost/x \
    REDIS_URL=redis://localhost:6379/0 \
    GDAL_LIBRARY_PATH="" \
    GEOS_LIBRARY_PATH="" \
    PROJ_LIBRARY_PATH="" \
    CONDA_ENV_PATH="" \
    python manage.py collectstatic --noinput
