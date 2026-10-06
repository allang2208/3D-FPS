import bpy,json,sys,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
sys.path.insert(0,str(O.parent/'RSH12InspectGrip20261004'))
from grip_scene import load,pose,native_pose,applied,matrix
report={}
for side in ('single','r','l'):
    if not (O/'Before'/(side+'_mesh.json')).exists():continue
    rig,data,authored,meta=load(side)
    source_meshes=[ob for ob in bpy.data.objects if ob.type=='MESH']
    payload=json.loads((O/'Before'/('DA_RSH12_'+('' if side=='single' else side+'_')+'base.json')).read_text())
    active={c['base']:c for c in payload['clips']}
    # Compare exactly the sparse mechanical tracks saved in UE.
    diffs=[]
    for clip in authored['clips']:
        tracks={tr['bone']:tr for tr in active[clip['base']]['tracks']}
        for tr in clip['tracks']:
            if not tr['bone'].startswith('WPN_'):continue
            other=tracks.get(tr['bone'])
            if other is None:diffs.append([clip['kind'],tr['bone'],'missing']);continue
            if len(other['values'])!=len(tr['values']):diffs.append([clip['kind'],tr['bone'],'length']);continue
            error=max(abs(a-b) for a,b in zip(other['values'],tr['values']))
            if error>1e-5:diffs.append([clip['kind'],tr['bone'],error])
    def geometry(rig,p,meshes):
        frame=(p['WPN_root']@Matrix(meta['alignment'])).inverted()
        result={}
        for bone in ('WPN_root','WPN_Crane','WPN_Cylinder','WPN_Extractor'):
            coords=[]
            for ob in meshes:
                if bone not in ob.vertex_groups:continue
                group=ob.vertex_groups[bone].index
                bind=frame@p[bone]@rig.data.bones[bone].matrix_local.inverted()@rig.matrix_world.inverted()@ob.matrix_world
                coords.extend([list(bind@v.co) for v in ob.data.vertices if any(g.group==group and g.weight>.99 for g in v.groups)])
            pts=np.array(coords);center=pts.mean(axis=0);val,vec=np.linalg.eigh(np.cov(pts.T));axis=vec[:,-1]
            if axis[1]<0:axis=-axis
            result[bone]=dict(count=len(pts),center=center.tolist(),bounds=[pts.min(0).tolist(),pts.max(0).tolist()],long_axis=axis.tolist(),angle=math.degrees(math.acos(min(1.,max(-1.,axis[1])))))
        return result
    p=pose(rig,data,authored,'idle',data['clips']['idle']['samples'][0])
    source=geometry(rig,p,source_meshes)
    if (O/'Before'/(side+'.fbx')).exists():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(O/'Before'/(side+'.fbx')))
        rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.animation_data_clear()
    meshes=[ob for ob in bpy.data.objects if ob.type=='MESH']
    saved=json.loads((O/'Before'/(side+'_mesh.json')).read_text())
    result=dict(mechanical_profile_diffs=diffs,source=source,evaluated={})
    key=next(k for k in saved['samples'] if k.endswith('idle'))
    entry=next(c for c in payload['clips'] if c['base'].split('.')[-1]==key)
    for retarget in ('False','True','MissingPrivateLayer'):
        sample=saved['samples'][key]['True' if retarget=='MissingPrivateLayer' else retarget][0]
        effective=entry if retarget!='MissingPrivateLayer' else dict(tracks=[])
        p=native_pose(rig,data,applied({n:matrix(v) for n,v in sample['local'].items()},effective,0.))
        result['evaluated'][retarget]=geometry(rig,p,meshes)
    report[side]=result
    print('SAVED_COMPARISON',side,'mechanical_profile_diffs',len(diffs),'cylinder_axis_degrees',
        {mode:row['WPN_Cylinder']['angle'] for mode,row in result['evaluated'].items()},flush=True)
(O/'diagnosis_saved.json').write_text(json.dumps(report,indent=2))
