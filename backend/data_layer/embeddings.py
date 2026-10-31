"""
backend/data_layer/embeddings.py
---------------------------------
Voyage AI embedding helpers.
Uses voyageai.Client.multimodal_embed() for both text and images.
"""

from __future__ import annotations

import io
import logging
import time
from pathlib import Path
from typing import Sequence

from PIL import Image

from .config import cfg

logger = logging.getLogger(__name__)

_voyage_client = None


def _get_client():
    global _voyage_client
    if _voyage_client is None:
        if not cfg.voyage_api_key:
            raise EnvironmentError(
                "VOYAGE_API_KEY is not set.  "
                "Use --skip-embeddings to run without embeddings."
            )
        import voyageai  # noqa: PLC0415
        _voyage_client = voyageai.Client(api_key=cfg.voyage_api_key)
    return _voyage_client


def _retry(fn, retries: int = 5, backoff: float = 2.0):
    """Call *fn* with exponential backoff and rate-limit handling (3 RPM free tier)."""
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            err_str = str(exc).lower()
            if "rate limit" in err_str or "3 rpm" in err_str or "429" in err_str or "tpm" in err_str:
                wait = 22.0 + attempt * 2.0
                logger.warning(
                    "Voyage rate limit hit (3 RPM free tier). Waiting %.1fs for rate window (attempt %d/%d)...",
                    wait, attempt + 1, retries,
                )
            else:
                wait = backoff ** attempt
                logger.warning("Voyage API error (attempt %d/%d): %s — retrying in %.1fs",
                               attempt + 1, retries, exc, wait)
            time.sleep(wait)


def embed_texts(texts: Sequence[str], input_type: str = "document") -> list[list[float]]:
    """
    Embed a batch of plain-text strings.

    input_type: "document" for stored content, "query" for search queries.
    Returns a list of 1024-dimensional float vectors.
    """
    if not texts:
        return []

    client = _get_client()

    # In Voyage AI Python SDK, inputs is List[List[Union[str, Image]]]
    inputs = [[t] for t in texts]

    def call():
        result = client.multimodal_embed(
            inputs=inputs,
            model=cfg.voyage_model,
            input_type=input_type,
        )
        return result.embeddings

    embeddings = _retry(call)

    for i, emb in enumerate(embeddings):
        if len(emb) != cfg.embedding_dimensions:
            raise ValueError(
                f"Expected {cfg.embedding_dimensions} dimensions, got {len(emb)} "
                f"for text index {i}."
            )
    return embeddings


def embed_images_with_text(items: Sequence[tuple[bytes, str]]) -> list[list[float]]:
    """
    Embed multiple (image_bytes, description) pairs in a single request
    using the multimodal model.

    Returns a list of 1024-dimensional float vectors.
    """
    if not items:
        return []

    client = _get_client()

    inputs = [[desc, Image.open(io.BytesIO(img_bytes))] for img_bytes, desc in items]

    def call():
        result = client.multimodal_embed(
            inputs=inputs,
            model=cfg.voyage_model,
            input_type="document",
        )
        return result.embeddings

    embeddings = _retry(call)

    for i, emb in enumerate(embeddings):
        if len(emb) != cfg.embedding_dimensions:
            raise ValueError(
                f"Expected {cfg.embedding_dimensions} dimensions, got {len(emb)} for image {i}."
            )
    return embeddings


def embed_image_with_text(image_bytes: bytes, description: str) -> list[float]:
    """
    Embed a single PNG/JPEG together with a contextual description
    using the multimodal model.

    Returns a 1024-dimensional float vector.
    """
    return embed_images_with_text([(image_bytes, description)])[0]


def embed_query(query: str) -> list[float]:
    """Embed a single search query string."""
    results = embed_texts([query], input_type="query")
    return results[0]


def embed_texts_batched(
    texts: Sequence[str],
    batch_size: int = 50,
    input_type: str = "document",
    delay_between_batches: float = 21.0,
) -> list[list[float]]:
    """
    Embed a large list of texts in batches to stay within API limits.
    Default delay is 21s to cleanly adhere to the 3 RPM free tier rate limit.
    """
    all_embeddings: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start: start + batch_size]
        logger.info("Embedding batch %d–%d / %d …",
                    start + 1, start + len(batch), len(texts))
        all_embeddings.extend(embed_texts(batch, input_type=input_type))
        if start + batch_size < len(texts):
            logger.info("Waiting %.1fs between batches to respect 3 RPM rate limit...", delay_between_batches)
            time.sleep(delay_between_batches)
    return all_embeddings

