#!/usr/bin/env python3
"""Update Zotero relevance ratings and keyword tags without losing existing tags."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pyzotero import zotero


RATING_RE = re.compile(r"^⭐{1,5}$")


def get_client() -> zotero.Zotero:
    load_dotenv()
    return zotero.Zotero(
        os.environ["ZOTERO_LIBRARY_ID"].strip(),
        os.getenv("ZOTERO_LIBRARY_TYPE", "user").strip(),
        os.environ["ZOTERO_API_KEY"].strip(),
    )


def merge_tags(tags: list[dict], rating: Optional[int], keywords: list[str]) -> list[dict]:
    result = []
    for tag in tags:
        value = tag.get("tag", "")
        if rating is not None and RATING_RE.fullmatch(value):
            continue
        result.append(tag)

    existing = {tag.get("tag", "") for tag in result}
    additions = []
    if rating is not None:
        additions.append("⭐" * rating)
    additions.extend(keywords)

    for value in additions:
        if value not in existing:
            result.append({"tag": value})
            existing.add(value)
    return result


def validate_record(record: dict) -> None:
    rating = record.get("rating")
    keywords = record.get("keyword_tags", [])
    if rating is None and not keywords:
        raise ValueError(f"{record.get('key')}: rating and keyword_tags are both empty")
    if rating is not None and (not isinstance(rating, int) or not 1 <= rating <= 5):
        raise ValueError(f"{record.get('key')}: rating must be an integer from 1 to 5")
    if keywords and not 2 <= len(keywords) <= 5:
        raise ValueError(f"{record.get('key')}: keyword_tags must contain 2 to 5 tags")
    if len(keywords) != len(set(keywords)):
        raise ValueError(f"{record.get('key')}: keyword_tags contains duplicates")
    if any(not isinstance(tag, str) or not tag.startswith("#") or len(tag) == 1 for tag in keywords):
        raise ValueError(f"{record.get('key')}: every keyword tag must use #关键词 format")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    records = json.loads(args.input.read_text(encoding="utf-8"))["records"]
    client = get_client()
    updated = 0
    unchanged = 0

    for record in records:
        validate_record(record)
        item = client.item(record["key"])
        data = item["data"]
        old_tags = data.get("tags", [])
        new_tags = merge_tags(old_tags, record.get("rating"), record.get("keyword_tags", []))

        if new_tags == old_tags:
            print(f"[same] {data.get('title', record['key'])}")
            unchanged += 1
            continue

        rating_text = "⭐" * record["rating"] if record.get("rating") else "no rating change"
        print(
            f"[{'dry-run' if args.dry_run else 'update'}] "
            f"{data.get('title', record['key'])} | {rating_text} | "
            f"{' '.join(record.get('keyword_tags', []))}"
        )
        if not args.dry_run:
            data["tags"] = new_tags
            client.update_item(item)
        updated += 1

    print(f"Updated: {updated}; unchanged: {unchanged}; dry_run: {args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
