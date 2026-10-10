"""Wait for existing material shader jobs without editing assets or changing PIE."""
from pathlib import Path
from datetime import datetime
import json
import unreal as u
P=Path(__file__).resolve().parent
E=u.MaterialEditingLibrary
m=u.load_asset('/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit')
if not m:raise RuntimeError('Missing spirit material')
shader=next(n for n in E.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
if shader.get_editor_property('code')!=(P/'spirit_visible.hlsl').read_text(encoding='utf-8'):
    raise RuntimeError('Loaded material differs from the authored revision')
stats=E.get_statistics(m)
instructions=stats.get_editor_property('num_pixel_shader_instructions')
if instructions<=0:raise RuntimeError('No compiled pixel shader; inspect shader compiler output')
result={'material':m.get_path_name(),'time':datetime.now().isoformat(),
        'shader_compilation_finished':True,'pixel_shader_instructions':instructions,
        'existing_pie_preserved':True,'recompiled_or_saved_by_this_read':False,'blade_instances':[]}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=comp.get_editor_property('static_mesh')
            if not mesh or 'FrostSword_Blade' not in mesh.get_path_name():continue
            row={'component':comp.get_name(),'mesh':mesh.get_path_name(),'visible':comp.is_visible(),'materials':[]}
            for slot in range(comp.get_num_materials()):
                overlay=comp.get_overlay_material(True,slot)
                entry={'overlay':overlay.get_path_name() if overlay else None}
                if isinstance(overlay,u.MaterialInstanceDynamic):
                    entry['parameters']={k:overlay.get_scalar_parameter_value(k) for k in ['RuneMode','SpiritOpacity','SpiritRestOpacity','SpiritBrightness']}
                    entry['dimensions']=str(overlay.get_vector_parameter_value('Dimensions'))
                row['materials'].append(entry)
            result['blade_instances'].append(row)
(P/'loaded_material_build.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
receipt=json.loads((P/'install_receipt.json').read_text(encoding='utf-8'))
receipt.update(shader_compilation_finished=True,shader_build_result='loaded_material_build.json',pixel_shader_instructions=instructions)
(P/'install_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
