import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AA=u.get_editor_subsystem(u.EditorActorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
def vec(v):return [v.x,v.y,v.z]
def run():
    world=UE.get_editor_world()
    data={'world':world.get_path_name(),'play_running':bool(UE.get_game_world()),'actors':[],'materials':{}}
    for a in AA.get_all_level_actors():
        p=a.get_actor_location();label=a.get_actor_label();b,e=a.get_actor_bounds(False)
        if not (label.startswith('DGN_RS_') or (1700<b.x<5100 and -4800<b.y<-1750)):continue
        r=a.get_actor_rotation()
        row=dict(path=a.get_path_name(),label=label,location=vec(p),rotation=dict(pitch=r.pitch,yaw=r.yaw,roll=r.roll),scale=vec(a.get_actor_scale3d()),bounds=[vec(b),vec(e)],folder=str(a.get_folder_path()),components=[])
        for c in a.get_components_by_class(u.StaticMeshComponent):
            row['components'].append(dict(name=c.get_name(),mesh=c.static_mesh.get_path_name() if c.static_mesh else None,materials=[m.get_path_name() if m else None for m in c.get_materials()]))
            for m in c.get_materials():
                if not m or m.get_path_name() in data['materials']:continue
                mi=m;parent=mi.get_editor_property('parent') if isinstance(mi,u.MaterialInstanceConstant) else None
                material=parent if isinstance(parent,u.Material) else mi
                d={'parent':parent.get_path_name() if parent else None}
                if isinstance(material,u.Material):
                    for prop in ['blend_mode','tangent_space_normal','translucency_lighting_mode','dithered_lod_transition','two_sided']:
                        d[prop]=str(material.get_editor_property(prop))
                data['materials'][m.get_path_name()]=d
        data['actors'].append(row)
    (ROOT/'Receipts/scene-before.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print('DUNGEON_SOURCE_STATE',data['world'],'play',data['play_running'],'actors',len(data['actors']))
run()
