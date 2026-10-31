import unreal as u,json
from pathlib import Path
R=Path(__file__).resolve().parent
L=u.MaterialEditingLibrary
s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
ed=s.get_editor_world();game=s.get_game_world()
data=json.loads((R.parent/'RefinementV2/Audit/after/components.json').read_text('utf8'))
paths=sorted({p for row in data['components'] for p in row['materials'] if p})
report=dict(editor_world=ed.get_path_name() if ed else None,game_world=game.get_path_name() if game else None,dirty_maps=[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],materials=[])
for p in paths:
    a=u.load_asset(p)
    if not a:continue
    row=dict(path=p,parents=[],textures=[])
    while isinstance(a,u.MaterialInstance):
        row['parents'].append(a.get_path_name());a=a.parent
    if not isinstance(a,u.Material):continue
    row['master']=a.get_path_name();row['two_sided']=a.get_editor_property('two_sided');row['blend_mode']=str(a.get_editor_property('blend_mode'))
    for n in L.get_material_expressions(a):
        if isinstance(n,u.MaterialExpressionTextureSample) and n.texture:
            t=n.texture;row['textures'].append(dict(path=t.get_path_name(),sampler=str(n.sampler_type),srgb=t.srgb,compression=str(t.compression_settings),width=t.blueprint_get_size_x(),height=t.blueprint_get_size_y()))
    row['normal_connected']=bool(L.get_material_property_input_node(a,u.MaterialProperty.MP_NORMAL))
    report['materials'].append(row)
(R/'material-source.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('BEDROOM_MATERIAL_SOURCE',len(report['materials']),report['editor_world'],report['game_world'],report['dirty_maps'])
