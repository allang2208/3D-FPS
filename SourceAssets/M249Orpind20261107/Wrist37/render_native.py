"""Inspect UE-exported final CPU skin, morphs, dynamic belts and attachments."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
capture=ROOT.parent/'Wrist34/geometry_wrist_thirty_seven_probe';out=ROOT/'native_probe';out.mkdir(exist_ok=True)
(out/'capture.json').write_text(json.dumps(dict(capture=str(capture))))
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1000;scene.render.resolution_y=760;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('World');scene.world.color=(.075,.075,.075)
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
def mat(name,col):
    m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);return m
skin=mat('Skin',(.58,.34,.22));metal=mat('Gun',(.14,.19,.23));brass=mat('Belt',(.56,.38,.13))
def mesh(name,p,f,m):
    if not len(f):return
    ids,ind=np.unique(f,return_inverse=True);me=bpy.data.meshes.new(name);me.from_pydata(p[ids].tolist(),[],ind.reshape(-1,3).tolist());me.materials.append(m)
    for face in me.polygons:face.use_smooth=name=='Skin'
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob)
for folder in sorted(capture.glob('box_*')):
    empty='empty' in folder.name;shift=.9 if empty else 0.;meta=json.loads((folder/'geometry.json').read_text());rows=json.loads((folder/'review.json').read_text())['frames'];dom=np.fromfile(folder/'dominant.bin',np.uint32);names=meta['bones'];slots=meta['slots']
    picks=[('hold',rows[-1]['source'],'l'),('regrip',2.6-shift,'l'),('support',3.-shift,'l'),('cover',.65,'l'),('free',1.,'l')]
    if folder.name.endswith('_base'):picks+=[('belt_pick',4.52-shift,'r'),('belt_lift',4.8-shift,'r'),('belt_place',5.1-shift,'r')]
    for tag,tm,side in picks:
        row=min(rows,key=lambda x:abs(x['source']-tm));stem=folder/Path(row['file']).stem;p=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3)*[1,-1,1];f=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3);materials=np.fromfile(stem.with_suffix('.materials'),np.uint32)
        hand=p[dom==names.index('hand_'+side)].mean(0);fore=p[dom==names.index('lowerarm_twist_01_'+side)].mean(0);center=hand*.7+fore*.3
        for view,offset in [('outside',[60,10,25]),('palm',[-60,-20,18])]:
            for ob in list(scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
            visible=np.isin(materials,row['visible_materials']);sk=np.array([s.startswith('Skin_') for s in slots])[materials];sd=np.array([n.endswith('_'+side) for n in names])[dom];blt=np.array(['Belt' in s for s in slots])[materials];glass=np.array(['Glass' in s or 'Reticle' in s for s in slots])[materials]
            mesh('Skin',p,f[visible&sk&sd[f].any(1)],skin);mesh('Gun',p,f[visible&~sk&~blt&~glass],metal);mesh('Belt',p,f[visible&~sk&blt],brass)
            for part in folder.glob(stem.name+'_*.vertices'):
                mesh(part.stem,np.fromfile(part,np.float32).reshape(-1,3)*[1,-1,1],np.fromfile(part.with_suffix('.indices'),np.uint32).reshape(-1,3),metal)
            cam=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',cam);scene.collection.objects.link(co);scene.camera=co;co.location=center+np.array(offset);co.rotation_euler=(Vector(center)-co.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=34;cam.clip_start=.1
            scene.render.filepath=str(out/f'{folder.name}_{tag}_{view}.png');bpy.ops.render.render(write_still=True)
