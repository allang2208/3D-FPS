from shared import *
import tempfile
inv=read(W/'inventory.json');ledger={}
def add(m,root):
 for k,d in m.items():
  rel=game(k)
  if rel in ledger:raise RuntimeError('Stage overlap '+rel)
  ledger[rel]=dict(package=k,stage=d['stage'],source=str(root/rel),target=d['sha256'])
for stage in ('Repair12','Repair13','Repair16','Finish29'):add(read(W/(stage+'-outputs.json')),W/'SurfaceOutputs')
late=read(W/'authored.json');props=read(W/'existing-icon-settings.json') if (W/'existing-icon-settings.json').exists() else {};mds=read(W/'import-provenance.json');retained={}
if not props:
 for k in list(late):
  if late[k]['stage'] in ('BipodIcon42','Conversation20261112'):late.pop(k)
for k,v in props.items():
 if all(v.values()) and mds[game(k)]['match']:
  late.pop(k);retained[k]=dict(reason='Approved source-art MD5 and texture settings already match',settings=v)
add(late,W/'Host');add(read(W/'original-material-change.json') if (W/'original-material-change.json').exists() else {},W/'SurfaceHost')
write('retained-icons.json',retained)
ready={}
for rel,r in ledger.items():
 src=Path(r['source']);dst=R/rel
 if not dst.exists() or not src.is_file() or sha(src)!=r['target']:raise RuntimeError(rel)
 baseline=inv[rel]['current'];current=sha(dst)
 if current==r['target']:continue
 if current!=baseline:raise RuntimeError('Edited during recovery '+rel)
 bak=W/'Before'/rel;bak.parent.mkdir(exist_ok=True,parents=True)
 if not bak.exists():shutil.copy2(dst,bak)
 if sha(bak)!=current:raise RuntimeError('Backup '+rel)
 incoming=W/'Pending'/rel;incoming.parent.mkdir(parents=True,exist_ok=True)
 if incoming.exists():assert sha(incoming)==r['target']
 else:shutil.copy2(src,incoming)
 assert incoming.resolve().drive.lower()==dst.resolve().drive.lower()
 if sha(incoming)!=r['target']:raise RuntimeError('Staging '+rel)
 for ext in ('.uexp','.ubulk','.uptnl'):
  if src.with_suffix(ext).exists() or dst.with_suffix(ext).exists():raise RuntimeError('Supplemental file '+rel)
 ready[rel]=dict(**r,baseline=baseline,stage_file=str(incoming),original_size=dst.stat().st_size,original_mtime_ns=dst.stat().st_mtime_ns)
prior=read(W/'publish-plan.json') if (W/'publish-plan.json').exists() else {}
write('publish-plan.json',{**prior,**ready})
print('prepared',len(ready),'approved existing icons',len(retained))
