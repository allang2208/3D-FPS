from pathlib import Path
O=Path(__file__).resolve().parent
code=(O/'surface_contact.py').read_text().split("if __name__=='__main__':")[0]
code=code.replace("exec(compile((O/'fit_clearance.py').read_text().split(\"report={'metric'\")[0],'surface_setup','exec'))", "exec(compile((O/'fit_clearance.py').read_text().split(\"report={'metric'\")[0].replace('candidate_poses.json','refined_poses.json'),'surface_setup','exec'))")
exec(compile(code,'surface_library','exec'))
report={}
for role in ('fire','cycle'):
 report[role]={}
 shift=0 if role=='fire' else 4
 for f in (0,*[t+shift for t in (8,12,16,19,22,24,27,29,32,34,36,39,43,46,48)],len(clips[role])-1):
  row=clips[role][f];P=points(row);result=actual(row,P[::3],True);dom=dominant[::3]
  report[role][str(f)]={n:{'penetration_mm':float(max(0,-d.min())*1000),'points':int((d<-.001).sum()),'bones':sorted(set(names[x] for x in dom[d<-.002]))} for n,d in result.items() if d.min()<-.0003}
  print('SURFACE',role,f,report[role][str(f)],flush=True)
(O/'surface_after.json').write_text(json.dumps(report,indent=2))
