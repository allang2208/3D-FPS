"""Contact sheets from the real owner capture and remote equipment instances."""
import sys,json
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(sys.argv[1]);out=root/'sheets';out.mkdir(exist_ok=True)
def entries(path):return [json.loads(x) for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def make(name,rows):
    canvas=Image.new('RGB',(260*len(rows[0]),220*len(rows)),'#242424');draw=ImageDraw.Draw(canvas)
    for y,row in enumerate(rows):
        for x,(file,label) in enumerate(row):
            im=Image.open(file).convert('RGB');im.thumbnail((260,195));canvas.paste(im,(260*x+(260-im.width)//2,220*y+20));draw.text((260*x+4,220*y+3),label,fill='white')
    canvas.save(out/(name+'.jpg'),quality=93)
for peer in ['host','client']:
    v=root/peer/'Visual'
    for fname,sub in [('owner','Owner'),('close','Close')]:
        data=entries(v/(fname+'.jsonl'))
        for view in ([''] if fname=='owner' else ['_0','_1']):
            for parity in [0,1]:
                rows=[]
                for case in range(parity,8,2):
                    keys=[r for r in data if r['case']==case and Path(r['image']).stem.endswith(view)]
                    if not keys:continue
                    row=[]
                    for stage,fraction,label in [(1,.85,'idle'),(2,.9,'aim'),(3,.05,'release'),(3,.35,'reload'),(3,.75,'reload'),(3,.94,'return'),(6,.8,'settled')]:
                        seq=[r for r in keys if r['stage']==stage]
                        if not seq:continue
                        r=seq[round((len(seq)-1)*fraction)];row.append((v/sub/r['image'],f'{case} {label} {r["source_time"]:.2f}'))
                    if row:rows.append(row)
                if rows:make(f'{peer}_{fname}{view}_{parity}',rows)
    remote=entries(v/'remote.jsonl');groups={}
    for r in remote:groups.setdefault(r['weapon_instance'],[]).append(r)
    rows=[]
    for key,seq in groups.items():
        active=[i for i,r in enumerate(seq) if r['action']!=0]
        if not active or not seq[-1]['profile']:continue
        ids=[0,active[0],active[len(active)//2],active[-1],min(len(seq)-1,active[-1]+2),len(seq)-1]
        rows.append([(v/'Remote'/seq[i]['image'],f'{key[:5]} action {seq[i]["action"]}') for i in ids])
    if rows:make(peer+'_remote',rows)
