FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

ARG INSTALL_EXTRAS=voxcpm

RUN python -m pip install --no-cache-dir --upgrade pip && \
    if [ -n "${INSTALL_EXTRAS}" ]; then \
        python -m pip install --no-cache-dir ".[${INSTALL_EXTRAS}]"; \
    else \
        python -m pip install --no-cache-dir .; \
    fi

EXPOSE 8000

CMD ["voxcpm2-api"]
