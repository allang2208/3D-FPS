import unreal as u, json
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Refinement20260922');out.mkdir(exist_ok=True)
mesh=u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')
pa=mesh.physics_asset
report={'physics':pa.get_path_name(),'bodies':[],'constraints':[], 'editor_game_world':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world())}
def prop(o,n):
    try:return o.get_editor_property(n)
    except Exception as e:return str(e)
for name in ['skeletal_body_setups','constraint_setup']:
    values=prop(pa,name)
    if isinstance(values,str):report[name]=values;continue
    for obj in values:
        entry={'name':obj.get_name()}
        if name=='skeletal_body_setups':
            entry['bone']=str(prop(obj,'bone_name'));entry['physics_type']=str(prop(obj,'physics_type'))
            agg=prop(obj,'agg_geom')
            entry['capsules']=str(prop(agg,'sphyl_elems'));entry['boxes']=str(prop(agg,'box_elems'))
            report['bodies'].append(entry)
        else:
            entry['instance']=str(prop(obj,'default_instance'));report['constraints'].append(entry)
report['cloth']=str(prop(mesh,'mesh_clothing_assets'))
report['mesh_bounds']=str(mesh.get_bounds())
report['dirty']=[p.get_path_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())]
(out/'ue_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
