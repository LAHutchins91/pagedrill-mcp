# Reuses Stetwise's cost() (same unit prices, fetched 2026-10-10; see /workspace/plugins/office-edit/pricing.md).
# A "format job" = upload + inspect + 2 reads + export (5 calls, counted by files) + propose/apply passes (edits) + PDF preview renders (recalcs, 12 s LibreOffice each).
import importlib.util, io, contextlib
spec = importlib.util.spec_from_file_location("m", "src/stetwise_pricing_model_copy.py"); m = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
print("Profile: files/mo, MB, propose+apply passes, preview renders")
light = m.cost("light student (4 papers)", 4, 0.3, 8, 8)
typ   = m.cost("typical (12 docs)", 12, 0.5, 36, 36)
heavy = m.cost("heavy @cap (60 docs)", 60, 2, 300, 120, retention_days=7)
abuse = m.cost("uncapped abuser (500 docs)", 500, 5, 3000, 1500, retention_days=7)
def net(p, months): return (p - (p*0.029 + 0.30 + p*0.007)) / months
for label, p, mo in [("$4.99/mo", 4.99, 1), ("$5.99/mo", 5.99, 1), ("$39.99/yr", 39.99, 12), ("$49.99/yr", 49.99, 12), ("$7.99/mo", 7.99, 1), ("$79.99/yr", 79.99, 12)]:
    n = net(p, mo); print(f"{label:10s} net/mo=${n:.2f}  margin light={n-light:.2f} typical={n-typ:.2f} heavy={n-heavy:.2f} ({(n-heavy)/(p/mo):.0%}) abuser={n-abuse:.2f}")
