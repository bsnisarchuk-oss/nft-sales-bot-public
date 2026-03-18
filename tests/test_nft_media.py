"""Tests for utils/nft_media.py — извлечение и нормализация URL изображений NFT."""

from utils.nft_media import _normalize_media_url, extract_image_url

# --- _normalize_media_url ---

def test_normalize_https():
    assert _normalize_media_url("https://example.com/img.png") == "https://example.com/img.png"


def test_normalize_http():
    assert _normalize_media_url("http://example.com/img.png") == "http://example.com/img.png"


def test_normalize_ipfs_protocol():
    url = _normalize_media_url("ipfs://QmXyz123/image.png")
    assert url == "https://cloudflare-ipfs.com/ipfs/QmXyz123/image.png"


def test_normalize_ipfs_cid_direct():
    url = _normalize_media_url("QmXyz123456789012345678901234567890abcdef")
    assert url.startswith("https://cloudflare-ipfs.com/ipfs/Qm")


def test_normalize_empty():
    assert _normalize_media_url("") == ""
    assert _normalize_media_url(None) == ""


def test_normalize_unknown_scheme():
    assert _normalize_media_url("ftp://server/file") == ""


# --- extract_image_url ---

def test_extract_from_metadata_image():
    nft = {"metadata": {"image": "https://example.com/nft.png"}}
    assert extract_image_url(nft) == "https://example.com/nft.png"


def test_extract_from_metadata_image_url():
    nft = {"metadata": {"image_url": "https://example.com/nft.png"}}
    assert extract_image_url(nft) == "https://example.com/nft.png"


def test_extract_from_root_image():
    """Fallback на корневое поле image."""
    nft = {"metadata": {}, "image": "https://example.com/root.png"}
    assert extract_image_url(nft) == "https://example.com/root.png"


def test_extract_from_metadata_list():
    """image может быть списком URL."""
    nft = {"metadata": {"image": ["https://example.com/1.png", "https://example.com/2.png"]}}
    assert extract_image_url(nft) == "https://example.com/1.png"


def test_extract_empty_metadata():
    assert extract_image_url({"metadata": {}}) == ""


def test_extract_no_dict():
    assert extract_image_url("not a dict") == ""


def test_extract_ipfs():
    nft = {"metadata": {"image": "ipfs://QmABCDEF123456/image.png"}}
    url = extract_image_url(nft)
    assert url.startswith("https://cloudflare-ipfs.com/ipfs/")
