"""Read existing PIE instances only; never start/stop play or change actors."""
import unreal as u,json
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessStaffReview20261009')
report={'started_game':False,'actors_modified':False,'characters':{}}
def path(v):return v.get_path_name() if v else None
def fields(o,names):
    out={}
    for n in names:
        try:
            v=o.get_editor_property(n);out[n]=path(v) if isinstance(v,u.Object) else str(v) if not isinstance(v,(float,int,bool,str)) else v
        except Exception as e:out[n]={'unavailable':str(e)}
    return out
worlds=u.EditorLevelLibrary.get_pie_worlds(False)
for who in ['Security','Receptionist']:
    bp=u.load_asset('/Game/Monsters/Faceless'+who+'/BP_Faceless'+who);cls=bp.generated_class();cdo=u.get_default_object(cls)
    sk=cdo.get_editor_property('visual_mesh').get_editor_property('skeleton')
    row={'compatible_skeletons':[str(v) for v in sk.get_editor_property('compatible_skeletons')],'instances':[]}
    for world in worlds:
        for actor in u.GameplayStatics.get_all_actors_of_class(world,cls):
            combat=actor.get_editor_property('combat');knock=actor.get_editor_property('knockdown');mesh=actor.get_editor_property('mesh');anim=mesh.get_anim_instance()
            row['instances'].append({'actor':path(actor),'state':fields(actor,['state']),
                'knockdown':fields(knock,['enabled','fall_clip','get_up_clip','prone_get_up_clip']),
                'combat':fields(combat,['hit_clip','dizzy_clip']),
                'anim_class':path(anim.get_class()) if anim else None,
                'animation':fields(anim,['current_asset']) if anim else None,
                'current_FR4_sum':sum(anim.get_curve_value(m.get_name()) for m in mesh.get_skeletal_mesh_asset().get_editor_property('morph_targets')) if anim and who=='Receptionist' else None})
    report['characters'][who]=row
(OUT/'existing_pie_snapshot.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M03_M04_EXISTING_PIE_READ '+json.dumps(report))