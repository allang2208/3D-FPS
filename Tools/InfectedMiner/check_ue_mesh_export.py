import bpy,json,numpy as np
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912')
def load(name):
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=str(R/'Delivery'/name),anim_offset=0.0)
    r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    result={'bones':{b.name:np.array(r.matrix_world@b.matrix_local) for b in r.data.bones},'meshes':{}}
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        result['meshes'][o.name]={'vertices':np.array([o.matrix_world@v.co for v in o.data.vertices]),'weights':[(v.index,o.vertex_groups[g.group].name,round(g.weight,6)) for v in o.data.vertices for g in v.groups]}
    return result
a=load('SK_InfectedMiner.fbx');b=load('SK_InfectedMiner_UE.fbx')
assert a['bones'].keys()==b['bones'].keys();assert a['meshes'].keys()==b['meshes'].keys()
err=max(float(np.max(np.abs(v-b['bones'][n]))) for n,v in a['bones'].items())
for n,m in a['meshes'].items():
    assert m['weights']==b['meshes'][n]['weights'],n
    err=max(err,float(np.max(np.abs(m['vertices']-b['meshes'][n]['vertices']))))
assert err<1e-5,err
report={'geometry_rest_max_error':err,'weights_unchanged':True,'bones':len(a['bones']),'mesh_vertices':{n:len(v['vertices']) for n,v in a['meshes'].items()},'change':'UE color layer selection only'}
(R/'Previews/FBX/ue-mesh-export-validation.json').write_text(json.dumps(report,indent=2));print('UE_COLOR_EXPORT_GEOMETRY_CHECK '+json.dumps(report))
