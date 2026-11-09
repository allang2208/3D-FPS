from pathlib import Path
import pickle,json,sys
r=Path(__file__).resolve().parent;families=['vertical','canted','prism','angled'];original=pickle.load(open(r/'return_fit.pkl','rb'));report=json.loads((r/'dense_all.json').read_text())
if sys.argv[1]=='prepare':
 for family in families:
  file=r/('return_fit_'+family+'.pkl')
  if not file.exists():pickle.dump(original,open(file,'wb'))
  file=r/('dense_'+family+'.json')
  if not file.exists():file.write_text(json.dumps({k:v for k,v in report.items() if k.startswith(family+'/')},indent=2))
else:
 for family in families:
  local=pickle.load(open(r/('return_fit_'+family+'.pkl'),'rb'))
  for key,value in local.items():
   if key[0]==family:original[key]=value
  local=json.loads((r/('dense_'+family+'.json')).read_text())
  if len(local)!=2 or any(v['remaining_over_1_8mm'] for v in local.values()):raise RuntimeError('Contact still unresolved: '+family)
  report.update(local)
 pickle.dump(original,open(r/'return_fit.pkl','wb'));(r/'dense_all.json').write_text(json.dumps(report,indent=2))
print('CONTACT25_DENSE_FILES',sys.argv[1],flush=True)
