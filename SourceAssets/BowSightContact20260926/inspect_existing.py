import json
from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/Saved/BowSightContact20260926');out.mkdir(parents=True,exist_ok=True)
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
p=u.GameplayStatics.get_player_character(w,0) if w else None
result={'world':w.get_path_name() if w else None,'components':[]}
def xyz(v):return [v.x,v.y,v.z]
if p:
    for c in p.get_components_by_class(u.SceneComponent):
        name=c.get_name()
        if 'Bow' not in name and 'ModularOutfit' not in str(c.component_tags) and not (isinstance(c,u.SkeletalMeshComponent) and c.is_visible()):continue
        row={'name':name,'class':c.get_class().get_name(),'visible':c.is_visible(),'parent':c.get_attach_parent().get_name() if c.get_attach_parent() else None,
             'location':xyz(c.get_editor_property('relative_location')),'scale':xyz(c.get_editor_property('relative_scale3d'))}
        if isinstance(c,u.SkeletalMeshComponent):
            m=c.get_skeletal_mesh_asset();row['mesh']=m.get_path_name() if m else None
            row['materials']=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]
            try:row['shown']=[c.is_material_section_shown(i,0) for i in range(c.get_num_materials())]
            except Exception as e:row['shown_error']=str(e)
            row['sockets']={n:xyz(c.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT).translation) for n in ['bow_grip','bow_nock','hand_l','hand_r','lowerarm_l','lowerarm_r'] if c.does_socket_exist(n)}
        result['components'].append(row)
result['assets']={}
for path in ['/Game/Weapons/DarkBow20260925/ContactV9/SK_Bow_BareArmsV7','/Game/Weapons/DarkBow20260925/ArmsV4/Outfits/SK_Bow_HuntFieldGloves']:
    m=u.load_asset(path)
    if m:result['assets'][path]={'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in m.materials]}
(out/'existing.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
