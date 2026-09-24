"""Background fabrication of the freight entrance mesh and its PBR detail maps."""
import json
import re
import shutil
import sys
from pathlib import Path
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
FREIGHT=ROOT.parent/'DungeonVentFreight20260922'
for folder in ('Authored/Textures','Sources','Receipts'):
    (ROOT/folder).mkdir(parents=True,exist_ok=True)
source=FREIGHT/'Scripts/author.py'
blend=FREIGHT/'Authored/Dungeon_VentFreight.blend'
manifest_path=FREIGHT/'Authored/manifest.json'
name='SM_RS_FreightTransfer_Lift'
for path in (blend,manifest_path,FREIGHT/'Authored'/(name+'.fbx')):
    backup=ROOT/'Sources'/path.name
    if not backup.exists():shutil.copy2(path,backup)

scope={'__file__':str(source),'__name__':'freight_door_partial_author'}
exec(compile(source.read_text(encoding='utf-8').split("for index,room in enumerate(H['CFG']['rooms']):",1)[0],str(source),'exec'),scope)
h=scope['H'];h['ROOM']=next(r for r in h['CFG']['rooms'] if r['id']=='FreightTransfer')
h['GROUPS']={};h['RECORDS']=[]
scope['build_freight_door'](h)
obj=scope['export_lift'](h)
record=h['RECORDS'][0]
replacement=ROOT/'Authored/FreightEntrance.blend'
bpy.data.libraries.write(str(replacement),{obj})

# Original tileable detail fields: restrained paint grain, directional machining,
# sparse scratches and localized oxide. Numerical PBR source, no external imagery.
n=1024;rng=np.random.default_rng(923302)
y,x=np.mgrid[0:n,0:n].astype(np.float32)/n
grain=rng.random((n,n),dtype=np.float32)
macro=np.clip(.5+.19*np.sin(x*np.pi*6+np.sin(y*np.pi*4))
    +.14*np.cos(y*np.pi*8+x*np.pi*2),0,1)
brushed=.5+.25*np.sin(y*np.pi*442+.35*np.sin(x*np.pi*12))+.25*(grain-.5)
scratches=np.clip((np.sin(y*np.pi*728+np.sin(x*np.pi*4))-.98)*40,0,1)
scratches*=np.clip((macro-.42)*4,0,1)
oxide=np.clip((macro*.7+grain*.3-.50)*3.0,0,1)
packed=np.stack((oxide,np.clip(.5+.2*(brushed-.5)+.20*(grain-.5),0,1),scratches),axis=-1)
height=.008*(brushed-.5)+.004*(grain-.5)-.025*scratches
dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.8
dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.8
normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
maps={}
for label,rgb in (('Detail',packed),('Normal',normal*.5+.5)):
    image=bpy.data.images.new('FreightSurface_'+label,width=n,height=n,alpha=True)
    image.colorspace_settings.name='Non-Color'
    rgba=np.concatenate((rgb.astype(np.float32),np.ones((n,n,1),np.float32)),axis=-1)
    image.pixels.foreach_set(rgba.ravel())
    path=ROOT/'Authored/Textures'/('FreightSurface_'+label+'.png')
    image.filepath_raw=str(path);image.file_format='PNG';image.save()
    maps[label]=str(path)

bpy.ops.wm.open_mainfile(filepath=str(blend))
previous=bpy.data.objects.get(name)
if previous is None:raise RuntimeError('Source entrance mesh missing')
bpy.data.objects.remove(previous,do_unlink=True)
with bpy.data.libraries.load(str(replacement),link=False) as (src,dst):dst.objects=[name]
for obj in dst.objects:
    bpy.context.scene.collection.objects.link(obj)
    for slot in obj.material_slots:
        key=re.sub(r'\.\d{3}$','',slot.material.name)
        if key in bpy.data.materials:slot.material=bpy.data.materials[key]
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
manifest['objects']=[record if r['name']==name else r for r in manifest['objects']]
manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
record['asset']='/Game/Dungeons/VentFreight20260922/Meshes/'+name
from door_geometry import FINISHES
receipt=dict(stage='authored',objects=[record],maps=maps,colors=FINISHES,
    source=str(blend),tests_run=False,rendered=False,normal_convention='DirectX')
(ROOT/'Authored/manifest.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
(ROOT/'Receipts/authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('FREIGHT_ENTRANCE_AUTHORED',record['asset'],flush=True)
