"""Orthographic shell and head inspection in the two native head frames."""
import argparse, json
from pathlib import Path
import numpy as np
from numba import njit
from PIL import Image, ImageDraw, ImageFont
P=Path(__file__).resolve().parents[2]
S=P/'SourceAssets/ModernTacticalSet20261113'
OLD=S/'HelmetHairFitR1'
OUT=S/'HelmetContourR2/Review'
rgba=np.array([[142,117,87],[101,84,61],[61,53,45],[106,86,62],[91,79,62],[68,57,49],[86,83,78],[172,153,137]],float)
def read(p):return json.loads(p.read_bytes())
@njit
def raster(buf,zbuf,q,f,c):
    h,w=zbuf.shape
    for k in range(len(f)):
        a,b,d=q[f[k,0]],q[f[k,1]],q[f[k,2]]
        xx0=max(0,int(np.floor(min(a[0],b[0],d[0]))));xx1=min(w-1,int(np.ceil(max(a[0],b[0],d[0]))))
        yy0=max(0,int(np.floor(min(a[1],b[1],d[1]))));yy1=min(h-1,int(np.ceil(max(a[1],b[1],d[1]))))
        area=(b[1]-d[1])*(a[0]-d[0])+(d[0]-b[0])*(a[1]-d[1])
        if abs(area)<.00001:continue
        for y in range(yy0,yy1+1):
            for x in range(xx0,xx1+1):
                l=((b[1]-d[1])*(x+.5-d[0])+(d[0]-b[0])*(y+.5-d[1]))/area
                m=((d[1]-a[1])*(x+.5-d[0])+(a[0]-d[0])*(y+.5-d[1]))/area
                n=1-l-m
                if min(l,m,n)<0:continue
                z=a[2]*l+b[2]*m+d[2]*n
                if z>zbuf[y,x]:zbuf[y,x]=z;buf[y,x]=c[k]
def draw(rig,version,angle):
    head=read(OLD/'Inputs'/f'{rig}_Head.json');h=head['bones']['head'];b=read(OLD/'Inputs'/f'{rig}_Body.json')['bones']['head']
    hp=(np.array(head['positions'])-h['position'])@np.linalg.inv(h['axes'])@b['axes']+b['position']
    data=read((S/version)/'Authored'/f'helmet_{rig}_world.json')
    mat=np.array(data['triangle_materials']);f=np.array(data['triangles'])
    p=np.array(data['positions']);hf=np.array(head['triangles'])
    cam=np.array([np.sin(angle),np.cos(angle),.045]);cam/=np.linalg.norm(cam)
    right=np.array([-np.cos(angle),np.sin(angle),0]);up=np.cross(cam,right)
    basis=np.array([right,-up,cam])
    buf=np.full((420,388,3),[40,43,47],dtype=np.uint8);zbuf=np.full(buf.shape[:2],-1e4)
    for v,faces,cols in [(hp,hf,np.full(len(hf),7)),(p,f,mat)]:
        n=np.cross(v[faces[:,1]]-v[faces[:,0]],v[faces[:,2]]-v[faces[:,0]])
        n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-10)
        n[n@cam<0]*=-1
        key=cam*.48+right*(-.50)+up*.72
        shade=.64+.40*np.maximum(0,n@key)
        c=np.clip(rgba[cols]*shade[:,None],0,255).astype(np.uint8)
        q=(v-np.array([0.,1.7,hp[:,2].max()-10.6]))@basis.T;q[:,0]=q[:,0]*11.1+194;q[:,1]=q[:,1]*11.1+215
        raster(buf,zbuf,q,faces,c)
    return Image.fromarray(buf)
def main():
    p=argparse.ArgumentParser();p.add_argument('version');args=p.parse_args()
    out=Image.new('RGB',(388*3,454*2),(40,43,47));d=ImageDraw.Draw(out);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
    for j,rig in enumerate(['Jason','Kaitlin']):
        for i,(angle,label) in enumerate([(0,'Front'),(.72,'Three-quarter'),(np.pi/2,'Side')]):
            out.paste(draw(rig,args.version,angle),(i*388,j*454))
            d.text((i*388+12,j*454+414),rig+' / '+label,fill=(222,217,209),font=font)
    OUT.mkdir(exist_ok=True,parents=True);out.save(OUT/(args.version+'.jpg'),quality=90)
if __name__=='__main__':main()
