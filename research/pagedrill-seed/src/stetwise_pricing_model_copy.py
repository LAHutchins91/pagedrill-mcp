# Stetwise cost model. All unit prices from pricing pages fetched 2026-10-10 (see pricing.md).
CR_CPU=0.000024; CR_MEM=0.0000025   # Cloud Run request-based, active, per vCPU-s / GiB-s (tier 1)
VCPU=2; GIB=4                        # engine instance size (Python + LibreOffice), concurrency 1
SUPA_EGRESS=0.09; SUPA_STORE=0.0213  # Supabase Pro overage $/GB, $/GB-month
GCP_EGRESS=0.12                      # ASSUMED: Cloud Run -> internet (Supabase) $/GB, page not fetched
V_INV=0.60/1e6; V_CPU_H=0.128; V_MEM_GBH=0.0106
RESEND=0.90/1000
def cost(name, files, mb, edits, recalcs, retention_days=1, emails=3,
         s_light=1.5, s_recalc=12):
    calls = files*5 + edits*2 + recalcs          # import/inspect/2 reads/export per file; propose+apply per edit
    eng_s = (files*5 + edits*2)*s_light + recalcs*s_recalc
    compute = eng_s*(VCPU*CR_CPU + GIB*CR_MEM)
    gb = mb/1024
    supa_egress_gb = calls*gb + files*gb          # engine pulls the file each call + user downloads
    gcp_egress_gb = (edits + recalcs)*gb          # engine writes a new version per apply / recalc
    versions_gb = (files + edits + recalcs)*gb
    storage = versions_gb*(retention_days/30)*SUPA_STORE
    vercel = calls*V_INV + calls*0.1/3600*V_CPU_H + calls*1.0/3600*0.5*V_MEM_GBH
    total = compute + supa_egress_gb*SUPA_EGRESS + gcp_egress_gb*GCP_EGRESS + storage + vercel + emails*RESEND
    print(f"{name:28s} calls={calls:5d} engine_s={eng_s:7.0f} compute=${compute:.3f} "
          f"supa_egress={supa_egress_gb:5.1f}GB ${supa_egress_gb*SUPA_EGRESS:.3f} gcp_egress={gcp_egress_gb:4.1f}GB ${gcp_egress_gb*GCP_EGRESS:.3f} "
          f"storage=${storage:.4f} vercel=${vercel:.4f} TOTAL=${total:.2f}")
    return total
light = cost("light (20 files,1MB,60 ed)", 20, 1, 60, 10)
typ   = cost("typical (60f,2MB,250 ed)", 60, 2, 250, 40)
heavy = cost("heavy@cap (250f,5MB,1000ed)", 250, 5, 1000, 200, retention_days=7)
abuse = cost("no-cap abuser (600f,10MB,3000)", 600, 10, 3000, 600, retention_days=7)
def stripe(p): return p*0.029+0.30+p*0.007
for label,p,months in [("$7.99/mo",7.99,1),("$9.99/mo",9.99,1),("$79.99/yr",79.99,12),("$99.99/yr",99.99,12)]:
    f=stripe(p); net=(p-f)/months
    print(f"{label:10s} stripe=${f:.2f} net/mo=${net:.2f} | margin light={net-light:.2f} ({(net-light)/(p/months):.0%}) "
          f"heavy={net-heavy:.2f} ({(net-heavy)/(p/months):.0%}) heavy+fixed@25subs={net-heavy-38.88/25:.2f} abuser={net-abuse:.2f}")
print("Cloud Run 1 warm min-instance idle/mo:", round(2592000*(VCPU*0.0000025+GIB*0.0000025),2))
