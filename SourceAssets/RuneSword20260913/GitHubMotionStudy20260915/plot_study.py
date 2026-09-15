import json,pathlib,numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.spatial import ConvexHull
root=pathlib.Path(__file__).parent;data=json.loads((root/'motion_data.json').read_text());out=root/'sheets';out.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
for c in data:
    frames=np.linspace(0,c['count']-1,12).round().astype(int)
    image=Image.new('RGB',(1440,840),(24,28,35));d=ImageDraw.Draw(image)
    for k,f in enumerate(frames):
        x=(k%4)*360;y=(k//4)*280;pts=np.array(c['points'][f]);wm=np.array(c['weapon'][f]);v=(wm@np.c_[c['vertices'],np.ones(len(c['vertices']))].T).T[:,:3]
        # Fixed Source first-person projection: forward -Y, right -X, up +Z.
        def project(p):return (x+140-p[0]*13,y+105-p[2]*13)
        for part in c['parts']:
            pm=np.array(part['matrices'][f]); pv=(pm@np.c_[part['vertices'],np.ones(len(part['vertices']))].T).T[:,:3]
            vv=np.array([project(p) for p in pv]); hull=ConvexHull(vv);d.polygon([tuple(vv[j]) for j in hull.vertices],fill=(175,185,193))
        for a,b in c['edges']:
            color=(80,190,220) if 'Finger' in c['names'][b] or 'Tip' in c['names'][b] else (110,115,123)
            if c['names'][b].startswith('Finger0') or c['names'][b]=='Tip0':color=(245,175,75)
            d.line([project(pts[a]),project(pts[b])],fill=color,width=5)
        for j,p in enumerate(pts):
            a,b=project(p);d.ellipse((a-3,b-3,a+3,b+3),fill=(235,235,235))
        d.text((x+10,y+10),f"{c['name']}  f{f}  {f/30:.2f}s",font=font,fill=(230,235,240))
    image.save(out/(c['name'].replace('/','_')+'.png'))
print(out)
