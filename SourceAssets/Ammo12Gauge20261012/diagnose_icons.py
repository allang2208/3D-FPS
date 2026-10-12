import unreal, json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME')
report={}
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=editor.get_game_world() or editor.get_editor_world()
report['world']=world.get_path_name() if world else None
report['subsystem_methods']=[s for s in dir(unreal) if 'subsystem' in s.lower() and ('get_' in s or 'Library' in s)]
try:
    gi=unreal.GameplayStatics.get_game_instance(world)
    models=[o for o in unreal.ObjectIterator(unreal.ColdSteelStatusModel) if not o.get_name().startswith('Default__')]
    report['model_paths']=[o.get_path_name() for o in models]
    model=models[0] if models else None
    report['game_instance']=gi.get_path_name() if gi else None
    report['model']=model.get_path_name() if model else None
    if model:
        cache=model.get_editor_property('ammo_icon_textures')
        report['loaded_icons']={str(k):{'path':v.get_path_name(),'width':v.blueprint_get_size_x(),'height':v.blueprint_get_size_y()} for k,v in cache.items() if v}
except Exception as e: report['cache_error']=str(e)
report['object_helpers']=[s for s in dir(unreal) if 'object' in s.lower() and ('iter' in s.lower() or 'get_' in s)]
report['widget_classes']=[s for s in dir(unreal) if s in ['ColdSteelAmmoWheel','WidgetBlueprintLibrary','ColdSteelHUDWidget']]
rows=json.loads((root/'Content/ColdSteelData/ammo_types.json').read_text(encoding='utf-8-sig'))['types']
report['direct_imports']=[]
for row in rows:
    if row['group']!='ammo_12g':continue
    path=root/'Content/ColdSteelData'/row['icon']
    texture=unreal.RenderingLibrary.import_file_as_texture2d(world,str(path))
    report['direct_imports'].append({'id':row['id'],'file':str(path),'loaded':bool(texture),
        'width':texture.blueprint_get_size_x() if texture else 0,'height':texture.blueprint_get_size_y() if texture else 0})
(root/'SourceAssets/Ammo12Gauge20261012/icon_diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('AMMO_ICON_DIAG '+json.dumps(report,ensure_ascii=False))
