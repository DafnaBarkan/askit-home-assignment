"""The three linguistic axes committed in REPORT.md.

Each text is scored as a 3D vector:

  positivity  - VADER compound score, -1 to 1, on the raw untouched text.
  self_other  - proportion of first-person-singular pronouns among all
                first/second/third-person pronoun tokens. Closed word list,
                counted over spaCy tokens so contractions ("I'm", "I've")
                split correctly. `it/its/itself` stay in the denominator:
                they count as other-reference.
  tense       - past / (past + future) tensed verbs, bounded 0-1. A raw
                past:future ratio is undefined for the many reviews with no
                future verbs at all; this form is monotonic in the same
                direction and defined whenever the text has one tensed verb.

Axes are NaN when their denominator is empty (no pronouns, no tensed verbs).
"""

import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

FIRST_SINGULAR = {"i", "me", "my", "mine", "myself"}
OTHER_PRONOUNS = {
    # first person plural
    "we", "us", "our", "ours", "ourselves",
    # second person
    "you", "your", "yours", "yourself", "yourselves",
    # third person singular
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "it", "its", "itself",
    # third person plural
    "they", "them", "their", "theirs", "themselves",
}
ALL_PRONOUNS = FIRST_SINGULAR | OTHER_PRONOUNS

FUTURE_MODALS = {"will", "shall"}
PERFECT_PASSIVE_AUX = {"have", "be"}


def load_nlp():
    """spaCy en_core_web_sm; NER is not needed and is the slowest component."""
    return spacy.load("en_core_web_sm", exclude=["ner"])


def positivity(analyzer, text):
    return analyzer.polarity_scores(text)["compound"]


def self_other(doc):
    """1sg pronouns / all pronouns. NaN when the text has no pronouns."""
    first = 0
    total = 0
    for token in doc:
        word = token.lower_
        if word in ALL_PRONOUNS:
            total += 1
            if word in FIRST_SINGULAR:
                first += 1
    if total == 0:
        return float("nan"), 0, 0
    return first / total, first, total


def count_tenses(doc):
    """(past, future) tensed-verb counts.

    Past   - VBD, plus VBN heading a perfect or passive construction
             (identified by a have/be auxiliary child).
    Future - modal will/shall, 'going to' + base verb, 'about to' + base verb.
    """
    past = 0
    future = 0

    for token in doc:
        tag = token.tag_

        if tag == "VBD":
            past += 1
        elif tag == "VBN":
            if any(child.dep_ in ("aux", "auxpass") and child.lemma_ in PERFECT_PASSIVE_AUX
                   for child in token.children):
                past += 1
        elif tag == "MD" and token.lemma_ in FUTURE_MODALS:
            future += 1
        elif tag == "VBG" and token.lemma_ == "go":
            # "going to wear" - a base-verb complement introduced by "to"
            if any(child.tag_ == "VB" and any(g.lower_ == "to" for g in child.children)
                   for child in token.children):
                future += 1
        elif token.lower_ == "about":
            nxt = token.nbor(1) if token.i + 1 < len(token.doc) else None
            after = token.nbor(2) if token.i + 2 < len(token.doc) else None
            if nxt is not None and after is not None and nxt.lower_ == "to" and after.tag_ == "VB":
                future += 1

    return past, future


def tense_score(doc):
    """past / (past + future). NaN when the text has no tensed verbs."""
    past, future = count_tenses(doc)
    if past + future == 0:
        return float("nan"), past, future
    return past / (past + future), past, future


def score_texts(texts, batch_size=200):
    """Yield one dict of axis scores (plus raw counts) per input text."""
    nlp = load_nlp()
    analyzer = SentimentIntensityAnalyzer()

    for text, doc in zip(texts, nlp.pipe(texts, batch_size=batch_size)):
        so, first, pronouns = self_other(doc)
        tense, past, future = tense_score(doc)
        yield {
            "positivity": positivity(analyzer, text),
            "self_other": so,
            "tense": tense,
            "n_first_singular": first,
            "n_pronouns": pronouns,
            "n_past": past,
            "n_future": future,
            "n_tokens": len(doc),
        }
