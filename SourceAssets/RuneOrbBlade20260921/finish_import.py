import unreal, json
from pathlib import Path
project=str(unreal.Paths.project_dir())
if str(Path(project).resolve()).replace('\\','/').lower() != 'd:/fps3d/fpsgame':
    raise RuntimeError('Wrong editor project: '+project)
dest='/Game/Weapons/RuneOrbBlade20260921'
report={'project':project,'meshes':{}}
for name in ('SM_RuneOrbBlade','SM_RuneBladeShard'):
    mesh=unreal.load_asset(dest+'/'+name)
    if mesh is None: raise RuntimeError('Missing imported '+name)
    report['meshes'][name]={'path':mesh.get_path_name(),'bounds':str(mesh.get_bounds()),'slots':[str(s.material_slot_name) for s in mesh.static_materials],'triangles':mesh.get_num_triangles(0)}
for cls, props in [('RuneOrbBladesComponent',{'BladeMesh':'SM_RuneOrbBlade'}),('RuneOrbBlade',{'ShardMesh':'SM_RuneBladeShard','ShardMaterial':'M_RuneBlade_Shards'})]:
    typ=unreal.load_class(None,'/Script/FPSGAME.'+cls)
    if not typ: continue
    obj=unreal.get_default_object(typ)
    for prop,asset in props.items():
        try:
            obj.set_editor_property(prop,unreal.load_asset(dest+'/'+asset))
            report[cls+'.'+prop]='refreshed'
        except Exception as e:
            report[cls+'.'+prop]='native rebuild/restart required: '+str(e)
Path('D:/FPS3D/FPSGAME/SourceAssets/RuneOrbBlade20260921/import-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('RUNE_IMPORT_COMPLETE '+json.dumps(report))
