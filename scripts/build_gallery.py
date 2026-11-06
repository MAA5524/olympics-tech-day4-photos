
import os
import re
import json
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps
from tqdm import tqdm


SOURCE_URL = os.environ["UU_PAGE_URL"]

ROOT = Path(".")
DIST = ROOT / "dist"
MEDIA = DIST / "media"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": SOURCE_URL,
}

MAX_SITE_SIZE = 900 * 1024 * 1024


def format_size(size):
    return f"{size / (1024 ** 2):.2f} MB"


def extract_photos():
    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=60
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    photos = []
    seen_names = set()

    for row in soup.find_all("tr"):
        for anchor in row.find_all("a", href=True):

            url = urljoin(SOURCE_URL, anchor["href"])
            parsed = urlparse(url)

            host = parsed.hostname or ""
            filename = unquote(Path(parsed.path).name)

            if not (
                host.endswith(".uupload.ir")
                and "/files/" in parsed.path
                and parsed.path.lower().endswith(
                    (".jpg", ".jpeg", ".png")
                )
                and "download" in parsed.query.lower()
            ):
                continue

            if filename.casefold() in seen_names:
                continue

            seen_names.add(filename.casefold())

            photos.append({
                "filename": filename,
                "download_url": url
            })

    if not photos:
        raise RuntimeError(
            "No photos found. Check the UUpload page structure."
        )

    print(f"Found {len(photos)} unique photos.")

    return photos


def optimize_image(source, destination, max_size, quality):
    with Image.open(source) as original:

        image = ImageOps.exif_transpose(original)

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        image.thumbnail(
            (max_size, max_size),
            Image.Resampling.LANCZOS
        )

        image.save(
            destination,
            "WEBP",
            quality=quality,
            method=6
        )


def build_gallery():

    (MEDIA / "thumbs").mkdir(parents=True, exist_ok=True)
    (MEDIA / "large").mkdir(parents=True, exist_ok=True)

    photos = extract_photos()
    manifest = []

    total_original = 0
    total_optimized = 0

    session = requests.Session()
    session.headers.update(HEADERS)

    for index, photo in enumerate(
        tqdm(photos, desc="Processing photos"),
        start=1
    ):

        with tempfile.NamedTemporaryFile(
            suffix=Path(photo["filename"]).suffix
        ) as temp:

            response = session.get(
                photo["download_url"],
                stream=True,
                timeout=(30, 180)
            )
            response.raise_for_status()

            size_bytes = 0

            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    temp.write(chunk)
                    size_bytes += len(chunk)

            temp.flush()

            image_name = f"{index:05d}.webp"

            thumb_path = MEDIA / "thumbs" / image_name
            large_path = MEDIA / "large" / image_name

            optimize_image(
                temp.name,
                large_path,
                max_size=1600,
                quality=82
            )

            optimize_image(
                temp.name,
                thumb_path,
                max_size=400,
                quality=75
            )

        optimized_size = (
            thumb_path.stat().st_size
            + large_path.stat().st_size
        )

        total_original += size_bytes
        total_optimized += optimized_size

        manifest.append({
            "filename": photo["filename"],
            "size": format_size(size_bytes),
            "size_bytes": size_bytes,
            "download_url": photo["download_url"],
            "thumb": f"media/thumbs/{image_name}",
            "large": f"media/large/{image_name}"
        })

    with (MEDIA / "photos.json").open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            manifest,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\nProcessing completed!")
    print(f"Photos: {len(manifest)}")
    print(f"Original size: {format_size(total_original)}")
    print(f"Optimized size: {format_size(total_optimized)}")

    return total_optimized


def prepare_site():

    for item in ("index.html", "assets", ".nojekyll"):

        source = ROOT / item
        destination = DIST / item

        if not source.exists():
            continue

        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)


if __name__ == "__main__":

    if DIST.exists():
        shutil.rmtree(DIST)

    DIST.mkdir(parents=True)

    prepare_site()
    build_gallery()

    site_size = sum(
        path.stat().st_size
        for path in DIST.rglob("*")
        if path.is_file()
    )

    print(f"Final site size: {format_size(site_size)}")

    if site_size > MAX_SITE_SIZE:
        raise RuntimeError(
            "The generated site exceeds the 900 MB safety limit."
        )
