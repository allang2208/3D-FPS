"""Read source geometry and animation reference frames for M27 authoring."""
import json
import math
import struct
from pathlib import Path
import bpy
import numpy as np

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ProductionV1')
SOURCE=ROOT.parent/'MeshyImport20261005V1/Source/Meshy_AI_M_27_Mawbound_Horror_1005150638_texture.glb'
ROOT.mkdir(parents=True,exist_ok=True)
raw=SOURCE.read_bytes(); js=struct.unpack_from('<I',raw,12)[0]
doc=json.loads(raw[20:20+js]); binary=raw[28+js:]
def accessor(i):
    a=doc['accessors'][i];v=doc['bufferViews'][a['bufferView']]
    dtype={5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']]
    arity={'SCALAR':1,'VEC2':2,'VEC3':3}[a['type']]
    size=np.dtype(dtype).itemsize
    return np.ndarray((a['count'],arity),dtype=dtype,buffer=binary,
        offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',size*arity),size)).copy()
p=doc['meshes'][0]['primitives'][0]
pos=accessor(p['attributes']['POSITION']); idx=accessor(p['indices']).reshape(-1,3)
np.savez_compressed(ROOT/'source_geometry.npz',positions=pos,indices=idx,
    normals=accessor(p['attributes']['NORMAL']),uv=accessor(p['attributes']['TEXCOORD_0']))
sections=[]
for height in np.arange(-.85,.91,.1):
    points=pos[np.abs(pos[:,1]-height)<.008]
    if len(points):
        sections.append({'source_y':round(float(height),2),'x_quantiles':np.quantile(points[:,0],[0,.1,.25,.5,.75,.9,1]).round(3).tolist(),
                         'z_quantiles':np.quantile(points[:,2],[0,.1,.5,.9,1]).round(3).tolist()})
(ROOT/'anatomy_sections.json').write_text(json.dumps(sections,indent=2),encoding='utf-8')
print('M27_SECTIONS '+json.dumps(sections),flush=True)

BASE=ROOT.parents[1]
sources={
 'Idle':BASE/'WitchFoundation20260920/Sources/Idle.fbx',
 'Walk':BASE/'WitchFoundation20260920/Sources/Walk.fbx',
 'Dizzy':BASE/'HumanoidStun20260926/fitted/A_Nurse_Dizzy.fbx',
 'Fall':BASE/'HumanoidKnockdown20260926/fitted/A_Nurse_Hit_Knockback.fbx',
 'GetUp':BASE/'HumanoidKnockdown20260926/fitted/A_Nurse_LayToIdle.fbx',
 'ProneGetUp':BASE/'HumanoidKnockdown20260926/fitted/A_Nurse_ProneToIdle.fbx'}
records={}
for role,path in sources.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path),use_anim=True)
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    action=rig.animation_data.action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    rate=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    start,end=action.frame_range
    if role=='Walk':start,end=1,46
    if role=='Idle':start,end=1,228
    count=round((end-start)/rate*30)+1
    bones=[b.name for b in rig.data.bones]
    rests=np.asarray([rig.matrix_world@b.matrix_local for b in rig.data.bones])
    frames=[]
    for i in range(count):
        f=start+i/30*rate
        bpy.context.scene.frame_set(math.floor(f),subframe=f%1)
        frames.append([rig.matrix_world@rig.pose.bones[n].matrix for n in bones])
    np.savez_compressed(ROOT/(role+'_donor.npz'),names=np.array(bones),rest=rests,frames=np.array(frames),
                        parents=np.array([b.parent.name if b.parent else '' for b in rig.data.bones]))
    records[role]={'file':str(path),'action':action.name,'seconds':(count-1)/30,'frames':count,
                   'bone_names':bones,'object_scale':list(rig.scale),'source_frame_start':float(start),
                   'source_frame_end':float(end),'sample_fps':30}
    print('M27_DONOR '+role+' '+str(count)+' frames '+','.join(bones[:12]),flush=True)
(ROOT/'donor_sources.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
