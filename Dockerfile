FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements.txt

RUN groupadd --system kletserbot \
    && useradd --system --gid kletserbot --home-dir /app kletserbot \
    && mkdir --parents /app/data/cardpacks \
    && chown kletserbot:kletserbot /app/data/cardpacks

COPY --chown=kletserbot:kletserbot src ./src

USER kletserbot

CMD ["python", "-m", "kletserbot"]
