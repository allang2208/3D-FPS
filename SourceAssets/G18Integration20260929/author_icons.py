"""G18 icon entry point; legacy raster helper retained for older repair scripts."""
import json,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
if __name__=='__main__':
    recipe=Path(__file__).parent.parent/'G18IconsFinal20260930/author_icons.py'
    subprocess.run([r'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe','-b','--python-exit-code','1','--python',str(recipe)],check=True)
    print('G18 production icons authored; publish with G18IconsFinal20260930/import_icons.py in UE commandlet')
    sys.exit(0)
O=Path(__file__).parent;D=O.parents[1]/'Content/ColdSteelData';I=O/'Icons';I.mkdir(exist_ok=True)
geo=json.loads((O/'icon_geometry.json').read_text());N=768
def raster(key,grey=False):
    data=geo[key];v=np.asarray(data['vertices'],float);tri=np.asarray(data['triangles'],int)
    # Gun root geometry is -Y forward. Accessories with X as their long axis
    # use XZ side projection; choose from the actual geometry, not the filename.
    extent=np.ptp(v,axis=0);horizontal=1 if extent[1]>=extent[0] else 0;depthaxis=1-horizontal
    pos=v[:,[horizontal,2]];lo=pos.min(axis=0);hi=pos.max(axis=0);scale=.83*N/max(hi-lo)
    xy=(pos-(lo+hi)*.5)*scale+N/2;xy[:,1]=N-xy[:,1]
    depth=np.full((N,N),-1e20);pixels=np.zeros((N,N,4),np.uint8)
    tex=np.asarray(Image.open(O/'Textures/T_G18_Base_color.png').convert('RGB')) if key=='factory' else None
    uvs=np.asarray(data.get('uv',[]))
    light=np.array([.8,-.4,1.]);light/=np.linalg.norm(light)
    for index,ids in enumerate(tri):
        p=xy[ids];a,b,c=p;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-7:continue
        xmin,ymin=np.maximum(0,np.floor(p.min(axis=0)).astype(int));xmax,ymax=np.minimum(N-1,np.ceil(p.max(axis=0)).astype(int))
        if xmax<xmin or ymax<ymin:continue
        xx,yy=np.meshgrid(np.arange(xmin,xmax+1)+.5,np.arange(ymin,ymax+1)+.5)
        w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;w2=1-w0-w1
        z=w0*v[ids[0],depthaxis]+w1*v[ids[1],depthaxis]+w2*v[ids[2],depthaxis]
        target=depth[ymin:ymax+1,xmin:xmax+1];mask=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)&(z>target)
        if not mask.any():continue
        normal=np.cross(v[ids[1]]-v[ids[0]],v[ids[2]]-v[ids[0]]);normal/=max(1e-10,np.linalg.norm(normal));shade=.58+.42*abs(normal@light)
        rgb=np.full((*xx.shape,3),185.*shade)
        if tex is not None and len(uvs):
            uv=w0[...,None]*uvs[index,0]+w1[...,None]*uvs[index,1]+w2[...,None]*uvs[index,2]
            tx=np.minimum(tex.shape[1]-1,(uv[...,0]%1*tex.shape[1]).astype(int));ty=np.minimum(tex.shape[0]-1,((1-uv[...,1]%1)*(tex.shape[0]-1)).astype(int))
            rgb=(tex[ty,tx].astype(float)*1.28+18)*shade
        if grey:rgb=np.repeat((rgb@np.array([.2126,.7152,.0722]))[...,None],3,axis=2)
        region=pixels[ymin:ymax+1,xmin:xmax+1];region[mask,:3]=np.clip(rgb[mask],0,255);region[mask,3]=255;target[mask]=z[mask]
    return Image.fromarray(pixels).resize((512,512),Image.Resampling.LANCZOS)
record={}
for key in geo:
    im=raster(key,grey=key!='factory');file=I/(key+'.png');im.save(file);record[key]=str(file)
(D/'Icons').mkdir(exist_ok=True);shutil.copy2(I/'factory.png',D/'Icons/ue_g18.png')
dest=D/'AttachmentIcons20260913';dest.mkdir(exist_ok=True)
mapping={'optic_false':'factory','optic_holographic':'holographic','optic_panoramic_red_dot':'panoramic_red_dot',
    'muzzle_false':'factory','muzzle_true':'suppressor','muzzle_tactical_suppressor':'tactical_suppressor','muzzle_brake':'brake',
    'magazine_false':'factory_magazine','magazine_ext_mag':'ext_mag','reargrip_false':'GripSurface',
    'reargrip_pistol_grip_granular':'GripSurface','reargrip_pistol_grip_diamond':'GripSurface','reargrip_pistol_grip_quickdot':'GripSurface',
    'trigger_false':'factory','trigger_g18_controlled_trigger':'factory','tactical_false':'factory','tactical_laser':'laser','tactical_flashlight':'flashlight','barrel_false':'factory','barrel_short':'factory','barrel_long':'factory'}
for key,part in mapping.items():
    im=Image.open(I/(part+'.png')).convert('RGBA');alpha=im.getchannel('A');im=im.convert('L').convert('RGBA');im.putalpha(alpha);im.save(dest/('ue_g18_'+key+'.png'))
for category in ('optic','muzzle','magazine','reargrip','trigger','tactical','barrel'):
    shutil.copy2(dest/('ue_g18_'+category+'_false.png'),dest/('ue_g18_category_'+category+'.png'))
(O/'icons.json').write_text(json.dumps({'geometry':record,'catalog':str(D/'Icons/ue_g18.png'),'modification_directory':str(dest),'method':'Offline textured triangle rasterization; modification icons neutral grayscale','runtime_tested':False},indent=2))
print('G18 catalog icons authored')
