"""Split multi-review users into a persona_source / ground_truth pair.

Input : data/filtered_reviews.json (already age/length-filtered; not re-filtered here)
Output: data/persona_source.json and data/ground_truth.json, JSON-lines,
        linked by 'user_id' (exactly one record per qualifying user in each file).

For every user with at least 2 reviews, two reviews are drawn at random; one is
assigned to persona_source and one to ground_truth. Users with more than two
reviews contribute only the two drawn; the rest are discarded.

Run: python3 src/split_persona_holdout.py
"""

import json
import random
from collections import Counter, defaultdict

SRC_PATH = "data/filtered_reviews.json"
PERSONA_PATH = "data/persona_source.json"
TRUTH_PATH = "data/ground_truth.json"

MIN_REVIEWS = 2
SEED = 42

AGE_BRACKETS = ["10s", "20s", "30s", "40s", "50s", "60+"]
RATING_BUCKETS = ["2", "4", "6", "8", "10"]


def age_bracket(age):
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


def to_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def cell(rec):
    """(age bracket, rating bucket) for a record, or None if either is unusable."""
    age = to_int(rec.get("age"))
    rating = str(rec.get("rating", "")).strip()
    if age is None or rating not in RATING_BUCKETS:
        return None
    return (age_bracket(age), rating)


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    rng = random.Random(SEED)

    by_user = defaultdict(list)
    total = 0
    with open(SRC_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                total += 1
                by_user[rec["user_id"]].append(rec)

    qualifying = {u: revs for u, revs in by_user.items() if len(revs) >= MIN_REVIEWS}

    review_count_hist = Counter(len(revs) for revs in qualifying.values())
    both_in_cell = 0
    same_cell = 0
    same_age_bracket = 0
    same_rating = 0
    cell_pairs = Counter()

    with open(PERSONA_PATH, "w", encoding="utf-8") as pf, \
         open(TRUTH_PATH, "w", encoding="utf-8") as tf:
        for user_id in sorted(qualifying):
            reviews = qualifying[user_id]
            persona, truth = rng.sample(reviews, 2)

            pf.write(json.dumps(persona, ensure_ascii=False) + "\n")
            tf.write(json.dumps(truth, ensure_ascii=False) + "\n")

            c_persona, c_truth = cell(persona), cell(truth)
            if c_persona is not None and c_truth is not None:
                both_in_cell += 1
                if c_persona == c_truth:
                    same_cell += 1
                    cell_pairs[c_persona] += 1
                if c_persona[0] == c_truth[0]:
                    same_age_bracket += 1
                if c_persona[1] == c_truth[1]:
                    same_rating += 1

    n = len(qualifying)

    section("QUALIFYING USERS")
    print(f"  records read from {SRC_PATH} : {total:,}")
    print(f"  distinct users                          : {len(by_user):,}")
    print(f"  users with >= {MIN_REVIEWS} reviews (qualifying)   : {n:,}")
    print(f"  reviews used ({n:,} users x 2)             : {n * 2:,}")
    print(f"  reviews discarded from 3+ users         : {sum(len(r) for r in qualifying.values()) - n * 2:,}")
    print("\n  qualifying users by review count:")
    for k in sorted(review_count_hist):
        label = f"{k}" if k <= 10 else None
        if label:
            print(f"    {k:>3} reviews : {review_count_hist[k]:>7,} users")
    tail = sum(v for k, v in review_count_hist.items() if k > 10)
    print(f"    11+       : {tail:>7,} users")

    section("AUDIENCE CELLS (age bracket x rating bucket)")
    print(f"  both reviews land in a valid cell     : {both_in_cell:,}  ({100.0 * both_in_cell / n:.2f}% of qualifying)")
    print(f"  both land in the SAME cell            : {same_cell:,}  ({100.0 * same_cell / n:.2f}%)")
    print(f"  same age bracket (rating may differ)  : {same_age_bracket:,}  ({100.0 * same_age_bracket / n:.2f}%)")
    print(f"  same rating bucket (age may differ)   : {same_rating:,}  ({100.0 * same_rating / n:.2f}%)")

    print("\n  users whose BOTH reviews sit in the same cell, by cell:")
    header = "  " + " " * 6 + "".join(f"{r:>9}" for r in RATING_BUCKETS) + f"{'total':>9}"
    print(header)
    for ab in AGE_BRACKETS:
        row = [cell_pairs.get((ab, r), 0) for r in RATING_BUCKETS]
        print(f"  {ab:<6}" + "".join(f"{v:>9,}" for v in row) + f"{sum(row):>9,}")
    col_totals = [sum(cell_pairs.get((ab, r), 0) for ab in AGE_BRACKETS) for r in RATING_BUCKETS]
    print(f"  {'total':<6}" + "".join(f"{v:>9,}" for v in col_totals) + f"{sum(col_totals):>9,}")

    section("OUTPUT")
    print(f"  {PERSONA_PATH} : {n:,} records (JSON-lines)")
    print(f"  {TRUTH_PATH} : {n:,} records (JSON-lines)")
    print(f"  linked by user_id; random seed = {SEED}")


if __name__ == "__main__":
    main()
