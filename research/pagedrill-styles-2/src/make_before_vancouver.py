"""Messy 'before' for Vancouver: author-year citations, APA-style reference list in alphabetical order. Fictional author; real references (PubMed/Crossref-checked)."""
import sys; sys.path.insert(0, "src")
from fmtlib import *
d = Document(); d.styles["Normal"].font.name = "Arial"; d.styles["Normal"].font.size = Pt(11)
def P(t, style=None):
    return d.add_paragraph(t, style=style)
P("Immunosuppression, Readmission and Brain Injury: A Short Review", "Title")
P("Jordan Example, Example College of Nursing")
P("Introduction", "Heading 1")
P("Solid-organ transplantation in people living with HIV was once rare, but outcomes have changed (Halpern et al., 2002). Older adults admitted for adverse drug reactions are often readmitted for the same reason (Zhang et al., 2009).")
P("Discussion", "Heading 1")
P("Laboratory work on brain injury shows how quickly excitatory amino acids rise after a contusion (Rose et al., 2002). Standard microbiology texts describe the infections that follow immunosuppression (Murray et al., 2002; Halpern et al., 2002).")
P("References", "Heading 1")
for t in ("Halpern, S. D., Ubel, P. A., & Caplan, A. L. (2002, July 25). Solid-Organ Transplantation in HIV-Infected Patients. New England Journal of Medicine, 347(4), 284-287.",
          "Murray, P. R., Rosenthal, K. S., Kobayashi, G. S., & Pfaller, M. A. (2002). Medical Microbiology (4th ed.). St. Louis: Mosby.",
          "Rose, M. E., Huerbin, M. B., Melick, J., Marion, D. W., Palmer, A. M., Schiding, J. K., Kochanek, P. M., & Graham, S. H. (2002). Regulation of Interstitial Excitatory Amino Acid Concentrations After Cortical Contusion Injury. Brain Research, 935(1-2), 40-46.",
          "Zhang, M., Holman, C. D., Price, S. D., Sanfilippo, F. M., Preen, D. B., & Bulsara, M. K. (2009, January 7). Comorbidity and Repeat Admission to Hospital for Adverse Drug Reactions in Older Adults: Retrospective Cohort Study. BMJ, 338, a2752. https://doi.org/10.1136/bmj.a2752"):
    p = P(t); p.paragraph_format.left_indent = Inches(0.5); p.paragraph_format.first_line_indent = -Inches(0.5)
d.save(sys.argv[1] if len(sys.argv) > 1 else "vanc_before.docx"); print("ok")
