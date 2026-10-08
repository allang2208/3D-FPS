"""Read the actual loaded guard and charge state; never modify gameplay."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
def path(o): return o.get_path_name() if o else None
def prop(o,k):
    try:return str(o.get_editor_property(k))
    except Exception as e:return 'unavailable: '+str(e)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
out={'world':path(world),'actors':[]}
if world:
    pawn=u.GameplayStatics.get_player_pawn(world,0)
    if pawn:
        actor={'pawn':path(pawn),'effects':[],'guards':[]}
        for c in pawn.get_components_by_class(u.ActorComponent):
            if c.get_class().get_name()=='PanChiGuardComponent':
                actor['effects'].append({'component':path(c),**{k:prop(c,k) for k in ['StoredCharges','ChargesEnd','ReadyAt','GuardMaterial','GuardMID']}})
        for c in pawn.get_components_by_class(u.StaticMeshComponent):
            if not c.component_has_tag('SwordSlot=guard'):continue
            mesh=c.static_mesh
            overlay=c.get_overlay_material()
            row={'component':path(c),'mesh':path(mesh),'parent':path(c.get_attach_parent()),'visible':c.is_visible(),'hidden':prop(c,'hidden_in_game'),
                 'overlay':path(overlay),'bounds':str(c.get_local_bounds()),'overlay_distance':c.get_overlay_material_max_draw_distance(),
                 'transform':str(c.get_component_transform()),'materials':[]}
            if isinstance(overlay,u.MaterialInstanceDynamic):
                row['parameters']={key:overlay.k2_get_scalar_parameter_value(key) for key in ['Stacks','Ready']}
            for i in range(c.get_num_materials()):row['materials'].append({'slot':i,'base':path(c.get_material(i)),'overlay':path(c.get_overlay_material(True,i))})
            actor['guards'].append(row)
        out['actors'].append(actor)
m=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/PanChiEffects20261006/M_PanChiGuardGlow')
out['material']={'path':path(m),**{k:prop(m,k) for k in ['blend_mode','shading_model','two_sided','disable_depth_test','usage_flag_warnings']}}
guard=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/PanChiGuard20261006/Meshes/SM_XuanChi_Guard_PanChiZhanYue_V1')
out['guard_asset']={'bounds':str(guard.get_bounding_box()),'materials':str(guard.static_materials),'nanite':prop(guard,'nanite_settings')}
(P/'glow-diagnosis-20261007.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
