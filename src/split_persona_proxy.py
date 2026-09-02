"""Pair each multi-review user's reviews into persona_source / proxy_pair.

Input : data/filtered_reviews.json (already age/length-filtered; not re-filtered here)
Output: data/persona_source_v2.json and data/proxy_pair.json, JSON-lines,
        linked by 'user_id'. Nothing existing is overwritten.

Pairing rule, applied per user with >= 2 reviews:
  Rule 1 (negative pair) : any two reviews whose ratings are both in {2, 4}
                           (2&2, 2&4 and 4&4 all qualify).
  Rule 2 (exact positive) : only if rule 1 finds nothing - any two reviews
                           sharing the EXACT same rating >= 6 (6&6, 8&8, 10&10;
                           no mixing).
  Otherwise the user is excluded; no fallback pair is forced.

When several candidate pairs exist, candidates are sorted by the two reviews'
original line index in the input file and one is drawn with random.Random(42).
The same generator then decides which of the two becomes persona_source.

Run: python3 src/split_persona_proxy.py
"""

import json
import random
from collections import Counter, defaultdict
from itertools import combinations

SRC_PATH = "data/filtered_reviews.json"
PERSONA_PATH = "data/persona_source_v2.json"
PROXY_PATH = "data/proxy_pair.json"

MIN_REVIEWS = 2
SEED = 42

NEGATIVE_RATINGS = {2, 4}
POSITIVE_RATINGS = [6, 8, 10]
AGE_BRACKETS = ["10s", "20s", "30s", "40s", "50s", "60+"]


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


def candidate_pairs(reviews):
    """(rule, [(idx_a, idx_b), ...]) for a user's reviews, or (None, []).

    `reviews` is a list of (line_index, record, rating) tuples.
    """
    negatives = [r for r in reviews if r[2] in NEGATIVE_RATINGS]
    if len(negatives) >= 2:
        pairs = [(a, b) for a, b in combinations(sorted(negatives, key=lambda r: r[0]), 2)]
        return 1, pairs

    pairs = []
    for rating in POSITIVE_RATINGS:
        same = sorted((r for r in reviews if r[2] == rating), key=lambda r: r[0])
        pairs.extend(combinations(same, 2))
    if pairs:
        pairs.sort(key=lambda p: (p[0][0], p[1][0]))
        return 2, pairs

    return None, []


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_matrix(counter, col_keys, title):
    print(f"\n  {title}")
    print("  " + " " * 6 + "".join(f"{str(c):>9}" for c in col_keys) + f"{'total':>9}")
    for ab in AGE_BRACKETS:
        row = [counter.get((ab, c), 0) for c in col_keys]
        print(f"  {ab:<6}" + "".join(f"{v:>9,}" for v in row) + f"{sum(row):>9,}")
    totals = [sum(counter.get((ab, c), 0) for ab in AGE_BRACKETS) for c in col_keys]
    print(f"  {'total':<6}" + "".join(f"{v:>9,}" for v in totals) + f"{sum(totals):>9,}")


def main():
    rng = random.Random(SEED)

    by_user = defaultdict(list)
    total = 0
    with open(SRC_PATH, encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if line:
                rec = json.loads(line)
                total += 1
                by_user[rec["user_id"]].append((idx, rec, to_int(rec.get("rating"))))

    qualifying = sorted(u for u, revs in by_user.items() if len(revs) >= MIN_REVIEWS)

    rule_counts = Counter()
    excluded_users = []
    negative_cells = Counter()   # (age bracket, "2&2"/"2&4"/"4&4") -> users
    positive_cells = Counter()   # (age bracket, 6/8/10) -> users

    with open(PERSONA_PATH, "w", encoding="utf-8") as pf, \
         open(PROXY_PATH, "w", encoding="utf-8") as xf:
        for user_id in qualifying:
            reviews = by_user[user_id]
            rule, pairs = candidate_pairs(reviews)

            if rule is None:
                rule_counts["excluded"] += 1
                excluded_users.append(user_id)
                continue

            chosen = rng.choice(pairs)
            persona, proxy = rng.sample(chosen, 2)

            pf.write(json.dumps(persona[1], ensure_ascii=False) + "\n")
            xf.write(json.dumps(proxy[1], ensure_ascii=False) + "\n")

            rule_counts[rule] += 1
            bracket = age_bracket(to_int(persona[1].get("age")))
            if rule == 1:
                combo = "&".join(str(r) for r in sorted((persona[2], proxy[2])))
                negative_cells[(bracket, combo)] += 1
            else:
                positive_cells[(bracket, persona[2])] += 1

    n_users = len(qualifying)

    section("PAIRING OUTCOME")
    print(f"  records read from {SRC_PATH} : {total:,}")
    print(f"  distinct users                          : {len(by_user):,}")
    print(f"  users with >= {MIN_REVIEWS} reviews (eligible)     : {n_users:,}")
    print()
    print(f"  rule 1 - negative pair (both in 2/4)    : {rule_counts[1]:>7,}  ({100.0 * rule_counts[1] / n_users:5.2f}%)")
    print(f"  rule 2 - exact positive pair (>= 6)     : {rule_counts[2]:>7,}  ({100.0 * rule_counts[2] / n_users:5.2f}%)")
    print(f"  excluded - neither rule applies         : {rule_counts['excluded']:>7,}  ({100.0 * rule_counts['excluded'] / n_users:5.2f}%)")
    print(f"  paired total                            : {rule_counts[1] + rule_counts[2]:>7,}")

    section("RULE 1 GROUP - AGE BRACKET x RATING COMBINATION")
    print_matrix(negative_cells, ["2&2", "2&4", "4&4"], "users per cell")

    section("RULE 2 GROUP - AGE BRACKET x RATING")
    print_matrix(positive_cells, POSITIVE_RATINGS, "users per cell")

    section("EXCLUDED GROUP")
    print(f"  excluded users (count only) : {rule_counts['excluded']:,}")
    print(f"  first 10 user_ids           : {', '.join(excluded_users[:10])}")

    section("OUTPUT / REPRODUCIBILITY")
    print(f"  {PERSONA_PATH} : {rule_counts[1] + rule_counts[2]:,} records (JSON-lines)")
    print(f"  {PROXY_PATH}      : {rule_counts[1] + rule_counts[2]:,} records (JSON-lines)")
    print("  linked by user_id, one record per paired user in each file")
    print(f"  random.Random(seed={SEED}); users iterated in sorted user_id order;")
    print("  candidate pairs sorted by original line index before sampling")


if __name__ == "__main__":
    main()
