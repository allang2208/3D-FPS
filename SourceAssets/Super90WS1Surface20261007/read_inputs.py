"""Read active Super90 material bindings for the requested finish replacement."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
R='/Game/Weapons/Super90/Cransh20261006';mesh=u.load_asset(R+'/SK_Super90_V7')
master=u.load_asset('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface')
data={'pie_active':bool(u.EditorLevelLibrary.get_game_world()),'mesh':mesh.get_path_name(),'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.materials],
      'master':master.get_path_name(),'master_scalars':[str(n) for n in L.get_scalar_parameter_names(master)],'master_textures':[str(n) for n in L.get_texture_parameter_names(master)],'attachments':{}}
for root in ('Optics20261007','Foregrips20261007'):
    for path in E.list_assets('/Game/Weapons/Super90/'+root+'/Meshes',True,False):
        obj=u.load_asset(path)
        if isinstance(obj,u.StaticMesh):data['attachments'][obj.get_path_name()]=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in obj.static_materials]
(O/'inputs.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('SUPER90_WS1_INPUTS',json.dumps(data,ensure_ascii=False))
