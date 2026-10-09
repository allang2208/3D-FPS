"""Requested cap repair: inspect imported collision and existing component binding."""
import unreal as u,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V14')
hat=u.load_asset('/Game/Monsters/FacelessSecurity/Accessories/SM_SecurityServiceCap_V14')
bp=u.load_asset('/Game/Monsters/FacelessSecurity/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);ss=u.get_engine_subsystem(u.SubobjectDataSubsystem);lib=u.SubobjectDataBlueprintFunctionLibrary
rows=[]
for h in ss.k2_gather_subobject_data_for_blueprint(bp):
    obj=lib.get_object_for_blueprint(lib.get_data(h),bp)
    if isinstance(obj,u.SecurityHatComponent):
        tr=obj.get_editor_property('head_attachment_transform');loc=tr.translation;scale=tr.scale3d;q=tr.rotation
        rows.append({'mesh':obj.get_editor_property('static_mesh').get_path_name(),'head_bone':str(obj.get_editor_property('head_bone')),
                     'location_cm':[loc.x,loc.y,loc.z],'rotation_xyzw':[q.x,q.y,q.z,q.w],'scale':[scale.x,scale.y,scale.z]})
report={'hat':hat.get_path_name(),'convex_colliders':sm.get_convex_collision_count(hat),
        'materials':[s.material_interface.get_path_name() for s in hat.get_editor_property('static_materials')],
        'body':cdo.get_editor_property('visual_mesh').get_path_name(),'components':rows,'game_tested':False}
(R/'Diagnosis/saved_hat.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
expected=json.loads((R/'authoring_receipt.json').read_text(encoding='utf-8'))['head_attachment']['relative_location_cm']
if report['convex_colliders']!=2 or len(rows)!=1 or rows[0]['mesh']!=hat.get_path_name():raise RuntimeError('Hat collision/component mismatch')
if any(abs(a-b)>.0001 for a,b in zip(rows[0]['location_cm'],expected)):raise RuntimeError('Head attachment changed')
print('SECURITY_HAT_V14_INSPECTED '+json.dumps(report),flush=True)
