"""Messy 'before' IEEE conference draft: Calibri 12, one column, typed heading numbers, author-year citations,
APA-ish reference list in alphabetical order, page numbers in the footer, 'Abstract:' label. Fictional author; references are real (Crossref-checked)."""
import sys; sys.path.insert(0, "src")
from fmtlib import *
d = Document(); st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(12)
s = d.sections[0]; s.left_margin = s.right_margin = Inches(1.25)
fp = s.footer.paragraphs[0]; fp.text = "Page "; add_field(fp, "PAGE")
def P(t, style=None, bold=False, center=False):
    p = d.add_paragraph(style=style); r = p.add_run(t); r.bold = bold
    if center: p.alignment = 1
    return p
P("LOW-COST DISPLAY AND SENSING HARDWARE FOR UNDERGRADUATE ENGINEERING LABS", bold=True, center=True).runs[0].font.size = Pt(16)
for t in ("Casey Example", "Department of Electrical Engineering", "Example State University", "Springfield, USA"): P(t, center=True)
P("Abstract: Undergraduate laboratories need display and sensing hardware that students can build, test and repair. We review four published results that suggest where such hardware is heading and what limits it. Printed and oxide-transistor displays can now be made with simple processes. Models of fields induced in moving bodies show how carefully exposure must be estimated. Better decoding analysis shows how much link margin a cheap radio really has. We describe a lab sequence built on these ideas.")
P("Keywords: engineering education, displays, sensors, laboratory design")
P("1. Introduction", "Heading 1")
P("Electrophoretic displays driven by amorphous oxide thin-film transistors are one low-power option for student projects (Ito et al., 2008). Organic light-emitting diode pixels can also be printed by laser-assisted forward transfer (Fardel et al., 2007).")
P("2. Methods", "Heading 1")
P("2.1 Field exposure", "Heading 2")
P("Students first estimate the electric field induced in a body that moves near a strong magnet, following the boundary element procedure of Chiampi and Zilberti (2011).")
P("2.2 Wireless links", "Heading 2")
P("The second exercise uses the analysis described in reference (Vatta et al., 2019) to predict how sum-product decoding behaves on a noisy channel. Together these sources cover displays, exposure and links (Chiampi and Zilberti, 2011; Ito et al., 2008; Fardel et al., 2007).")
P("3. Conclusion", "Heading 1")
P("A small set of published methods is enough to anchor a full semester of hands-on work.")
P("Acknowledgements", "Heading 1")
P("The author thanks the teaching assistants who tested each exercise.")
P("References", "Heading 1")
for t in ("Chiampi, M. M., & Zilberti, L. L. (2011, October). Induction of Electric Field in Human Bodies Moving Near MRI: An Efficient BEM Computational Procedure. IEEE Transactions on Biomedical Engineering, 58(10), 2787-93. https://doi.org/10.1109/TBME.2011.2158315",
          "Fardel, R., Nagel, M., Nüesch, F., Lippert, T., & Wokaun, A. (2007, August). Fabrication of organic light-emitting diode pixels by laser-assisted forward transfer. Applied Physics Letters, 91(6), 061103. doi:10.1063/1.2759475",
          "Ito, M., Miyazaki, C., Ishizaki, M., Kon, M., Ikeda, N., Okubo, T., Matsubara, R., Hatta, K., Ugajin, Y., & Sekine, N. (2008, May). Application of amorphous oxide TFT to electrophoretic display. Journal of Non-Crystalline Solids, 354(19-25), 2777-2782.",
          "Vatta, F., Soranzo, A., & Babich, F. (2019, February). More Accurate Analysis of Sum-Product Decoding of LDPC Codes Using a Gaussian Approximation. IEEE Communications Letters, 23(2), 230-233. https://doi.org/10.1109/LCOMM.2018.2886261"):
    p = P(t); p.paragraph_format.left_indent = Inches(0.5); p.paragraph_format.first_line_indent = -Inches(0.5)
d.save(sys.argv[1] if len(sys.argv) > 1 else "ieee_before.docx"); print("ok")
