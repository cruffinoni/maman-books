import math
import re
from dataclasses import dataclass

FORMAT_KEYWORDS: frozenset[str] = frozenset({"epub", "pdf", "mobi", "azw3", "fb2"})

LANGUAGE_KEYWORDS: dict[str, str] = {
    "english": "en", "anglais": "en",
    "french": "fr", "francais": "fr",
    "spanish": "es", "espanol": "es",
    "german": "de", "deutsch": "de",
    "italian": "it", "italiano": "it",
    "portuguese": "pt",
}


STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "de", "le", "la", "les", "du", "des",
    "and", "et", "by", "par", "in", "of", "for",
})

DEGRADED_KEYWORDS: frozenset[str] = frozenset({
    "omnibus", "collection", "anthology", "summary", "excerpt",
    "abridged", "complete", "complet", "integral", "intégral",
    "boxset", "box", "bundle", "trilogy", "saga",
})

VOLUME_RE = re.compile(r'(?:\b(?:vol\.?|volume|book|tome|t\.?)|#)\s*(\d+)\b', re.IGNORECASE)

FORMAT_RANK: dict[str, int] = {"epub": 3, "mobi": 2, "azw3": 2, "pdf": 1}
SOURCE_RANK: dict[str, int] = {"anna": 2, "prowlarr": 1}

_TOKEN_SPLIT_RE = re.compile(r'[\s\-_/]+')

_BM25_K1: float = 1.5
_BM25_B: float = 0.75
_DEGRADED_PENALTY: float = 0.20
_VOLUME_BONUS: float = 0.15
_VOLUME_PENALTY: float = 0.15
_LANGUAGE_BONUS: float = 0.10
_LANGUAGE_PENALTY: float = 0.05


@dataclass(frozen=True)
class ParsedQuery:
    raw: str
    content_tokens: frozenset[str]
    format_hint: str | None
    language_hint: str | None
    volume_hint: int | None


def parse_query(raw: str) -> ParsedQuery:
    lowered = raw.lower()
    tokens = _TOKEN_SPLIT_RE.split(lowered)

    format_hint: str | None = None
    for t in tokens:
        if t in FORMAT_KEYWORDS:
            format_hint = t
            break

    language_hint: str | None = None
    for t in tokens:
        if t in LANGUAGE_KEYWORDS:
            language_hint = LANGUAGE_KEYWORDS[t]
            break

    volume_hint: int | None = None
    m = VOLUME_RE.search(raw)
    if m:
        volume_hint = int(m.group(1))

    volume_tokens: set[str] = set()
    for vm in VOLUME_RE.finditer(lowered):
        volume_tokens.update(_TOKEN_SPLIT_RE.split(vm.group(0).lower()))

    lang_tokens = {t for t in tokens if t in LANGUAGE_KEYWORDS}

    content_tokens: frozenset[str] = frozenset(
        t for t in tokens
        if t not in FORMAT_KEYWORDS
        and t not in lang_tokens
        and t not in volume_tokens
        and t not in STOP_WORDS
        and len(t) > 1
    )

    return ParsedQuery(
        raw=raw,
        content_tokens=content_tokens,
        format_hint=format_hint,
        language_hint=language_hint,
        volume_hint=volume_hint,
    )



def _apply_adjustments(results: list, pq: ParsedQuery, scores: list[float]) -> None:
    for i, result in enumerate(results):
        title_lower = result.title.lower()

        if pq.volume_hint is not None:
            vm = VOLUME_RE.search(title_lower)
            scores[i] += _VOLUME_BONUS if (vm and vm.group(1) == str(pq.volume_hint)) else -_VOLUME_PENALTY

        if pq.language_hint is not None:
            matched = any(k in title_lower for k, v in LANGUAGE_KEYWORDS.items() if v == pq.language_hint)
            scores[i] += _LANGUAGE_BONUS if matched else -_LANGUAGE_PENALTY

        if any(kw in title_lower for kw in DEGRADED_KEYWORDS):
            scores[i] -= _DEGRADED_PENALTY

        scores[i] = max(0.0, min(1.0, scores[i]))


def _bm25_scores(results: list, pq: ParsedQuery) -> list[float]:
    if not results:
        return []

    query_terms = list(pq.content_tokens)

    if not query_terms:
        scores = [0.5] * len(results)
        _apply_adjustments(results, pq, scores)
        return scores

    doc_tokens: list[list[str]] = [
        _TOKEN_SPLIT_RE.split(r.title.lower()) for r in results
    ]
    doc_lengths = [len(tokens) for tokens in doc_tokens]
    n_docs = len(results)
    avgdl = sum(doc_lengths) / n_docs

    df: dict[str, int] = {}
    for tokens in doc_tokens:
        token_set = set(tokens)
        for term in query_terms:
            if term in token_set:
                df[term] = df.get(term, 0) + 1

    idf: dict[str, float] = {
        term: math.log((n_docs - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5) + 1)
        for term in query_terms
    }

    raw_scores: list[float] = []
    for idx, tokens in enumerate(doc_tokens):
        dl = doc_lengths[idx]
        tf_map: dict[str, int] = {}
        for t in tokens:
            tf_map[t] = tf_map.get(t, 0) + 1
        bm25 = sum(
            idf[term] * (tf_map.get(term, 0) * (_BM25_K1 + 1))
            / (tf_map.get(term, 0) + _BM25_K1 * (1 - _BM25_B + _BM25_B * dl / avgdl))
            for term in query_terms
        )
        raw_scores.append(bm25)

    max_score = max(raw_scores)
    normalised = [s / max_score for s in raw_scores] if max_score > 0.0 else [0.5] * n_docs

    _apply_adjustments(results, pq, normalised)
    return normalised


def _format_score(result, pq: ParsedQuery) -> int:
    if pq.format_hint is not None:
        return 3 if result.ext == pq.format_hint else 0
    return FORMAT_RANK.get(result.ext, 0)


def _reliability_score(result) -> int:
    if result.is_torrent:
        return 1 if result.seeders else 0
    return min(3, SOURCE_RANK.get(result.source, 0) + (1 if result.md5 else 0))


def rank(results: list, pq: ParsedQuery) -> list[tuple[float, int, int]]:
    """Return a (content, format, reliability) score tuple per result, in input order."""
    content_scores = _bm25_scores(results, pq)
    return [
        (content_scores[i], _format_score(results[i], pq), _reliability_score(results[i]))
        for i in range(len(results))
    ]
