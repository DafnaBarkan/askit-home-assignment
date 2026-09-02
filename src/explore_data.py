"""Exploration of the RentTheRunway fit-review dataset (gzipped JSON-lines).

Reports raw descriptive statistics only; makes no recommendations.
Run: python3 src/explore_data.py
"""

import gzip
import json
import statistics
from collections import Counter, OrderedDict

DATA_PATH = "data/renttherunway_final_data.json.gz"


def is_present(value):
    """Non-null and, for strings, non-empty after stripping whitespace."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def to_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


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
    field_order = OrderedDict()          # field -> first-seen order
    examples = {}                        # field -> up to 3 example values
    present_counts = Counter()           # field -> count of non-null/non-empty
    ages = []
    age_decades = Counter()
    age_unparsed = 0
    ratings = Counter()
    word_counts = []
    both_age_text = 0
    age_rating_text = 0

    for rec in load(DATA_PATH):
        total += 1

        for field, value in rec.items():
            if field not in field_order:
                field_order[field] = len(field_order)
                examples[field] = []
            if is_present(value):
                present_counts[field] += 1
                if len(examples[field]) < 3:
                    examples[field].append(value)

        age_raw = rec.get("age")
        rating_raw = rec.get("rating")
        text_raw = rec.get("review_text")

        has_age = is_present(age_raw)
        has_rating = is_present(rating_raw)
        has_text = is_present(text_raw)

        if has_age:
            age = to_int(age_raw)
            if age is None:
                age_unparsed += 1
            else:
                ages.append(age)
                if age < 10:
                    age_decades["<10"] += 1
                elif age < 20:
                    age_decades["10s"] += 1
                elif age < 30:
                    age_decades["20s"] += 1
                elif age < 40:
                    age_decades["30s"] += 1
                elif age < 50:
                    age_decades["40s"] += 1
                elif age < 60:
                    age_decades["50s"] += 1
                else:
                    age_decades["60+"] += 1

        if has_rating:
            ratings[str(rating_raw).strip()] += 1

        if has_text:
            word_counts.append(len(text_raw.split()))

        if has_age and has_text:
            both_age_text += 1
            if has_rating:
                age_rating_text += 1

    # 1. Total records
    section("1. TOTAL RECORDS")
    print(f"  {total:,}")

    # 2. Fields + examples
    section("2. FIELDS AND EXAMPLE VALUES")
    for field in field_order:
        print(f"\n  {field!r}")
        for ex in examples[field]:
            s = ex if isinstance(ex, str) else repr(ex)
            if isinstance(ex, str) and len(s) > 140:
                s = s[:140] + " ..."
            print(f"      - {s}")

    # 3. Non-null / non-empty counts
    section("3. NON-NULL / NON-EMPTY COUNT PER FIELD")
    width = max(len(f) for f in field_order)
    for field in field_order:
        n = present_counts[field]
        print(f"  {field:<{width}}  {n:>8,}  ({100.0 * n / total:5.1f}% of {total:,})")

    # 4. Age distribution
    section("4. AGE DISTRIBUTION")
    print(f"  records with non-empty age : {present_counts['age']:,}")
    print(f"  parsed as integer          : {len(ages):,}")
    print(f"  non-empty but unparseable  : {age_unparsed:,}")
    if ages:
        print(f"  min    : {min(ages)}")
        print(f"  max    : {max(ages)}")
        print(f"  median : {statistics.median(ages)}")
        print(f"  mean   : {statistics.mean(ages):.2f}")
        print("\n  histogram by decade (of parsed ages):")
        histogram(age_decades, ["<10", "10s", "20s", "30s", "40s", "50s", "60+"], len(ages))

    # 5. Rating distribution
    section("5. RATING DISTRIBUTION")
    print(f"  records with non-empty rating : {present_counts.get('rating', 0):,}")
    print(f"  records with missing rating   : {total - present_counts.get('rating', 0):,}")
    print()
    keys = sorted(ratings, key=lambda k: (to_int(k) is None, to_int(k), k))
    histogram(ratings, keys, sum(ratings.values()))

    # 6. Review word counts
    section("6. REVIEW_TEXT WORD COUNT (whitespace split)")
    print(f"  records with non-empty review_text : {len(word_counts):,}")
    if word_counts:
        print(f"  min    : {min(word_counts)}")
        print(f"  max    : {max(word_counts)}")
        print(f"  median : {statistics.median(word_counts)}")
        print(f"  mean   : {statistics.mean(word_counts):.2f}")
        buckets = ["0-9", "10-24", "25-49", "50-74", "75-99", "100-149", "150-199", "200-299", "300+"]
        wc_hist = Counter()
        for w in word_counts:
            if w < 10:
                wc_hist["0-9"] += 1
            elif w < 25:
                wc_hist["10-24"] += 1
            elif w < 50:
                wc_hist["25-49"] += 1
            elif w < 75:
                wc_hist["50-74"] += 1
            elif w < 100:
                wc_hist["75-99"] += 1
            elif w < 150:
                wc_hist["100-149"] += 1
            elif w < 200:
                wc_hist["150-199"] += 1
            elif w < 300:
                wc_hist["200-299"] += 1
            else:
                wc_hist["300+"] += 1
        print("\n  histogram:")
        histogram(wc_hist, buckets, len(word_counts))

    # 7. Joint completeness
    section("7. JOINT COMPLETENESS")
    print(f"  age AND review_text non-empty            : {both_age_text:,}  ({100.0 * both_age_text / total:.1f}%)")
    print(f"  age AND rating AND review_text non-empty : {age_rating_text:,}  ({100.0 * age_rating_text / total:.1f}%)")


if __name__ == "__main__":
    main()
