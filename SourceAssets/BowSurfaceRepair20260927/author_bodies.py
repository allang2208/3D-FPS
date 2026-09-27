"""Correct retained bow winding, preserving every vertex, bone, weight and UV."""
import bpy,bmesh,json,hashlib
from pathlib import Path
P=Path(__file__).parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'BowFlex20260927/Bow_ElasticBodies.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['Armature']
def contract(obj):
    return {'positions':[list(v.co) for v in obj.data.vertices],
            'weights':[[[g.group,g.weight] for g in v.groups] for v in obj.data.vertices],
            'bones':[[b.name,b.parent.name if b.parent else '',[list(r) for r in b.matrix_local]] for b in rig.data.bones]}
records=[]
for role in ('Original','Swift','Heavy','Steady'):
    obj=bpy.data.objects['SK_Bow_Flex_'+role];obj.data=obj.data.copy()
    before=contract(obj)
    bm=bmesh.new();bm.from_mesh(obj.data);bm.faces.ensure_lookup_table();bm.normal_update()
    normals=[f.normal.copy() for f in bm.faces]
    volume_before=bm.calc_volume(signed=True)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update()
    flipped=sum(n.dot(f.normal)<-.9 for n,f in zip(normals,bm.faces))
    volume_after=bm.calc_volume(signed=True)
    bm.to_mesh(obj.data);bm.free()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    if obj.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
    obj.data.update()
    # Scoped diagnosis requested by the user: protect the existing animation contract.
    if contract(obj)!=before:raise RuntimeError('Surface repair changed geometry or rig: '+obj.name)
    rig.select_set(True);bpy.context.view_layer.objects.active=rig
    fbx=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False,
        use_tspace=True,mesh_smooth_type='FACE')
    records.append({'mesh':obj.name,'reoriented_faces':flipped,'volume_before':volume_before,'volume_after':volume_after,
                    'vertex_positions_weights_bones_unchanged':True,'sha256':hashlib.sha256(fbx.read_bytes()).hexdigest()})
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_ElasticBodies_Outward.blend'))
(P/'authoring.json').write_text(json.dumps({'assets':records,'rendered':False,'gameplay_tested':False},indent=2),encoding='utf8')
print('BOW_OUTWARD_SURFACES_AUTHORED',json.dumps(records))
