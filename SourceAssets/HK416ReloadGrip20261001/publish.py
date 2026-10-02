"""Publish the staged HK416 packages after shared Content has been released."""
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1];C=(P/'Content').resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ps='Get-CimInstance Win32_Process -Filter "Name=\'UnrealEditor.exe\' OR Name=\'UnrealEditor-Cmd.exe\'" | Select-Object -ExpandProperty CommandLine | ConvertTo-Json -Compress'
run=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,text=True,check=True)
commands=json.loads(run.stdout) if run.stdout.strip() else []
if isinstance(commands,str):commands=[commands]
for command in commands:
 for quoted,plain in re.findall(r'"([^"\r\n]+\.uproject)"|(\S+\.uproject)',command,re.IGNORECASE):
  project=Path(quoted or plain)
  if (project.parent/'Content').resolve()==C:raise RuntimeError('Shared Content is still loaded: '+str(project)+'. No staged packages copied.')
manifest=json.loads((O/'staging.json').read_text(encoding='utf-8-sig'))
delivery=json.loads((O/'staged_delivery.json').read_text())
if not delivery.get('saved') or len(delivery['animations'])!=20 or len(delivery['profiles'])!=4:raise RuntimeError('Staged publication is incomplete')
copies=[]
for relative,spec in manifest['targets'].items():
 target=(C/relative).resolve();source=Path(spec['staged_file']).resolve()
 if not target.is_relative_to(C) or not source.is_relative_to((O/'PackageStaging/Content').resolve()):raise RuntimeError('Unexpected package destination')
 if sha(target)!=spec['original_sha256']:raise RuntimeError('Preserve concurrent package edit: '+relative)
 if sha(source)!=spec['original_sha256']:copies.append((source,target))
receipt=O/'publication.json';state={'copied':[],'runtime_tested':False}
for source,target in copies:
 temp=target.with_suffix('.hk416-grip-publish.tmp')
 if temp.exists():raise RuntimeError('Preserve previous publication temp: '+str(temp))
 shutil.copy2(source,temp);os.replace(temp,target)
 state['copied'].append(str(target.relative_to(C)));receipt.write_text(json.dumps(state,indent=1))
delivery.update({'staged':False,'saved':True,'status':'Twenty native HK416 reload clips and affected entries of four runtime grip profiles published; drum profile retained','published_packages':len(copies),'runtime_tested':False})
(O/'delivery.json').write_text(json.dumps(delivery,indent=1))
state['saved']=True;receipt.write_text(json.dumps(state,indent=1))
print('HK416_RELOAD_GRIP_PUBLISHED',len(copies),flush=True)
