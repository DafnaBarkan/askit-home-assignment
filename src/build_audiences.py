"""Build the four audience groups A/B/C/D from the persona pool.

Input : data/persona_source_v2.json (22,835 users, exactly one review each)
Output: data/audiences.json - {"A": [...], "B": [...], "C": [...], "D": [...]}
        where each list holds the full review records assigned to that audience.

Definitions:
  A - age >= 40,      rating >= 8
  B - age 18-29,      rating >= 8
  C - all ages,       rating in {2, 4}
  D - age >= 18,      rating >= 8, age-bracket-matched to C

Build order is C, D, A, B. A user occupies at most one audience: every user
placed in an earlier group is struck from all later candidate pools. Because
each user contributes exactly one record with one age and one rating, C cannot
collide with A/B/D (rating 2/4 vs >= 8) and A cannot collide with B (age 40+ vs
18-29); the only real conflict is D, whose pool is a superset of A's and B's,
and it is resolved by drawing D first.

Sizing: C is taken whole. D matches C's bracket counts exactly. A and B are both
cut to min(|A pool|, |B pool|) after D is removed.

Run: python3 src/build_audiences.py
"""

import json
import random
from collections import Counter, defaultdict

SRC_PATH = "data/persona_source_v2.json"
OUT_PATH = "data/audiences.json"

SEED = 42
MIN_AGE_D = 18          # under-18 users are not eligible for D
LOW_RATINGS = {2, 4}
HIGH_RATING_MIN = 8

BRACKETS = ["10s", "20s", "30s", "40s", "50s", "60+"]


def bracket(age):
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


def main():
    rng = random.Random(SEED)

    records = {}
    with open(SRC_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                rec["_age"] = int(rec["age"])
                rec["_rating"] = int(rec["rating"])
                records[rec["user_id"]] = rec

    used = set()

    def take(user_ids):
        used.update(user_ids)
        return [records[u] for u in user_ids]

    # --- C: every low-rating user -------------------------------------------
    c_ids = sorted(u for u, r in records.items() if r["_rating"] in LOW_RATINGS)
    C = take(c_ids)
    c_brackets = Counter(bracket(r["_age"]) for r in C)

    # --- D: age-bracket-matched to C, 18+, high rating ----------------------
    d_candidates = defaultdict(list)
    for u, r in records.items():
        if u not in used and r["_rating"] >= HIGH_RATING_MIN and r["_age"] >= MIN_AGE_D:
            d_candidates[bracket(r["_age"])].append(u)

    d_ids = []
    shortfall = {}
    for b in BRACKETS:
        want = c_brackets.get(b, 0)
        pool = sorted(d_candidates[b])
        if want == 0:
            continue
        if len(pool) < want:
            shortfall[b] = want - len(pool)
            d_ids.extend(pool)
        else:
            d_ids.extend(rng.sample(pool, want))
    D = take(sorted(d_ids))

    # --- A and B: equal size, drawn from what D left behind ------------------
    a_pool = sorted(u for u, r in records.items()
                    if u not in used and r["_rating"] >= HIGH_RATING_MIN and r["_age"] >= 40)
    b_pool = sorted(u for u, r in records.items()
                    if u not in used and r["_rating"] >= HIGH_RATING_MIN and 18 <= r["_age"] <= 29)
    size = min(len(a_pool), len(b_pool))

    a_ids = sorted(rng.sample(a_pool, size)) if size < len(a_pool) else a_pool
    A = take(a_ids)
    b_ids = sorted(rng.sample(b_pool, size)) if size < len(b_pool) else b_pool
    B = take(b_ids)

    groups = {"A": A, "B": B, "C": C, "D": D}

    # --- write ---------------------------------------------------------------
    clean = {g: [{k: v for k, v in r.items() if not k.startswith("_")} for r in recs]
             for g, recs in groups.items()}
    with open(OUT_PATH, "w", encoding="utf-8") as out:
        json.dump(clean, out, ensure_ascii=False, indent=1)

    # --- report --------------------------------------------------------------
    section("AUDIENCE SIZES")
    print(f"  pool: {SRC_PATH} - {len(records):,} users, one review each\n")
    print(f"  A (age >= 40, rating >= 8)      : {len(A):>6,}   candidate pool {len(a_pool):,}")
    print(f"  B (age 18-29, rating >= 8)      : {len(B):>6,}   candidate pool {len(b_pool):,}")
    print(f"  C (all ages, rating in 2/4)     : {len(C):>6,}   taken whole")
    print(f"  D (18+, rating >= 8, C-matched) : {len(D):>6,}")
    print(f"\n  total assigned users            : {len(used):,}")
    print(f"  overlap between any two groups  : "
          f"{sum(len(groups[x]) for x in groups) - len(used)} (0 = disjoint)")
    if shortfall:
        print(f"  D bracket shortfalls            : {shortfall}")
    else:
        print("  D bracket shortfalls            : none - matched C exactly")

    section("PERSONAS PER AGE BRACKET, PER AUDIENCE")
    counts = {g: Counter(bracket(r["_age"]) for r in recs) for g, recs in groups.items()}
    print(f"  {'bracket':<9}" + "".join(f"{g:>9}" for g in "ABCD"))
    for b in BRACKETS:
        print(f"  {b:<9}" + "".join(f"{counts[g].get(b, 0):>9,}" for g in "ABCD"))
    print(f"  {'total':<9}" + "".join(f"{len(groups[g]):>9,}" for g in "ABCD"))

    print("\n  C vs D bracket match:")
    for b in BRACKETS:
        if counts["C"].get(b, 0) or counts["D"].get(b, 0):
            ok = "match" if counts["C"].get(b, 0) == counts["D"].get(b, 0) else "MISMATCH"
            print(f"    {b:<5} C={counts['C'].get(b, 0):>4}  D={counts['D'].get(b, 0):>4}  {ok}")

    section("RATING BREAKDOWN PER AUDIENCE")
    print(f"  {'rating':<9}" + "".join(f"{g:>9}" for g in "ABCD"))
    rcounts = {g: Counter(r["_rating"] for r in recs) for g, recs in groups.items()}
    for rating in [2, 4, 8, 10]:
        print(f"  {rating:<9}" + "".join(f"{rcounts[g].get(rating, 0):>9,}" for g in "ABCD"))

    section("OUTPUT")
    print(f"  wrote {OUT_PATH}")
    print(f"  random.Random(seed={SEED}); user_ids sorted before every sample")


if __name__ == "__main__":
    main()
