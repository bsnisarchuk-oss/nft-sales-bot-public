from typing import Any


def _normalize_media_url(url: str) -> str:
    """Преобразует IPFS/CID и HTTP(S) URL в нормализованный HTTPS-формат."""
    url = (url or "").strip()
    if not url:
        return ""

    # ipfs://<cid>/path
    if url.startswith("ipfs://"):
        rest = url[len("ipfs://"):].lstrip("/")
        return "https://cloudflare-ipfs.com/ipfs/" + rest

    # прямой CID (Qm...)
    if url.startswith("Qm") and len(url) > 40:
        return "https://cloudflare-ipfs.com/ipfs/" + url

    # уже http(s)
    if url.startswith("http://") or url.startswith("https://"):
        return url

    return ""


def extract_image_url(nft_data: dict[str, Any]) -> str:
    """
    Извлекает URL изображения из данных NFT.
    Ищет в metadata и корне, нормализует IPFS/HTTP через _normalize_media_url.
    """
    if not isinstance(nft_data, dict):
        return ""

    meta = nft_data.get("metadata") or {}
    if isinstance(meta, dict):
        for k in ("image", "image_url", "imageUrl", "preview", "cover"):
            v = meta.get(k)
            if isinstance(v, str):
                u = _normalize_media_url(v)
                if u:
                    return u
            if isinstance(v, list) and v:
                for it in v:
                    if isinstance(it, str):
                        u = _normalize_media_url(it)
                        if u:
                            return u

    # запасной вариант — ищем в корне
    for k in ("image", "preview"):
        v = nft_data.get(k)
        if isinstance(v, str):
            u = _normalize_media_url(v)
            if u:
                return u

    return ""
