"""Read the current editor and surface assets; no saved content changes."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];(ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if not ue:raise RuntimeError('No interactive editor subsystem')
w=ue.get_editor_world();g=ue.get_game_world()
out={'editor_world':w.get_path_name(),'game_world':g.get_path_name() if g else None,
     'dirty':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
     'geometry_api':str(u.GeometryScript_Primitives.append_rectangle_xy.__doc__),'materials':{}}
for path in ['/Game/Dungeons/AtmosphereV2/Materials/M_Concrete',
             '/Game/Dungeons/WallDamage20260923/Materials/MI_FabExposedBed',
             '/Game/Dungeons/WallDamage20260923/Materials/MI_FabBrokenConcrete']:
    m=u.load_asset(path);base=m.get_base_material()
    out['materials'][path]={'base':base.get_path_name(),'nanite_override':str(u.MaterialEditingLibrary.get_nanite_override_material(m)),
        'code':[e.get_editor_property('code') for e in u.MaterialEditingLibrary.get_material_expressions(base) if e.__class__.__name__=='MaterialExpressionCustom']}
(ROOT/'Receipts/context.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('WALL_REVIEW_CONTEXT',out['editor_world'],out['game_world'],'dirty',len(out['dirty']),out['geometry_api'],flush=True)
