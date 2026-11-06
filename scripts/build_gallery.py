from __future__ import annotations

import os
import re
import json
import time
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps, UnidentifiedImageError
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry


# ============================================================
# Configuration
# ============================================================

SOURCE_URL = os.environ["UU_PAGE_URL"]

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
MEDIA = DIST / "media"

THUMBS_DIR = MEDIA / "thumbs"
LARGE_DIR = MEDIA / "large"

# Set MAX_PHOTOS=20 for testing.
# Set MAX_PHOTOS=0 for all photos.
MAX_PHOTOS = int(os.getenv("MAX_PHOTOS", "0"))

# Network configuration
MAX_RETRIES = 5
DOWNLOAD_DELAY = float(os.getenv("DOWNLOAD_DELAY", "0.5"))
CONNECT_TIMEOUT = 30
READ_TIMEOUT = 180
CHUNK_SIZE = 1024 * 1024

# Image configuration
THUMB_MAX_SIZE = 400
LARGE_MAX_SIZE = 1600

THUMB_QUALITY = 75
LARGE_QUALITY = 82

# GitHub Pages safety limit
MAX_SITE_SIZE = 900 * 1024 * 1024

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36"
    ),
    "Referer": SOURCE_URL,
}

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


# ============================================================
# HTTP Session
# ============================================================

def create_session() -> requests.Session:
    session = requests.Session()

    retry = Retry(
        total=MAX_RETRIES,
        connect=MAX_RETRIES,
        read=MAX_RETRIES,
        status=MAX_RETRIES,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods={"GET"},
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=5,
        pool_maxsize=5,
    )

    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)

    return session


# ============================================================
# Helpers
# ============================================================

def format_size(size: int) -> str:
    return f"{size / (1024 ** 2):.2f} MB"


def normalize_identity(url: str) -> str:
    """
    Mirror servers can have different hostnames but
    point to the same file path.

    Ignore hostname and query parameters when identifying
    mirror duplicates.
    """
    parsed = urlparse(url)

    path = unquote(parsed.path).casefold()

    return path


def extract_filename(url: str) -> str:
    parsed = urlparse(url)
    filename = unquote(Path(parsed.path).name)

    if not filename:
        return "unknown-image"

    return filename


def is_valid_image_url(url: str) -> bool:
    parsed = urlparse(url)

    host = (parsed.hostname or "").lower()
    path = unquote(parsed.path).lower()

    valid_host = (
        host == "uupload.ir"
        or host.endswith(".uupload.ir")
    )

    valid_path = "/files/" in path

    extension = Path(path).suffix

    return (
        valid_host
        and valid_path
        and extension in SUPPORTED_EXTENSIONS
    )


# ============================================================
# Extract image links
# ============================================================

def extract_photos(session: requests.Session) -> list[dict]:

    print("\nFetching UUpload folder...")

    response = session.get(
        SOURCE_URL,
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type", ""
    ).lower()

    if "html" not in content_type:
        raise RuntimeError(
            f"Unexpected folder response: {content_type}"
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    photos = []
    seen_paths = set()

    for row in soup.find_all("tr"):

        for anchor in row.find_all("a", href=True):

            url = urljoin(
                SOURCE_URL,
                anchor["href"],
            )

            if not is_valid_image_url(url):
                continue

            identity = normalize_identity(url)

            # Ignore mirror duplicates, not duplicate filenames.
            if identity in seen_paths:
                continue

            seen_paths.add(identity)

            filename = extract_filename(url)

            photos.append({
                "filename": filename,
                "download_url": url,
            })

            # One direct image link per row.
            break

    if not photos:
        raise RuntimeError(
            "No direct image links found. "
            "UUpload page structure may have changed."
        )

    print(f"Found {len(photos)} unique image links.")

    if MAX_PHOTOS > 0:
        photos = photos[:MAX_PHOTOS]

        print(
            f"TEST MODE: processing only "
            f"{len(photos)} photos."
        )

    return photos


# ============================================================
# Download one image with retry
# ============================================================

def download_image(
    session: requests.Session,
    url: str,
    destination: Path,
) -> int:

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            size_bytes = 0

            with session.get(
                url,
                stream=True,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            ) as response:

                response.raise_for_status()

                content_type = response.headers.get(
                    "Content-Type", ""
                ).lower()

                if (
                    "text/html" in content_type
                    or "application/json" in content_type
                ):
                    raise ValueError(
                        f"Unexpected response type: {content_type}"
                    )

                with open(destination, "wb") as output:

                    for chunk in response.iter_content(
                        chunk_size=CHUNK_SIZE
                    ):

                        if not chunk:
                            continue

                        output.write(chunk)
                        size_bytes += len(chunk)

            if size_bytes == 0:
                raise ValueError("Downloaded file is empty.")

            # Verify actual image data.
            with Image.open(destination) as image:
                image.verify()

            return size_bytes

        except (
            requests.RequestException,
            OSError,
            ValueError,
            UnidentifiedImageError,
        ) as error:

            last_error = error

            if destination.exists():
                destination.unlink()

            if attempt == MAX_RETRIES:
                break

            wait_time = min(2 ** attempt, 30)

            print(
                f"\nDownload attempt {attempt} failed: {error}"
            )

            print(
                f"Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

    raise RuntimeError(
        f"Failed to download {url} "
        f"after {MAX_RETRIES} attempts: {last_error}"
    )


# ============================================================
# Image optimization
# ============================================================

def optimize_image(
    source: Path,
    destination: Path,
    max_size: int,
    quality: int,
):

    with Image.open(source) as original:

        image = ImageOps.exif_transpose(original)

        # Preserve transparency where present.
        if image.mode in ("RGBA", "LA"):
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")

        image.thumbnail(
            (max_size, max_size),
            Image.Resampling.LANCZOS,
        )

        image.save(
            destination,
            format="WEBP",
            quality=quality,
            method=6,
        )


# ============================================================
# Prepare static website
# ============================================================

def prepare_site():

    print("\nPreparing website...")

    required_items = [
        "index.html",
        "assets",
    ]

    for item in required_items:

        source = ROOT / item
        destination = DIST / item

        if not source.exists():
            raise FileNotFoundError(
                f"Required website file is missing: {source}"
            )

        if source.is_dir():

            shutil.copytree(
                source,
                destination,
                dirs_exist_ok=True,
            )

        else:

            shutil.copy2(
                source,
                destination,
            )

    nojekyll = ROOT / ".nojekyll"

    if nojekyll.exists():
        shutil.copy2(
            nojekyll,
            DIST / ".nojekyll",
        )


# ============================================================
# Build gallery
# ============================================================

def build_gallery():

    THUMBS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    LARGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    session = create_session()

    photos = extract_photos(session)

    manifest = []

    total_original = 0
    total_optimized = 0

    print("\nStarting image processing...\n")

    for index, photo in enumerate(
        tqdm(photos, desc="Processing"),
        start=1,
    ):

        original_filename = photo["filename"]

        # Unique output name prevents filename collisions.
        image_name = f"{index:05d}.webp"

        thumb_path = THUMBS_DIR / image_name
        large_path = LARGE_DIR / image_name

        # Temporary original image is deleted after each photo.
        suffix = Path(original_filename).suffix or ".jpg"

        temp_path = None

        try:

            with tempfile.NamedTemporaryFile(
                suffix=suffix,
                delete=False,
            ) as temp:

                temp_path = Path(temp.name)

            size_bytes = download_image(
                session,
                photo["download_url"],
                temp_path,
            )

            # Large preview
            optimize_image(
                temp_path,
                large_path,
                max_size=LARGE_MAX_SIZE,
                quality=LARGE_QUALITY,
            )

            # Thumbnail
            optimize_image(
                temp_path,
                thumb_path,
                max_size=THUMB_MAX_SIZE,
                quality=THUMB_QUALITY,
            )

            optimized_size = (
                thumb_path.stat().st_size
                + large_path.stat().st_size
            )

            total_original += size_bytes
            total_optimized += optimized_size

            manifest.append({
                "filename": original_filename,
                "size": format_size(size_bytes),
                "size_bytes": size_bytes,
                "download_url": photo["download_url"],
                "thumb": f"media/thumbs/{image_name}",
                "large": f"media/large/{image_name}",
            })

        finally:

            if temp_path and temp_path.exists():
                temp_path.unlink()

        if DOWNLOAD_DELAY > 0:
            time.sleep(DOWNLOAD_DELAY)

    # Save manifest only after all photos are processed.
    manifest_path = MEDIA / "photos.json"
    temp_manifest = MEDIA / "photos.json.tmp"

    with temp_manifest.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            manifest,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temp_manifest.replace(manifest_path)

    print("\n" + "=" * 50)
    print("GALLERY BUILD COMPLETED")
    print("=" * 50)

    print(f"Photos processed: {len(manifest)}")
    print(f"Original size: {format_size(total_original)}")
    print(f"Optimized size: {format_size(total_optimized)}")

    if total_original:
        reduction = (
            1 - total_optimized / total_original
        ) * 100

        print(f"Size reduction: {reduction:.2f}%")

    print("=" * 50)


# ============================================================
# Main
# ============================================================

def main():

    if DIST.exists():
        shutil.rmtree(DIST)

    DIST.mkdir(
        parents=True,
        exist_ok=True,
    )

    prepare_site()

    build_gallery()

    site_size = sum(
        path.stat().st_size
        for path in DIST.rglob("*")
        if path.is_file()
    )

    print(
        f"\nFinal site size: {format_size(site_size)}"
    )

    if site_size > MAX_SITE_SIZE:
        raise RuntimeError(
            "Generated site exceeds the 900 MB safety limit."
        )


if __name__ == "__main__":
    main()
