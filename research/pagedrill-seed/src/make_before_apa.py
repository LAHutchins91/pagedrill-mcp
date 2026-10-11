"""Build a deliberately messy student paper (before.docx).
SAMPLE ONLY: student/instructor/course names are fictional placeholders.
All three references are real works (taken from APA Style's own reference-example pages,
DOIs checked against Crossref on 2026-10-10). Claims about sources only restate their titles."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import sys

out = sys.argv[1] if len(sys.argv) > 1 else "before.docx"
d = Document()
sec = d.sections[0]
sec.left_margin = sec.right_margin = Inches(1.25)   # wrong margins
sec.top_margin = Inches(0.7); sec.bottom_margin = Inches(0.8)
# wrong page header: "Running head:" label, no page number
sec.header.paragraphs[0].text = "Running head: OLDER ADULTS ONLINE"

def para(text, font="Calibri", size=11, bold=False, align=None, style=None, color=None, under=False, italic=False):
    p = d.add_paragraph(style=style) if style else d.add_paragraph()
    r = p.add_run(text); r.font.name = font; r.font.size = Pt(size); r.bold = bold
    r.italic = italic; r.underline = under
    if color: r.font.color.rgb = RGBColor(*color)
    if align is not None: p.alignment = align
    p.paragraph_format.line_spacing = 1.0           # single spacing
    p.paragraph_format.space_after = Pt(10)          # extra space after
    return p

# No title page: header info crammed at top, left-aligned
para("Name: Jordan Sample", "Arial", 10)
para("Class: PSY 201 Intro to Psychology", "Arial", 10)
para("Professor: Dr. Avery Placeholder", "Arial", 10)
para("Due: October 18, 2026", "Arial", 10)
para("older adults, information searching, and shopping online", "Comic Sans MS", 16, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT)

h = para("INTRODUCTION", "Cambria", 14, bold=True, style="Heading 1", color=(0x2F,0x54,0x96))
J = WD_ALIGN_PARAGRAPH.JUSTIFY
para("More older adults now use the internet to find information and to buy everyday goods. "
     "This paper looks at two parts of that change: how older adults search for information, and how they shop online. "
     "Rybaczewska and Sparks 2022 examined e-commerce activities among ageing consumers (Rybaczewska and Sparks 2022).",
     "Georgia", 11, align=J)

para("1. Background", "Cambria", 13, bold=True, style="Heading 1", color=(0x2F,0x54,0x96))
para("Searching for information online is a multi-step task. Sanchiz, Chevalier, and Amadieu (2017) compared how older "
     "and young adults start searching for information and looked at the role of age, domain knowledge, and problem complexity.",
     "Times New Roman", 12, align=J)
para("a) searching for information", "Arial", 12, bold=False, style="Heading 2", under=True)
para("Because searching has several steps, problems at the first step can carry through the rest of a search "
     "(Sanchiz, Chevalier, & Amadieu, 2017; Rybaczewska & Sparks, 2022).", "Calibri", 11, align=J)
para("b) SHOPPING ONLINE", "Arial", 12, bold=True, style="Heading 2")
para("Online shopping is one of the e-commerce activities that ageing consumers take part in (Rybaczewska & Sparks, 2022).",
     "Calibri", 11, align=J)
para("Help From the Community", "Arial", 11, bold=False, italic=False, style="Heading 3")
para("During the COVID-19 pandemic, some people helped older neighbours get groceries and supplies (Toner).",
     "Calibri", 11, align=J)

para("Conclusion", "Cambria", 14, bold=True, style="Heading 1", color=(0x2F,0x54,0x96))
para("Older adults are active online, but the tools they use should fit how they search and shop. "
     "Future work could look at both activities together.", "Calibri", 11, align=J)

# Reference list: wrong label, not on new page, wrong order, no hanging indent, mixed formats
para("Works Cited:", "Calibri", 14, bold=True, under=True)
para("Toner, K. When Covid-19 hit, he turned his newspaper route into a lifeline for senior citizens. CNN. "
     "https://www.cnn.com/2020/06/04/us/coronavirus-newspaper-deliveryman-groceries-senior-citizens-cnnheroes-trnd/index.html",
     "Calibri", 11)
para("Maria Rybaczewska and Leigh Sparks (2022). \"Ageing consumers and e-commerce activities\", Ageing and Society, "
     "42(8), pp. 1879-1898. doi:10.1017/S0144686X20001932", "Calibri", 11)
para("Sanchiz, M., Chevalier, A., Amadieu, F. 2017. How do older and young adults start searching for information? "
     "Impact of age, domain knowledge and problem complexity on the different steps of information searching. "
     "Computers in Human Behavior 72, 67-78.", "Times New Roman", 12)
d.core_properties.comments = "SAMPLE DOCUMENT: student, instructor and course are fictional placeholders. References are real works."
d.core_properties.author = "Jordan Sample (fictional)"
d.save(out)
print("wrote", out)
