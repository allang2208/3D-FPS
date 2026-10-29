"""Extract untouched Free3D world motion and native FBX bind matrices."""
import bpy,json
from pathlib import Path
from mathutils import Matrix
from io_scene_fbx import parse_fbx
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
SRC=ROOT/'SourceAssets/DualBladeSourceSearch20261029'

def row(m):
    p,q,s=m.decompose();return list(p)+[q.x,q.y,q.z,q.w]+list(s)

for role,stem in [('Slash1','Free3D_Cross_Attack'),('Slash2','Free3D_Heavy_Attack')]:
    bpy.ops.wm.open_mainfile(filepath=str(SRC/(stem+'.blend')))
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    names=['Hips']+[b.name.split(':')[-1] for b in arm.data.bones]
    bone_names=[b.name for b in arm.data.bones]
    first,last=arm.animation_data.action.frame_range;rate=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    tree,_=parse_fbx.parse(str(SRC/(stem+'.fbx')))
    objects=next(e for e in tree.elems if e.id==b'Objects')
    ids={e.props[0]:e.props[1].split(b'\x00')[0].decode().split(':')[-1] for e in objects.elems if e.id==b'Model'}
    bind={}
    for e in objects.elems:
        if e.id!=b'Pose':continue
        for item in e.elems:
            if item.id!=b'PoseNode':continue
            node=next(x.props[0] for x in item.elems if x.id==b'Node')
            values=next(x.props[0] for x in item.elems if x.id==b'Matrix')
            if node in ids:bind[ids[node]]=Matrix([values[i:i+4] for i in range(0,16,4)]).transposed()
    # FBX import rotates source Y-up into Blender Z-up and converts cm to m.
    # Derive the exact affine basis from a skin bind instead of assuming it.
    b=arm.data.bones[0];name=b.name.split(':')[-1]
    source_to_blender=(arm.matrix_world@b.matrix_local)@bind[name].inverted()
    reference=[row(source_to_blender@bind[n]) for n in names]
    frames=[]
    for i in range(round((last-first)/rate*120)+1):
        time=first+i*rate/120;f=int(time)
        bpy.context.scene.frame_set(f,subframe=time-f);bpy.context.view_layer.update()
        frames.append([row(arm.matrix_world)]+[row(arm.matrix_world@arm.pose.bones[n].matrix) for n in bone_names])
    data=dict(names=names,reference_world=reference,frames=frames,rate=120,duration=(last-first)/rate,
              source=str(SRC/(stem+'.fbx')),source_first=first,source_last=last,source_rate=rate)
    (OUT/(role+'-source.json')).write_text(json.dumps(data,separators=(',',':')))
    print('EXTRACTED',role,len(frames),'binds',len(bind),'pelvis',reference[0][:3],flush=True)
