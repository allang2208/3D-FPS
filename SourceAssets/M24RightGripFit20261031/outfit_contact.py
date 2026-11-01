from pathlib import Path
O=Path(__file__).resolve().parent
exec(compile((O/'fit.py').read_text().split('\nprevious=json.loads')[0],'fit_setup','exec'))
sol=json.loads((FIX/'fit_parameters.json').read_text())
glove=json.loads((CHECK/'ue_field_gloves_black_geometry.json').read_text());gp=np.array(glove['positions'])*[.01,-.01,.01];gw=np.zeros((len(gp),len(names)))
for i,ws in glove['weights'].items():
 for n,w in ws.items():
  if n in indices:gw[int(i),indices[n]]=w
gh=gw[:,handbones].sum(1)>.5;out={}
for variant,v in sol['variants'].items():
 row=pose(np.array(v['parameters']));p=skin(row,P=gp,W=gw);x=(np.c_[p,np.ones(len(p))]@np.array(inv).T)[:,:3]
 out[variant]={}
 for key,b in [('grip_envelope',grip_hulls[variant]),('grip_surface',trees[variant]),('receiver',trees['receiver'])]:
  vals=[signed(b,p)*1000 for p in x[gh]]
  if key=='grip_surface':vals=[v if signed(grip_hulls[variant],p)<0 else abs(v) for p,v in zip(x[gh],vals)]
  out[variant][key]={'penetration_mm':max(0.,-min(vals)),'vertices_over_1mm':sum(d<-1 for d in vals)}
(FIX/'glove_contact.json').write_text(json.dumps(out,indent=2));print('GLOVE_CONTACT',json.dumps(out),flush=True)
