import bpy,json,math
from pathlib import Path
OUT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMReplacement')
contract=json.loads((OUT/'akm_replacement_export_report.json').read_text())
original={};checks=[]
changed={'WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Muzzle','WPN_SOCKET_Eject','WPN_Trigger'}
unchanged=[c for c in contract['clips']if c['source']=='unchanged source action']
def use(rig,act,f):
    rig.animation_data.action=act;rig.animation_data.action_slot=act.slots[0]
    bpy.context.scene.frame_set(f);bpy.context.view_layer.update()
def matrices(rig):
    return {b.name:b.matrix.copy()for b in rig.pose.bones if b.name not in changed}
bpy.ops.wm.open_mainfile(filepath=r'D:\FPS3D\FPSGAME\SourceAssets\AKM\SK_AKM_Viewmodel_Source.blend')
rig=bpy.data.objects['SK_AKM_Viewmodel']
for clip in unchanged:
    act=bpy.data.actions[clip['action']]
    frames=sorted({clip['start'],clip['end'],(clip['start']+clip['end'])//2})
    for f in frames:use(rig,act,f);original[(clip['clip'],f)]=matrices(rig)
bpy.ops.wm.open_mainfile(filepath=str(OUT/'SK_AKM_Replacement_Source.blend'))
rig=bpy.data.objects['SK_AKM_Viewmodel'];maximum=0
for (clip,f),expected in original.items():
    use(rig,bpy.data.actions['AKM_'+clip],f)
    for n,m in matrices(rig).items():maximum=max(maximum,max(abs(m[i][j]-expected[n][i][j])for i in range(4)for j in range(4)))
assert maximum<.0001,maximum
checks.append({'name':'unchanged action transforms across sampled frames','max_matrix_deviation':maximum,'sample_count':len(original)})
meshes=[o for o in bpy.data.objects if o.type=='MESH' and o.parent==rig and not o.hide_render]
assert any(o.name.startswith('SK_ArmsReplacement_WRAD')for o in meshes),'New arms not integrated'
assert not any(o.name.startswith('SK_FP_CH_Default_Cubic')for o in meshes),'Old cube arms remain'
max_dimension=0;pose_samples=0
for clip in contract['clips']:
    act=bpy.data.actions[clip['action']]
    for f in sorted({clip['start'],clip['end'],(clip['start']+clip['end'])//2}):
        use(rig,act,f);deps=bpy.context.evaluated_depsgraph_get()
        for o in meshes:
            e=o.evaluated_get(deps);m=e.to_mesh();pts=[e.matrix_world@v.co for v in m.vertices];e.to_mesh_clear()
            assert all(math.isfinite(v)for p in pts for v in p),o.name
            extent=max(max(p[i]for p in pts)-min(p[i]for p in pts)for i in range(3));max_dimension=max(max_dimension,extent)
            assert extent<2.0,(o.name,clip['clip'],f,extent)
        pose_samples+=1
checks.append({'name':'finite evaluated meshes and plausible scale','samples':pose_samples,'max_mesh_extent_m':max_dimension})
for clip in ['fire','aim_fire']:
    act=bpy.data.actions['AKMR_'+clip];use(rig,act,1)
    stable={n:rig.pose.bones[n].matrix.copy()for n in ['WPN_root','hand_l','hand_r']}
    travel=[]
    for f in range(1,14):
        use(rig,act,f);travel.append(rig.pose.bones['WPN_bolt'].location.y)
        for n,m in stable.items():assert max(abs(m[i][j]-rig.pose.bones[n].matrix[i][j])for i in range(4)for j in range(4))<.0001
    assert abs(travel[-1]-travel[0])<.0001
    checks.append({'name':clip+' stable hands/root and closed bolt endpoints','bolt_travel_cm':max(travel)-min(travel),'duration_s':.1})
report={'passed':True,'checks':checks,'scope':'Blender source actions, evaluated candidate geometry and binding; UE runtime acceptance separate'}
(OUT/'akm_replacement_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('AKM_REPLACEMENT_VALIDATION_OK '+json.dumps(report))
