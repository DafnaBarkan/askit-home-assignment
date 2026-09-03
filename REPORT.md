# AskIt Research Lab: Home Assignment Report

## Dataset and Seperation to Audiences
__RentTheRunway Clothing Fit Dataset:__ Public dataset of clothing reviews from a women's online fashion retailer (Misra, Wan & McAuley, RecSys 2018). Downloaded from cseweb.ucsd.edu/~jmcauley/datasets.html#clothing_fit.
* Pre-AI reviews (dataset published 2018, review dates pre-2018) — no LLM-generated contamination risk.
* Age is self-reported per reviewer, but reviews may describe gift purchases (e.g. an older customer reviewing an item bought for a daughter) — reflecting the recipient's style, not the reviewer's own. May cause a validity problem.


__Fields used for audience separation:__ age (self-reported, numeric), rating (2–10, even values only).
__Data field:__ review_text (free text).
__Filtering:__ age restricted to 10–80 (raw data included implausible values 0–117); minimum 10 words per review. 180,091 of 191,584 age-complete records retained.
__Proxy pairs (same-user validation):__ negative pair = both reviews rating ∈ {2,4}; positive pair = both reviews same exact rating ≥6. Of 31,339 users with 2+ qualifying reviews: 234 (0.75%) had a matched negative pair, 22,601 (72.12%) a matched positive pair, 8,504 (27.14%) neither
*negative-sentiment users rare. Positive audiences have sample paired data (22,601 users) for direct same-user proxy comparison.*

### Audiences - age and rating
Four audiences, each an age × rating cell:
- __A__ — older customers × high rating (≥8)
- __B__ - younger customers × high rating (≥8)
- __C__ — all ages x low rating (2/4)
- __D__ — all ages x high rating (≥8)

A vs. B isolates the age axis (rating held high). C vs. D isolates the sentiment axis (D resampled to match C's age composition/count, so age doesn't confound the comparison). A/C are dev; B/D are held-out.

## Part 1: Degrees of freedom and measurement

__Audiences language axes:__ short literature review identified three axes along which audiences differ that are easy to capture in a few hours:
- __Negative–Positive words__ — shifts positive with age (Pennebaker & Stone, 2003).Surface (lexical choice).
- __Self–Other reference__ — shifts toward more other-reference with age (Pennebaker & Stone, 2003). Structural (function words, provide the grammatical framework of a sentence, grammatical relationships).
- __Past–Future tense__ — shifts toward future tense with age (Pennebaker & Stone, 2003). Structural (grammatical).
*Text structure: organization of ideas within a text. Text surface: actual words/phrases/syntax used, doesn't necessarily change the sentence structure.*

### Ground truth
Context 1 (in-domain, "write a review of a clothing item you bought online recently"): __direct__ — persona built from one of a user's reviews, generated text compared against that same user's held-out paired review (2+ review users only).
Context 2 (out-of-domain, "tell a friend about your weekend"): __proxy__ — no matching real text per user exists. Generated text's axis scores compared against the audience-level distribution in real data.

### Axes measurements
__Positivity:__ VADER compound score (-1 to 1). Lexicon + context rules, not raw word-matching. Tool: `vaderSentiment` (Hutto & Gilbert, 2014).
__Self–Other reference:__ proportion of first-person-singular pronouns (I, me, my) among all first/second/third-person pronoun occurrences. Closed word-list count.
__Past–Future tense:__ ratio of past to future tense verbs via POS tagging. Tool: spaCy `en_core_web_sm` (Honnibal et al., 2020).

Each text scored as vector v = [positivity, self_other, tense_ratio].

__Expected values:__
- Age axis (A vs. B): A (older) expected higher positivity, lower self-other score (more other-reference), higher future-tense ratio than B (younger).
- Rating axis (C vs. D): D (high rating) expected higher positivity than C (low rating). No strong prior on self-other or tense direction for this axis, more exploratory.

### Within-audience and between-audience variation measurements
Within-audience heterogeneity: how much a persona inside an audience differs from the rest. I will use __betadisper__ — a multivariate test used to analyze the homogeneity of group dispersion. Measures average distance of each persona vector to its audience centroid.
Between-audience separation: how different audience averages are from each other. I will use __PERMANOVA (Permutational Multivariate Analysis of Variance)__ - a non-parametric test used to compare groups and determine if their multivariate centroids. Significance via permutation (999 permutations).
Both computed once on real reviews and once on generated personas (test).

*A perfect score on this metric (completely seperated audiences) would still miss whether the model was able to capture a persona type or subgroups within the audience.*


## Part 2: Fast research
Final audience members: A = 3,837 · B = 3,837 · C = 234 · D = 234 — 8,142 distinct users, zero shared.

### A and B
__cases with no scoreable pronouns/verbs:__ After dropping cases with no scoreable pronouns/verbs, n=3,332 (A) and n=3,513 (B).
__Axis descriptives:__
- Positivity — A mean: 0.820, B mean: 0.857. Predicted A higher. Result: inverted, B is higher.
- Self-other — A mean: 0.576, B mean: 0.596. Predicted: A lower (more other-reference). Result: matches.
- Tense — A mean: 0.962, B mean: 0.976. Predicted: A lower (more future-tense). Result: matches.

Between-audience (PERMANOVA): R² = 0.0035, F = 23.76, p = 0.001.
Within-audience (betadisper): A mean distance to centroid = 0.319, B mean distance to centroid = 0.271.


## Part 3: Slow research

*Disclaimer: This suggestion is a result of further thinking about the problem after the 5 hours limitation.*

We are trying here to model how different audiences, and personas within an audience, respond to a given question. Meaning, we are basically trying to capture their cognitive state (how they think and behave). Here we are trying to do so using text alone. However, adding physiological measurements within the same context (online review writing) could help the model represent these personas more accurately. This connects to a research field called ‘psychophysiology’, that studies how mental processes interact with physiological systems. This can be measured through methods like EEG (electroencephalography) or HRV (heart rate variability). 

# Another week plan
- I would do more research on semantic differences and lenguage generation. With more research and deeper understanding I could design metrics better suited to the data (the positivity axis moved in the opposite direction then expected).

- I would choose a different dataset that is better suited to the task. Rating and age distributions weren't evenly balanced across all audiences (negative-sentiment reviews are especially rare). With another week I would choose a dataset, or combine a few, that has more distinct audiences.

- And obviously, I would build and improve the actual model. I didn't reach part of the assignment, the generation of the function itself and testing it.
