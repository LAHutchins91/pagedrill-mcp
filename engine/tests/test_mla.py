"""Sourced MLA Handbook, 9th ed. mechanics. The style stays unselectable."""

import unittest

from pagedrill.mla import (
    EM_DASHES,
    HANDBOOK_5_124_ORDER,
    RANGE_EXAMPLES,
    UNSOURCED_SECTIONS,
    alphabetize_key,
    corporate_parenthetical,
    format_doi,
    format_issue_range,
    format_pages,
    format_url,
    format_works_cited_entry,
    in_text,
    join_seasons,
    local_newspaper,
    parenthetical,
    render_works_cited,
    shorten_range,
    shorten_year_range,
    supplied,
    timestamp_span,
    title_case,
    title_sort_parts,
    works_cited_authors,
)
from pagedrill.profiles import get_profile, is_selectable


def person(family, given="Ada"):
    return {"family": family, "given": given}


class MlaStaysHidden(unittest.TestCase):
    def test_profile_is_not_selectable(self):
        profile = get_profile("mla9-research-paper")
        self.assertFalse(profile["hidden"] is False)
        self.assertFalse(profile["checklist_verified"])
        self.assertFalse(is_selectable(profile))
        self.assertEqual(profile["unsourced_sections"], ["2.89-2.125"])
        self.assertEqual(UNSOURCED_SECTIONS, ("2.89–2.125",))
        self.assertFalse(str(profile["status"]).startswith("verified"))


class TitleCase(unittest.TestCase):
    def test_principal_words_and_small_words(self):
        self.assertEqual(title_case("reading, writing, and the screen"), "Reading, Writing, and the Screen")
        self.assertEqual(
            title_case("the impact of digital communication media"),
            "The Impact of Digital Communication Media",
        )

    def test_subtitle_article_is_capitalized(self):
        self.assertEqual(
            title_case("redefining reading: the impact of digital communication media"),
            "Redefining Reading: The Impact of Digital Communication Media",
        )

    def test_closed_prefix_and_ordinary_hyphen(self):
        self.assertEqual(title_case("anti-slavery movements in the atlantic"), "Anti-slavery Movements in the Atlantic")
        self.assertEqual(title_case("a well-known history of art"), "A Well-Known History of Art")

    def test_phrases(self):
        self.assertEqual(title_case("notes according to a friend"), "Notes according to a Friend")
        self.assertEqual(title_case("love as if it mattered"), "Love As If It Mattered")
        self.assertEqual(title_case("life as a house"), "Life as a House")

    def test_untitled_text_is_not_recased(self):
        self.assertEqual(title_case("roses are red", exact=True), "roses are red")


class NumberRanges(unittest.TestCase):
    def test_handbook_examples(self):
        for source, expected in RANGE_EXAMPLES.items():
            self.assertEqual(shorten_range(source), expected, source)

    def test_years_and_open_range(self):
        self.assertEqual(shorten_year_range("2000", "2003"), "2000–03")
        self.assertEqual(shorten_year_range("1945", "1989"), "1945–89")
        self.assertEqual(shorten_year_range("1898", "1901"), "1898–1901")
        self.assertEqual(shorten_year_range("800", "814"), "800–14")
        self.assertEqual(shorten_year_range("748", "742", start_era="BCE", end_era="BCE"), "748–742 BCE")
        self.assertEqual(shorten_year_range("143", "149", start_era="BCE", end_era="CE"), "143 BCE–149 CE")
        self.assertEqual(shorten_range("2000-"), "2000– ")

    def test_page_labels(self):
        self.assertEqual(format_pages("50-69"), "pp. 50–69")
        self.assertEqual(format_pages("11-14"), "pp. 11–14")
        self.assertEqual(format_pages("193-200"), "pp. 193–200")
        self.assertEqual(format_pages("12"), "p. 12")


class Authors(unittest.TestCase):
    def test_works_cited_two_and_three(self):
        self.assertEqual(
            works_cited_authors([person("Dorris", "Michael"), person("Erdrich", "Louise")]),
            "Dorris, Michael, and Louise Erdrich.",
        )
        self.assertEqual(
            works_cited_authors([person("Gilbert", "Sandra M."), person("Gubar", "Susan")], role="editors"),
            "Gilbert, Sandra M., and Susan Gubar, editors.",
        )
        self.assertEqual(works_cited_authors([person("Charon", "Rita")], et_al=True), "Charon, Rita, et al.")
        self.assertEqual(
            works_cited_authors([person("Adams", "Peter"), person("Lee", "Ann"), person("Ng", "Kim")]),
            "Adams, Peter, et al.",
        )

    def test_in_text_two_and_three(self):
        two, _ = in_text([person("Lemery"), person("Auerbach")], "4-5")
        many, _ = in_text([person("Nickerson"), person("Lee"), person("Ng")], "135")
        self.assertEqual(two, "(Lemery and Auerbach 4–5)")
        self.assertEqual(many, "(Nickerson et al. 135)")

    def test_corporate_drops_the_article_and_flags_an_unspecified_shortening(self):
        short, flag = corporate_parenthetical("the Modern Language Association")
        self.assertEqual(short, "Modern Language Association")
        self.assertIsNone(flag)
        longer, flagged = corporate_parenthetical("the Department of Labor")
        self.assertEqual(longer, "Department of Labor")
        self.assertIn("6.6", flagged)


class Alphabetizing(unittest.TestCase):
    def test_section_5_124_fixture(self):
        ordered = sorted(HANDBOOK_5_124_ORDER, key=alphabetize_key)
        self.assertEqual(ordered, list(HANDBOOK_5_124_ORDER))

    def test_repeat_authors_use_three_em_dashes(self):
        entries = [
            {"authors": [person("Morrison", "Toni")], "title": "Jazz", "type": "book", "publisher": "Knopf", "year": "1992"},
            {"authors": [person("Morrison", "Toni")], "title": "Beloved", "type": "book", "publisher": "Knopf", "year": "1987"},
            {"authors": [person("Morrison", "Toni")], "role": "translator", "title": "Song of Solomon", "type": "book", "publisher": "Knopf", "year": "1977"},
        ]
        lines, flags = render_works_cited(entries)
        self.assertEqual(flags, [])
        self.assertTrue(lines[0].startswith("Morrison, Toni. Beloved."))
        self.assertTrue(lines[1].startswith(f"{EM_DASHES}. Jazz."))
        self.assertTrue(lines[2].startswith(f"{EM_DASHES}, translator. Song of Solomon."))

    def test_coauthors_sort_by_the_second_surname_then_share_dashes(self):
        entries = [
            {"authors": [person("Scholes", "Robert"), person("Rabkin", "Eric")], "title": "Science Fiction", "type": "book", "publisher": "Oxford UP", "year": "1977"},
            {"authors": [person("Scholes", "Robert"), person("Kellogg", "Robert")], "title": "The Nature of Narrative", "type": "book", "publisher": "Oxford UP", "year": "1966"},
            {"authors": [person("Scholes", "Robert"), person("Kellogg", "Robert")], "title": "Another Book", "type": "book", "publisher": "Oxford UP", "year": "1970"},
        ]
        lines, flags = render_works_cited(entries)
        self.assertEqual(flags, [])
        self.assertTrue(lines[0].startswith("Scholes, Robert, and Robert Kellogg. Another Book."))
        self.assertTrue(lines[1].startswith(f"{EM_DASHES}. The Nature of Narrative."))
        self.assertTrue(lines[2].startswith("Scholes, Robert, and Eric Rabkin. Science Fiction."))

    def test_perry_same_coauthors_use_dashes_and_chronological_order(self):
        team = [person("Perry", "John"), person("Bratman", "Michael"), person("Fischer", "John Martin")]
        title = "Introduction to Philosophy: Classical and Contemporary Readings"
        entries = [
            {"authors": team, "et_al": True, "title": title, "type": "book", "edition": "8th ed.", "publisher": "Oxford UP", "year": "2018"},
            {"authors": list(team), "et_al": True, "title": title, "type": "book", "edition": "7th ed.", "publisher": "Oxford UP", "year": "2015"},
        ]
        lines, flags = render_works_cited(entries)
        self.assertEqual(flags, [])
        self.assertTrue(lines[0].startswith("Perry, John, et al. Introduction to Philosophy: Classical and Contemporary Readings. 7th ed., Oxford UP, 2015."))
        self.assertTrue(lines[1].startswith(f"{EM_DASHES}. Introduction to Philosophy: Classical and Contemporary Readings. 8th ed., Oxford UP, 2018."))

    def test_horner_different_teams_repeat_et_al_and_sort_by_title(self):
        entries = [
            {
                "authors": [person("Horner", "Bruce"), person("Lu", "Min-Zhan"), person("Royster", "Jacqueline Jones")],
                "et_al": True,
                "title": "Language Difference in Writing: Toward a Translingual Approach",
                "container": "College English",
                "volume": "73",
                "issue": "3",
                "month": "Jan.",
                "year": "2011",
                "pages": "304-21",
            },
            {
                "authors": [person("Horner", "Bruce"), person("Other", "Alex"), person("Team", "Sam")],
                "et_al": True,
                "role": "editors",
                "title": "Cross-Language Relations in Composition",
                "type": "book",
                "publisher": "Southern Illinois UP",
                "year": "2010",
            },
        ]
        lines, flags = render_works_cited(entries)
        self.assertEqual(flags, [])
        self.assertTrue(lines[0].startswith("Horner, Bruce, et al., editors. Cross-Language Relations in Composition."))
        self.assertTrue(lines[1].startswith("Horner, Bruce, et al. \u201cLanguage Difference in Writing:"))
        self.assertNotIn(EM_DASHES, " ".join(lines))

    def test_tannen_solo_then_pairs_then_et_al(self):
        solo = person("Tannen", "Deborah")
        entries = [
            {"authors": [solo, person("Saville-Troike", "Muriel")], "role": "editors", "title": "Perspectives on Silence", "type": "book", "publisher": "Ablex Publishing", "year": "1985"},
            {"authors": [solo, person("Freedle", "Roy O.")], "role": "editors", "title": "Linguistics in Context: Connecting Observation and Understanding", "type": "book", "publisher": "Ablex Publishing", "year": "1988"},
            {"authors": [solo, person("Kendall", "Shari"), person("Gordon", "Cynthia")], "et_al": True, "role": "editors", "title": "Family Talk: Discourse and Identity in Four American Families", "type": "book", "publisher": "Oxford UP", "year": "2007"},
            {"authors": [solo], "title": "You're Wearing That? Understanding Mothers and Daughters in Conversation", "type": "book", "publisher": "Ballantine Books", "year": "2006"},
            {"authors": [solo], "title": "Talking Voices: Repetition, Dialogue, and Imagery in Conversational Discourse", "type": "book", "edition": "2nd ed.", "publisher": "Cambridge UP", "year": "2007"},
        ]
        lines, flags = render_works_cited(entries)
        self.assertEqual(flags, [])
        self.assertTrue(lines[0].startswith("Tannen, Deborah. Talking Voices:"))
        self.assertTrue(lines[1].startswith(f"{EM_DASHES}. You're Wearing That?"))
        self.assertTrue(lines[2].startswith("Tannen, Deborah, and Roy O. Freedle, editors. Linguistics in Context:"))
        # Sec. 2.90's transcribed preposition list does not include "on".
        self.assertTrue(lines[3].startswith("Tannen, Deborah, and Muriel Saville-Troike, editors. Perspectives On Silence."))
        self.assertTrue(lines[4].startswith("Tannen, Deborah, et al., editors. Family Talk:"))
        self.assertEqual(sum(1 for line in lines if line.startswith(EM_DASHES)), 1)

    def test_coauthor_order_is_recorded_as_found(self):
        entries = [
            {"authors": [person("Scholes", "Robert"), person("Kellogg", "Robert")], "title": "The Nature of Narrative", "type": "book", "publisher": "Oxford UP", "year": "1966"},
            {"authors": [person("Kellogg", "Robert"), person("Scholes", "Robert")], "title": "Reversed Names", "type": "book", "publisher": "Oxford UP", "year": "1970"},
        ]
        lines, _ = render_works_cited(entries)
        self.assertTrue(lines[0].startswith("Kellogg, Robert, and Robert Scholes."))
        self.assertTrue(lines[1].startswith("Scholes, Robert, and Robert Kellogg."))

    def test_title_numerals_articles_and_sequences(self):
        titles = [
            "The Representation of War in German Literature",
            "1914: An Anonymous Diary on the Eve of World War I",
            "The Guns of August",
            "Henry V",
            "Henry IV",
            "Star Trek III: The Search for Spock",
            "Star Trek II: The Wrath of Khan",
            "An Encyclopedia of the Latin American Novel",
            "Le théâtre en France au Moyen Age",
        ]
        ordered = sorted(titles, key=title_sort_parts)
        guns = ordered.index("The Guns of August")
        diary = ordered.index("1914: An Anonymous Diary on the Eve of World War I")
        representation = ordered.index("The Representation of War in German Literature")
        self.assertLess(guns, diary)
        self.assertLess(diary, representation)
        self.assertLess(ordered.index("Henry IV"), ordered.index("Henry V"))
        self.assertLess(ordered.index("Star Trek II: The Wrath of Khan"), ordered.index("Star Trek III: The Search for Spock"))
        self.assertTrue(title_sort_parts("1914: An Anonymous Diary on the Eve of World War I")[0].startswith("NINETEENFOURTEEN"))
        self.assertTrue(title_sort_parts("An Encyclopedia of the Latin American Novel")[0].startswith("ENCYCLOPEDIA"))
        self.assertTrue(title_sort_parts("Le théâtre en France au Moyen Age")[0].startswith("THEATRE"))


class EntryPunctuation(unittest.TestCase):
    def test_published_examples(self):
        mantel = format_works_cited_entry(
            {"type": "book", "authors": [person("Mantel", "Hilary")], "title": "Wolf Hall", "publisher": "Picador", "year": "2010"}
        )
        adams = format_works_cited_entry(
            {
                "authors": [person("Adams", "Peter")],
                "et_al": True,
                "title": "The Accelerated Learning Program: Throwing Open the Gates",
                "container": "Journal of Basic Writing",
                "volume": "28",
                "issue": "2",
                "season": "Fall",
                "year": "2009",
                "pages": "50-69",
            }
        )
        berman = format_works_cited_entry(
            {
                "authors": [person("Berman", "Russell A.")],
                "title": "The Necessity of Second-Language Learning",
                "container": "ADFL Bulletin",
                "volume": "43",
                "issue": "2",
                "year": "2015",
                "pages": "11-14",
                "doi": "10.1632/adfl.43.2.11",
            }
        )
        self.assertEqual(mantel, "Mantel, Hilary. Wolf Hall. Picador, 2010.")
        self.assertEqual(
            adams,
            "Adams, Peter, et al. \u201cThe Accelerated Learning Program: Throwing Open the Gates.\u201d "
            "Journal of Basic Writing, vol. 28, no. 2, fall 2009, pp. 50\u201369.",
        )
        self.assertTrue(berman.endswith("https://doi.org/10.1632/adfl.43.2.11."))
        self.assertEqual(format_doi("doi:10.1632/adfl.45.1.171"), "https://doi.org/10.1632/adfl.45.1.171")
        self.assertEqual(format_url("https://www.jstor.org/stable/40859548"), "www.jstor.org/stable/40859548")

    def test_container_exceptions_and_supplied_details(self):
        self.assertEqual(join_seasons("fall", "winter"), "fall-winter")
        self.assertEqual(format_issue_range("3", "4"), "nos. 3\u20134")
        self.assertEqual(supplied("1971", uncertain=True), "[1971?]")
        self.assertEqual(local_newspaper("Herald and Presbyter", "Cincinnati"), "Herald and Presbyter [Cincinnati]")
        self.assertEqual(parenthetical("Baron", "194"), "(Baron 194)")
        self.assertEqual(parenthetical("Wollstonecraft", "185", title="Vindication"), "(Wollstonecraft, Vindication 185)")
        self.assertEqual(parenthetical("Chan", "41", label="par."), "(Chan, par. 41)")
        self.assertEqual(timestamp_span("00:03:16", "00:03:17"), "00:03:16\u201317")


if __name__ == "__main__":
    unittest.main()
