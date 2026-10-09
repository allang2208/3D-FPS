"""Read current M03 bindings and imported cap geometry/collision; no gameplay."""
import unreal as u,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurityReview20261009');R.mkdir(parents=True,exist_ok=True)
D='/Game/Monsters/FacelessSecurity';bp=u.load_asset(D+'/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh')
skeleton=mesh.get_editor_property('skeleton');physics=mesh.get_editor_property('physics_asset')
report={'mesh':mesh.get_path_name(),'skeleton':skeleton.get_path_name(),'physics':physics.get_path_name() if physics else None,
        'core_clips':{},'states':{},'hats':[],'pie_active':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),
        'game_tested':False}
def animation(a):return {'path':a.get_path_name() if a else None,'same_skeleton':a.get_editor_property('skeleton')==skeleton if a else False}
for n in ['idle','walk','attack']:report['core_clips'][n]=animation(cdo.get_editor_property(n+'_clip'))
for group,names in [('combat',['hit_clip','dizzy_clip']),('knockdown',['fall_clip','get_up_clip','prone_get_up_clip'])]:
    obj=cdo.get_editor_property(group)
    for n in names:report['states'][group+'.'+n]=animation(obj.get_editor_property(n))
ss=u.get_engine_subsystem(u.SubobjectDataSubsystem);lib=u.SubobjectDataBlueprintFunctionLibrary;sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
for h in ss.k2_gather_subobject_data_for_blueprint(bp):
    obj=lib.get_object_for_blueprint(lib.get_data(h),bp)
    if isinstance(obj,u.SecurityHatComponent):
        hat=obj.get_editor_property('static_mesh');tr=obj.get_editor_property('head_attachment_transform');p=tr.translation
        report['hats'].append({'mesh':hat.get_path_name() if hat else None,'head_bone':str(obj.get_editor_property('head_bone')),
            'location_cm':[p.x,p.y,p.z],
            'convex_colliders':len(hat.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('convex_elems')),
            'vertices_lod0':None if report['pie_active'] else sm.get_number_verts(hat,0),
            'vertex_count_note':'Editor vertex statistics unavailable during PIE' if report['pie_active'] else 'Editor static mesh statistics',
            'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in hat.get_editor_property('static_materials')]})
(R/'assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('SECURITY_REVIEW_ASSETS '+json.dumps(report))
