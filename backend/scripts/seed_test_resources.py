#!/usr/bin/env python
"""Seed downloadable test resources (Image/Audio/Video/Document/Text) into the platform.

This script is intended for development/testing only.

What it does:
- Reads a JSON manifest of remote resources
- Downloads each resource with size/type checks
- Creates MediaFile rows
- Attaches them to a target HeritageItem
- Ensures LOMGeneral + LOMRights exist and appends attribution text

Usage (from repo root or anywhere):
  python backend/scripts/seed_test_resources.py --heritage-item-id <uuid>

If no heritage item id is provided, the script creates a minimal HeritageItem.

Manifest:
  backend/scripts/test_resources_manifest.json

Notes:
- Text resources are currently represented as MediaFile(file_type='document') with a text/* mime_type.
- The manifest includes placeholders for audio/video/pdf; you should fill in PD/CC URLs you trust.
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

import django


def _setup_django() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "backend"
    sys.path.insert(0, str(backend_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    django.setup()


def _load_manifest(manifest_path: Path) -> dict:
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _download(url: str, max_bytes: int | None):
    try:
        import requests
    except Exception as e:
        raise RuntimeError(
            "`requests` is required for downloading. Install it in your backend env."
        ) from e

    headers = {
        # Some hosts (notably Wikimedia) reject default user agents.
        'User-Agent': 'HeritagePlatform-dev/0.1 (resource seeding; local testing)'
    }

    with requests.get(
        url,
        stream=True,
        timeout=30,
        allow_redirects=True,
        headers=headers,
    ) as resp:
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()

        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if max_bytes is not None and total > max_bytes:
                raise RuntimeError(f"Download exceeded max_bytes={max_bytes}: {url}")
            chunks.append(chunk)

        return b"".join(chunks), content_type


def _guess_extension(url: str, content_type: str) -> str:
    # URL-based hint first
    suffix = Path(url.split("?")[0]).suffix.lower().lstrip(".")
    if suffix:
        return suffix

    # Content-Type fallback
    mapping = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "audio/mpeg": "mp3",
        "video/mp4": "mp4",
        "application/pdf": "pdf",
        "text/plain": "txt",
    }
    return mapping.get(content_type, "bin")


def _ensure_lom_rights(lom_general, attribution_lines: list[str]):
    from apps.education.models import LOMRights

    rights, _ = LOMRights.objects.get_or_create(
        lom_general=lom_general,
        defaults={
            "cost": False,
            "copyright_and_other_restrictions": True,
            "description": "",
        },
    )

    existing = rights.description or ""
    add_block = "\n".join([l.strip() for l in attribution_lines if l.strip()])
    if add_block and add_block not in existing:
        rights.description = (existing + "\n" + add_block).strip() if existing else add_block
        rights.save(update_fields=["description"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default=str(Path(__file__).with_name("test_resources_manifest.json")),
        help="Path to JSON manifest",
    )
    parser.add_argument(
        "--heritage-item-id",
        default=None,
        help="UUID of an existing HeritageItem to attach resources to",
    )
    args = parser.parse_args()

    _setup_django()

    from django.contrib.gis.geos import Point
    from django.core.files.base import ContentFile
    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory, Parish, MediaFile
    from apps.education.models import LOMGeneral

    User = get_user_model()
    user = User.objects.first()

    manifest_path = Path(args.manifest).resolve()
    manifest = _load_manifest(manifest_path)

    if args.heritage_item_id:
        item = HeritageItem.objects.get(id=args.heritage_item_id)
    else:
        ht, _ = HeritageType.objects.get_or_create(
            slug="tangible",
            defaults={"name": "Tangible"},
        )
        hc, _ = HeritageCategory.objects.get_or_create(
            slug="architecture",
            defaults={"name": "Architecture"},
        )
        parish, _ = Parish.objects.get_or_create(name="Seed Parish", canton="Riobamba")

        item = HeritageItem.objects.create(
            title="Seeded Item (Test Resources)",
            description="Automatically generated item for resource playback tests.",
            heritage_type=ht,
            heritage_category=hc,
            parish=parish,
            location=Point(-78.65, -1.67),
            status="published",
            contributor=user,
            submission_date=timezone.now(),
        )

    lom_general, _ = LOMGeneral.objects.get_or_create(
        heritage_item=item,
        defaults={
            "title": item.title,
            "language": "es",
            "description": item.description,
            "coverage": "Riobamba, Ecuador",
            "structure": "atomic",
            "aggregation_level": 1,
        },
    )

    print(f"Target heritage item: {item.id} — {item.title}")
    print(f"Manifest: {manifest_path}")

    attribution_lines: list[str] = []

    for entry in manifest.get("resources", []):
        name = entry.get("name")
        file_type = entry.get("file_type")
        url = (entry.get("url") or "").strip()
        max_bytes = entry.get("max_bytes")
        expected_mime = entry.get("expected_mime")
        expected_mime_prefix = entry.get("expected_mime_prefix")
        attribution = entry.get("attribution")

        if not url:
            print(f"- Skipping (no url): {name}")
            continue

        print(f"- Downloading: {name} ({file_type})")
        data, content_type = _download(url, max_bytes)

        if expected_mime and content_type != expected_mime:
            raise RuntimeError(
                f"Unexpected Content-Type for {url}: got {content_type}, expected {expected_mime}"
            )
        if expected_mime_prefix and not content_type.startswith(expected_mime_prefix):
            raise RuntimeError(
                f"Unexpected Content-Type for {url}: got {content_type}, expected prefix {expected_mime_prefix}"
            )

        ext = _guess_extension(url, content_type)
        safe_stem = "".join(c if c.isalnum() else "_" for c in (name or "resource"))
        filename = f"{safe_stem}.{ext}".lower()

        mf = MediaFile(
            file_type=file_type,
            mime_type=content_type,
            alt_text=name or "",
            caption=name or "",
            uploaded_by=user,
        )
        mf.file.save(filename, ContentFile(data), save=True)

        if file_type == "image":
            item.images.add(mf)
        elif file_type == "audio":
            item.audio.add(mf)
        elif file_type == "video":
            item.video.add(mf)
        elif file_type == "document":
            item.documents.add(mf)
        else:
            raise RuntimeError(f"Unsupported file_type: {file_type}")

        if attribution:
            attribution_lines.append(f"- {name}: {attribution}")

    _ensure_lom_rights(lom_general, attribution_lines)

    print("Done.")
    print(f"Heritage item detail: /api/v1/heritage-items/{item.id}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
