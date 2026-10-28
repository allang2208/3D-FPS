"""Read only: preserve the user's active Play session and report the narrow bow state."""
from pathlib import Path
import unreal as u
import json,os
P=Path(__file__).parent
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_game_world() if editor else None
def prop(obj,name):
    try:
        value=obj.get_editor_property(name)
        return value.get_path_name() if isinstance(value,u.Object) else str(value)
    except Exception as exc:return str(exc)
r={'pid':os.getpid(),'game_world':world.get_path_name() if world else None,'players':[]}
if world:
    cls=u.load_class(None,'/Script/FPSGAME.FPSGAMECharacter')
    for actor in u.GameplayStatics.get_all_actors_of_class(world,cls):
        row={'actor':actor.get_path_name(),'components':[]}
        for c in actor.get_components_by_class(u.ActorComponent):
            name=c.get_class().get_name()
            if name=='BowMountainEchoComponent':
                row['components'].append({'class':name,**{k:prop(c,k) for k in ['equipped_instance','stacks','hud_material','arrow_material']}})
            elif name=='BowCadenceComponent':
                row['components'].append({'class':name,'state':prop(c,'state')})
        r['players'].append(row)
for label,path in [('alpine','/Game/Weapons/WoodSteelLongbow20261026/MountainEchoAlpineV23/M_MountainEcho_AlpineHUD'),('cadence','/Game/Weapons/WoodSteelLongbow20261026/CadenceV1/M_Cadence_HUD')]:
    mat=u.load_asset(path)
    r[label]={'asset':mat.get_path_name() if mat else None}
    if mat:
        nodes=[x for x in u.MaterialEditingLibrary.get_material_expressions(mat) if isinstance(x,u.MaterialExpressionComponentMask)]
        r[label]['masks']=[{'name':n.get_name(),'input_names':[str(s) for s in u.MaterialEditingLibrary.get_material_expression_input_names(n)],
            'connected':[v.get_name() if v else None for v in u.MaterialEditingLibrary.get_inputs_for_material_expression(mat,n)]} for n in nodes]
(P/('runtime-'+str(os.getpid())+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print('RESONANCE_RUNTIME '+json.dumps(r,ensure_ascii=False))
