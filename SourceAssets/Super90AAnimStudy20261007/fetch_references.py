"""Collect public format/hierarchy sources for research; never execute fetched code."""
from pathlib import Path
import urllib.request,json,hashlib,subprocess
O=Path(__file__).parent/'Sources';O.mkdir(exist_ok=True)
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'FPSGAME-animation-research'})
    with urllib.request.urlopen(req,timeout=40) as r:return r.read()
sources=[]
for repo,files in [
    ('MrClock8163/Arma3ObjectBuilder',['Arma3ObjectBuilder/utilities/data.py','Arma3ObjectBuilder/io/data_rtm.py','Arma3ObjectBuilder/io/import_rtm.py','LICENSE'])]:
    result=subprocess.run(['git','ls-remote','https://github.com/'+repo+'.git','refs/heads/master'],capture_output=True,text=True,check=True,timeout=40)
    commit=result.stdout.split()[0]
    for file in files:
        url='https://raw.githubusercontent.com/'+repo+'/'+commit+'/'+file
        try:raw=get(url)
        except Exception as e:
            sources.append({'url':url,'error':str(e)});continue
        dest=O/(repo.split('/')[-1]+'_'+Path(file).name);dest.write_bytes(raw)
        sources.append({'url':url,'file':str(dest),'sha256':hashlib.sha256(raw).hexdigest()})
    print(repo,commit,flush=True)
(O/'sources.json').write_text(json.dumps(sources,indent=2))
