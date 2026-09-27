"""V15 effort and release refinement, preserving V11 contact and native bind."""
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1]
s=(ROOT/'SourceAssets/BowSightContact20260926/generated_actions.py').read_text(encoding='utf8')
s=s.replace('shoulder_open=smooth(support)','shoulder_open=smooth(max(0.,(support-.10)/.90))\n    elbow_open=smooth(min(1.,support*1.18))')
s=s.replace('PREP_ELBOW_POLES[side].lerp(DRAW_ELBOW_POLES[side],shoulder_open)','PREP_ELBOW_POLES[side].lerp(DRAW_ELBOW_POLES[side],elbow_open if side==\'r\' else shoulder_open)')
s=s.replace("shoulder_target=SHOULDERS[side].lerp(raised_shoulder,raised)","shoulder_target=SHOULDERS[side].lerp(raised_shoulder,raised)\n        if side=='r' and role=='Draw':shoulder_target+=Vector((-.7,.25,-.35))*math.sin(math.pi*support)**2")
s=s.replace("nock=bow@BRACE.lerp(ANCHOR,q)","if role=='Hold':\n        # Shared transport preserves both real hand contacts at every sample.\n        bow.translation+=Vector((.06*math.sin(2*math.pi*phase),.025*math.sin(4*math.pi*phase),.04*math.sin(2*math.pi*phase)))\n    nock=bow@BRACE.lerp(ANCHOR,q)")
s=s.replace('release=smooth(t/.075)','release=smooth(t/.085)').replace('settle=smooth((t-.14)/(.64-.14))','settle=smooth((t-.10)/(.64-.10))')
s=s.replace('Vector((-1.1,.35,-.35))*recoil','Vector((-.45,.10,-.10))*recoil').replace('Vector((-4.5*release,5.5*release,1.8*release))','Vector((-2.2*release,1.5*release,.55*release))')
s=s.replace("seconds=.050 if digit in ('index','middle','ring')","seconds=.032 if digit in ('index','middle','ring')")
s=s.replace("Bow_SupportClearanceV11.blend","Bow_EffortReleaseV15.blend")
(P/'generated_actions.py').write_text(s,encoding='utf8')
exec(compile(s,str(P/'generated_actions.py'),'exec'),{'__file__':str(P/'generated_actions.py')})
