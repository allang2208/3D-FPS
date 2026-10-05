"""Author skin-bound muzzle landmarks from the real V02 front aperture rim.
Reads retained mesh geometry and weights; no renders or gameplay validation.
"""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/Monsters/LurkerM08'
OUT=BASE/'RimSpeedV07_20261005';OUT.mkdir(exist_ok=True)
SOURCE=BASE/'AirCannonV06_20261004/M08_AirCannon_Animated_V06.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
obj=bpy.data.objects['SK_LurkerM08'];rig=bpy.data.objects['Armature']
rig.animation_data.action=None
old=json.loads((BASE/'ProductionV01_20261004/authoring.json').read_text(encoding='utf-8'))
scale=old['scale'];pelvis=next(b for b in old['bones'] if b['name']=='pelvis')
offset=np.array(pelvis['head'])/scale-np.array((0,.52,-.055))
coords=np.empty(len(obj.data.vertices)*3,dtype=np.float64)
obj.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
raw=coords/scale-offset
mat=np.empty(len(obj.data.polygons),dtype=np.int32);obj.data.polygons.foreach_get('material_index',mat)
loops=np.empty(len(obj.data.loops),dtype=np.int32);obj.data.loops.foreach_get('vertex_index',loops)
_,first,inverse=np.unique(np.round(coords,6),axis=0,return_index=True,return_inverse=True)
tri=inverse[loops.reshape(-1,3)[mat==1]]
edges=np.sort(np.concatenate((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]])),axis=1)
edges,count=np.unique(edges,axis=0,return_counts=True)
ids=first[np.unique(edges[count==1])]
# Material 1 is the rebuilt internal bore. Its front boundary is the visible
# aperture lip, not a bone centre or an invented offset from the crown.
p=raw[ids];cx=-.00055;cz=.205
theta=np.arctan2((p[:,2]-cz)/.121,(p[:,0]-cx)/.105)
radius=np.sqrt(((p[:,2]-cz)/.121)**2+((p[:,0]-cx)/.105)**2)
front=(p[:,1]<.04)&(radius>.65)&(radius<1.6)
ids=ids[front];theta=theta[front]
rows=[]
for i in range(16):
    angle=i*2*math.pi/16
    delta=np.abs(np.angle(np.exp(1j*(theta-angle))))
    candidates=np.flatnonzero(delta<math.pi/16)
    if not len(candidates):raise RuntimeError('Front rim sector missing '+str(i))
    # The foremost inner/outer material seam is the exit lip along source -Y.
    j=candidates[np.argmin(raw[ids[candidates],1])];index=int(ids[j]);vertex=obj.data.vertices[index]
    weights=[{'bone':obj.vertex_groups[g.group].name,'weight':float(g.weight)} for g in vertex.groups
        if obj.vertex_groups[g.group].name in rig.data.bones and g.weight>1e-6]
    total=sum(w['weight'] for w in weights)
    if total<=0:raise RuntimeError('Unbound rim vertex '+str(index))
    for w in weights:w['weight']/=total
    rows.append({'vertex':index,'position_m':list(vertex.co),'weights':weights,'angle':float(theta[j])})
marker=bpy.data.meshes.new('M08_AirMuzzle_RimSkin')
marker.from_pydata([r['position_m'] for r in rows],[(i,(i+1)%16) for i in range(16)],[])
guide=bpy.data.objects.new('AUTHORING_AirMuzzle_Rim',marker);bpy.context.scene.collection.objects.link(guide)
guide.show_in_front=True;guide.hide_render=True
for name in sorted({w['bone'] for r in rows for w in r['weights']}):
    group=guide.vertex_groups.new(name=name)
    for i,row in enumerate(rows):
        for w in row['weights']:
            if w['bone']==name:group.add([i],w['weight'],'REPLACE')
modifier=guide.modifiers.new('Follow actual rim skin','ARMATURE');modifier.object=rig
guide['purpose']='Exact source front-aperture landmarks for runtime muzzle and charge frame; not gameplay geometry.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M08_RimAnchors_V07.blend'))
report={'revision':'M08_RimSpeedV07_20261005','source':str(SOURCE),'mesh_asset':'/Game/Monsters/LurkerM08/CanineV03/SK_LurkerM08_CanineV03',
    'landmarks':rows,'calibration_bones':{n:list(rig.data.bones[n].head_local) for n in ('pelvis','chest','hand.L','hand.R','arch_crown')},
    'front_rim_bounds_m':{'min':np.array([r['position_m'] for r in rows]).min(axis=0).tolist(),'max':np.array([r['position_m'] for r in rows]).max(axis=0).tolist()},
    'method':'16 front boundary vertices of rebuilt inner bore; retain actual vertex skin weights',
    'runtime_tested':False,'rendered':False}
(OUT/'rim_binding.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M08_RIM_BINDING_AUTHORED '+json.dumps(report['front_rim_bounds_m']),flush=True)
