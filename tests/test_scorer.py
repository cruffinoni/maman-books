import unittest

from models import SearchResult
from services.scorer import (
    ParsedQuery,
    parse_query,
    rank,
    _format_score,
    _reliability_score,
)


def _result(
    title="Dune",
    author="Frank Herbert",
    ext="epub",
    source="anna",
    is_torrent=False,
    md5="abc123",
    seeders=0,
    size_bytes=1_000_000,
) -> SearchResult:
    return SearchResult(
        source=source,
        title=title,
        author=author,
        ext=ext,
        size_bytes=size_bytes,
        is_torrent=is_torrent,
        download_url="",
        md5=md5,
        guid="",
        indexer_id=0,
        magnet_url="",
        seeders=seeders,
    )


class TestParseQuery(unittest.TestCase):
    def test_plain_title(self):
        pq = parse_query("Dune Frank Herbert")
        self.assertEqual(pq.raw, "Dune Frank Herbert")
        self.assertIn("dune", pq.content_tokens)
        self.assertIn("frank", pq.content_tokens)
        self.assertIn("herbert", pq.content_tokens)
        self.assertIsNone(pq.format_hint)
        self.assertIsNone(pq.language_hint)
        self.assertIsNone(pq.volume_hint)

    def test_format_hint_extracted(self):
        pq = parse_query("Dune epub")
        self.assertEqual(pq.format_hint, "epub")
        self.assertNotIn("epub", pq.content_tokens)

    def test_language_hint_english(self):
        pq = parse_query("Dune English")
        self.assertEqual(pq.language_hint, "en")
        self.assertNotIn("english", pq.content_tokens)

    def test_language_hint_french(self):
        pq = parse_query("Dune francais")
        self.assertEqual(pq.language_hint, "fr")

    def test_volume_hint_tome(self):
        pq = parse_query("Dune tome 2")
        self.assertEqual(pq.volume_hint, 2)
        self.assertNotIn("tome", pq.content_tokens)
        self.assertNotIn("2", pq.content_tokens)

    def test_volume_hint_vol(self):
        pq = parse_query("Wheel of Time vol. 3")
        self.assertEqual(pq.volume_hint, 3)

    def test_volume_hint_hash(self):
        pq = parse_query("Discworld #5")
        self.assertEqual(pq.volume_hint, 5)

    def test_stop_words_excluded(self):
        pq = parse_query("The Lord of the Rings")
        self.assertNotIn("the", pq.content_tokens)
        self.assertNotIn("of", pq.content_tokens)
        self.assertIn("lord", pq.content_tokens)
        self.assertIn("rings", pq.content_tokens)

    def test_single_char_tokens_excluded(self):
        pq = parse_query("T. S. Eliot")
        self.assertNotIn("t", pq.content_tokens)
        self.assertNotIn("s", pq.content_tokens)
        self.assertIn("eliot", pq.content_tokens)

    def test_all_hints_combined(self):
        pq = parse_query("Dune Messiah Frank Herbert epub English tome 2")
        self.assertEqual(pq.format_hint, "epub")
        self.assertEqual(pq.language_hint, "en")
        self.assertEqual(pq.volume_hint, 2)
        self.assertIn("dune", pq.content_tokens)
        self.assertIn("messiah", pq.content_tokens)
        self.assertIn("frank", pq.content_tokens)
        self.assertIn("herbert", pq.content_tokens)
        self.assertNotIn("epub", pq.content_tokens)
        self.assertNotIn("english", pq.content_tokens)

    def test_empty_query(self):
        pq = parse_query("")
        self.assertEqual(pq.content_tokens, frozenset())
        self.assertIsNone(pq.format_hint)
        self.assertIsNone(pq.language_hint)
        self.assertIsNone(pq.volume_hint)



class TestFormatScore(unittest.TestCase):
    def test_exact_format_hint_match(self):
        pq = parse_query("Dune epub")
        self.assertEqual(_format_score(_result(ext="epub"), pq), 3)

    def test_format_hint_mismatch(self):
        pq = parse_query("Dune epub")
        self.assertEqual(_format_score(_result(ext="pdf"), pq), 0)

    def test_no_format_hint_uses_rank(self):
        pq = parse_query("Dune")
        self.assertEqual(_format_score(_result(ext="epub"), pq), 3)
        self.assertEqual(_format_score(_result(ext="mobi"), pq), 2)
        self.assertEqual(_format_score(_result(ext="azw3"), pq), 2)
        self.assertEqual(_format_score(_result(ext="pdf"), pq), 1)
        self.assertEqual(_format_score(_result(ext="txt"), pq), 0)

    def test_unknown_ext_scores_zero(self):
        pq = parse_query("Dune")
        self.assertEqual(_format_score(_result(ext="cbz"), pq), 0)


class TestReliabilityScore(unittest.TestCase):
    def test_anna_with_md5(self):
        r = _result(source="anna", is_torrent=False, md5="abc")
        self.assertEqual(_reliability_score(r), 3)

    def test_anna_without_md5(self):
        r = _result(source="anna", is_torrent=False, md5="")
        self.assertEqual(_reliability_score(r), 2)

    def test_prowlarr_direct_with_md5(self):
        r = _result(source="prowlarr", is_torrent=False, md5="abc")
        self.assertEqual(_reliability_score(r), 2)

    def test_prowlarr_direct_without_md5(self):
        r = _result(source="prowlarr", is_torrent=False, md5="")
        self.assertEqual(_reliability_score(r), 1)

    def test_torrent_with_seeders(self):
        r = _result(is_torrent=True, seeders=10)
        self.assertEqual(_reliability_score(r), 1)

    def test_torrent_no_seeders(self):
        r = _result(is_torrent=True, seeders=0)
        self.assertEqual(_reliability_score(r), 0)

    def test_unknown_source_direct(self):
        r = _result(source="unknown", is_torrent=False, md5="abc")
        self.assertEqual(_reliability_score(r), 1)


class TestBm25Rank(unittest.TestCase):
    def test_french_forensics_exact_match_ranks_first(self):
        pq = parse_query("Philippe Boxho Entretien avec un cadavre")
        exact_epub = _result(title="Entretien avec un cadavre", author="Philippe Boxho", ext="epub", source="anna", md5="abc")
        exact_pdf = _result(title="Entretien avec un cadavre", author="Philippe Boxho", ext="pdf", source="anna", md5="abc")
        vampire = _result(title="Entretien avec un vampire", author="Anne Rice", ext="epub", source="anna", md5="def")
        boxho_corps = _result(title="Le Corps humain - Philippe Boxho", author="Philippe Boxho", ext="epub", source="anna", md5="ghi")
        harry = _result(title="Harry Potter", author="J.K. Rowling", ext="epub", source="anna", md5="jkl")

        corpus = [exact_epub, exact_pdf, vampire, boxho_corps, harry]
        scores = rank(corpus, pq)

        self.assertGreater(scores[0][0], scores[2][0], "exact match must beat vampire")
        self.assertGreater(scores[0][1], scores[1][1], "epub must beat pdf for same title")
        self.assertLess(scores[4][0], scores[0][0], "Harry Potter must score lowest on content")

    def test_dune_volume_correct_volume_ranks_first(self):
        pq = parse_query("Dune tome 2 Frank Herbert")
        correct_vol = _result(title="Dune tome 2 - Le Messie de Dune", ext="epub", source="anna", md5="a")
        wrong_vol = _result(title="Dune tome 1", ext="epub", source="anna", md5="b")
        integrale = _result(title="Dune - Intégrale", ext="epub", source="anna", md5="c")
        right_content_pdf = _result(title="Dune Messiah Frank Herbert", ext="pdf", source="anna", md5="d")
        foundation = _result(title="Foundation Isaac Asimov", ext="epub", source="anna", md5="e")

        corpus = [correct_vol, wrong_vol, integrale, right_content_pdf, foundation]
        scores = rank(corpus, pq)

        self.assertGreater(scores[0][0], scores[1][0], "correct volume must beat wrong volume")
        self.assertLess(scores[2][0], scores[0][0], "integrale must be penalised below exact match")
        self.assertGreater(scores[0][0], scores[1][0], "wrong volume must be penalised")
        self.assertLess(scores[4][0], scores[0][0], "Foundation must rank last on content")

    def test_educated_epub_format_hint(self):
        pq = parse_query("Educated Tara Westover epub")
        epub_anna = _result(title="Educated", author="Tara Westover", ext="epub", source="anna", md5="a")
        pdf_anna = _result(title="Educated", author="Tara Westover", ext="pdf", source="anna", md5="b")
        epub_prowlarr = _result(title="Educated", author="Tara Westover", ext="epub", source="prowlarr", md5="")
        wild = _result(title="Wild", author="Cheryl Strayed", ext="epub", source="anna", md5="c")

        corpus = [epub_anna, pdf_anna, epub_prowlarr, wild]
        scores = rank(corpus, pq)

        self.assertGreater(scores[0][1], scores[1][1], "epub must rank above pdf on format")
        self.assertLess(scores[3][0], scores[0][0], "Wild must rank last on content")

    def test_sapiens_tiebreak_epub_beats_pdf(self):
        pq = parse_query("Sapiens Yuval Noah Harari")
        epub_anna_md5 = _result(title="Sapiens", author="Yuval Noah Harari", ext="epub", source="anna", md5="a")
        pdf_anna_md5 = _result(title="Sapiens", author="Yuval Noah Harari", ext="pdf", source="anna", md5="b")
        epub_prowlarr = _result(title="Sapiens", author="Yuval Noah Harari", ext="epub", source="prowlarr", md5="")
        pdf_prowlarr = _result(title="Sapiens", author="Yuval Noah Harari", ext="pdf", source="prowlarr", md5="")

        corpus = [epub_anna_md5, pdf_anna_md5, epub_prowlarr, pdf_prowlarr]
        scores = rank(corpus, pq)

        self.assertEqual(scores[0][0], scores[1][0], "content scores must be equal for identical titles")
        self.assertEqual(scores[0][0], scores[2][0], "content scores must be equal for identical titles")
        self.assertGreater(scores[0][1], scores[1][1], "epub beats pdf on format tier")
        self.assertGreater(scores[0][2], scores[2][2], "anna+md5 beats prowlarr+no-md5 on reliability")

    def test_empty_query_returns_neutral_content_scores(self):
        pq = parse_query("")
        corpus = [_result(title="Dune"), _result(title="Foundation")]
        scores = rank(corpus, pq)
        self.assertEqual(scores[0][0], 0.5)
        self.assertEqual(scores[1][0], 0.5)

    def test_empty_results_returns_empty(self):
        pq = parse_query("Dune")
        self.assertEqual(rank([], pq), [])

    def test_scores_clamped_to_0_1(self):
        pq = parse_query("Dune Frank Herbert tome 2 english")
        corpus = [
            _result(title="Dune tome 2 by Frank Herbert English Edition"),
            _result(title="Random Unrelated Book Title"),
            _result(title="Dune Omnibus Complete Collection"),
        ]
        scores = rank(corpus, pq)
        for content, fmt, rel in scores:
            self.assertGreaterEqual(content, 0.0)
            self.assertLessEqual(content, 1.0)


class TestRankOrdering(unittest.TestCase):
    def test_content_dominates_format(self):
        pq = parse_query("Dune Frank Herbert")
        right_pdf = _result(title="Dune by Frank Herbert", ext="pdf")
        wrong_epub = _result(title="Harry Potter", ext="epub")
        corpus = [right_pdf, wrong_epub]
        scores = rank(corpus, pq)
        self.assertGreater(scores[0], scores[1])

    def test_omnibus_sinks_below_exact_match(self):
        pq = parse_query("Dune Frank Herbert")
        exact = _result(title="Dune by Frank Herbert")
        omnibus = _result(title="Dune Omnibus Complete Collection Frank Herbert")
        corpus = [exact, omnibus]
        scores = rank(corpus, pq)
        self.assertGreater(scores[0], scores[1])

    def test_format_tiebreaks_when_content_equal(self):
        pq = parse_query("Dune")
        epub_r = _result(title="Dune", ext="epub", source="prowlarr", md5="")
        pdf_r = _result(title="Dune", ext="pdf", source="prowlarr", md5="")
        corpus = [epub_r, pdf_r]
        scores = rank(corpus, pq)
        self.assertEqual(scores[0][0], scores[1][0], "content scores must be equal")
        self.assertGreater(scores[0][1], scores[1][1], "epub beats pdf on format")

    def test_reliability_tiebreaks_when_content_and_format_equal(self):
        pq = parse_query("Dune")
        anna_r = _result(title="Dune", ext="epub", source="anna", md5="abc", is_torrent=False)
        prowlarr_r = _result(title="Dune", ext="epub", source="prowlarr", md5="", is_torrent=False)
        corpus = [anna_r, prowlarr_r]
        scores = rank(corpus, pq)
        self.assertEqual(scores[0][0], scores[1][0], "content scores must be equal")
        self.assertEqual(scores[0][1], scores[1][1], "format scores must be equal")
        self.assertGreater(scores[0][2], scores[1][2], "anna+md5 beats prowlarr+no-md5 on reliability")

    def test_sorted_list_puts_best_first(self):
        pq = parse_query("Educated Tara Westover epub")
        corpus = [
            _result(title="Wild", author="Cheryl Strayed", ext="epub"),
            _result(title="Educated", author="Tara Westover", ext="pdf"),
            _result(title="Educated", author="Tara Westover", ext="epub", source="anna", md5="abc"),
        ]
        scores = rank(corpus, pq)
        ranked = sorted(zip(scores, corpus), key=lambda x: x[0], reverse=True)
        best = ranked[0][1]
        worst = ranked[-1][1]
        self.assertEqual(best.title, "Educated")
        self.assertEqual(best.ext, "epub")
        self.assertEqual(worst.title, "Wild")

    def test_empty_list_returns_empty(self):
        pq = parse_query("Dune")
        self.assertEqual(rank([], pq), [])


if __name__ == "__main__":
    unittest.main()
