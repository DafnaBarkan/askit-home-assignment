"""Filter the RentTheRunway fit-review dataset to an analysis-ready subset.

Keeps records where:
  - 'age' and 'rating' are present, and 10 <= age <= 80 (inclusive)
  - 'review_text' is present and has >= 10 whitespace-split words

Writes the survivors to data/filtered_reviews.json (JSON-lines, same shape as
the input records) so later scripts can load them directly.

Run: python3 src/filter_data.py
"""

import gzip
import json
from collections import Counter

SRC_PATH = "data/renttherunway_final_data.json.gz"
OUT_PATH = "data/filtered_reviews.json"

AGE_MIN = 10
AGE_MAX = 80
MIN_WORDS = 10


def is_present(value):
    """Non-null and, for strings, non-empty after stripping whitespace."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def to_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def decade_bucket(age):
    if age < 20:
        return "10s"
    if age < 30:
        return "20s"
    if age < 40:
        return "30s"
    if age < 50:
        return "40s"
    if age < 60:
        return "50s"
    return "60+"


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def histogram(counter, keys, total):
    width = max(len(str(k)) for k in keys)
    for k in keys:
        n = counter.get(k, 0)
        pct = 100.0 * n / total if total else 0.0
        bar = "#" * int(round(pct / 2))
        print(f"  {str(k):<{width}}  {n:>8,}  {pct:>5.1f}%  {bar}")


def main():
    total = 0
    kept = 0
    dropped = Counter()          # reason -> count (first failing reason per record)
    age_decades = Counter()
    ratings = Counter()

    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for rec in load(SRC_PATH):
            total += 1

            age_raw = rec.get("age")
            rating_raw = rec.get("rating")
            text_raw = rec.get("review_text")

            if not is_present(age_raw):
                dropped["age missing"] += 1
                continue
            age = to_int(age_raw)
            if age is None:
                dropped["age unparseable"] += 1
                continue
            if not (AGE_MIN <= age <= AGE_MAX):
                dropped[f"age outside {AGE_MIN}-{AGE_MAX}"] += 1
                continue
            if not is_present(rating_raw):
                dropped["rating missing"] += 1
                continue
            if not is_present(text_raw):
                dropped["review_text missing"] += 1
                continue
            if len(text_raw.split()) < MIN_WORDS:
                dropped[f"review_text under {MIN_WORDS} words"] += 1
                continue

            kept += 1
            age_decades[decade_bucket(age)] += 1
            ratings[str(rating_raw).strip()] += 1
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    section("FILTER RESULT")
    print(f"  original records : {total:,}")
    print(f"  kept             : {kept:,}  ({100.0 * kept / total:.2f}% of original)")
    print(f"  removed          : {total - kept:,}  ({100.0 * (total - kept) / total:.2f}%)")
    print("\n  removed by first failing criterion:")
    width = max(len(r) for r in dropped) if dropped else 1
    for reason, n in dropped.most_common():
        print(f"    {reason:<{width}}  {n:>8,}")

    section("AGE DISTRIBUTION BY DECADE (FILTERED)")
    histogram(age_decades, ["10s", "20s", "30s", "40s", "50s", "60+"], kept)

    section("RATING DISTRIBUTION (FILTERED)")
    keys = sorted(ratings, key=lambda k: (to_int(k) is None, to_int(k), k))
    histogram(ratings, keys, kept)

    section("OUTPUT")
    print(f"  wrote {kept:,} records to {OUT_PATH} (JSON-lines)")


if __name__ == "__main__":
    main()
