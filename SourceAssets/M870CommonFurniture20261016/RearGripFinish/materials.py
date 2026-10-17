"""Private M870 instances of the existing SUPER90 static rear-grip finish."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P=O.parent;D='/Game/Weapons/M870/CommonFurniture20261016/Materials'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
S='/Game/Weapons/Super90/RearGrips20261012/Materials'
F=json.loads((O/'finish.json').read_text())
METAL=json.loads((P.parent/'M870CommonOptics20261016/finish.json').read_text())
R={'saved':[],'source':'SUPER90 rear-grip WS1; M870 native neck PBR samples','finish':F,'completed':False}
def clone(source,target):
    obj=u.load_asset(target) if E.does_asset_exist(target) else E.duplicate_asset(source,target)
    if not obj:raise RuntimeError('Missing '+source)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    R['saved'].append(obj.get_path_name())
def scalars(mi,values):
    for key,value in values.items():L.set_material_instance_scalar_parameter_value(mi,key,value)
def vectors(mi,values):
    for key,value in values.items():L.set_material_instance_vector_parameter_value(mi,key,u.LinearColor(*value,1))
for key in ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'):
    mat=clone(S+'/MI_S90_'+key,D+'/MI_M870_'+key)
    # Existing vertex region mask and donor packed roughness stay intact. The
    # continuous neck fit changes UV density, so scale grain by the new surface.
    row=json.loads((O/'authoring.json').read_text())[key]
    stable=key=='stable_antislip_reargrip';coat=F if stable else METAL
    scalars(mat,{'Roughness':coat['Roughness'][0],'Metallic':coat['Metalic'][0],'PolymerRoughness':F['Roughness'][0],'BeadScale':row['bead_scale'],'WeaponWetness':0})
    vectors(mat,{'FinishColor':coat['base_color_linear'],'PolymerColor':F['base_color_linear']})
    L.update_material_instance(mat);save(mat)
transition=clone(S+'/MI_S90_RearGrip_Transition',D+'/MI_M870_RearGripTransition')
scalars(transition,{'Metallic':0,'Roughness':max(.5,F['Roughness'][0]),'UseVertexMetalMask':0,'UseDonorRoughness':0,'SourceRoughnessWeight':0,'BeadScale':10})
vectors(transition,{'FinishColor':F['base_color_linear'],'PolymerColor':F['base_color_linear']});L.update_material_instance(transition);save(transition)
src='/Game/Weapons/M870/Tactical20261015/Materials/M_M870_OriginalSurface'
native=clone(src,D+'/M_M870_RearGripNativeContact')
# This private native-atlas copy is consumed only by rigid furniture.
native.set_editor_property('automatically_set_usage_in_editor',False)
for prop in ('used_with_skeletal_mesh','used_with_clothing','used_with_morph_targets'):native.set_editor_property(prop,False)
L.recompile_material(native);save(native)
R['completed']=True;(O/'material_receipt.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('M870_REAR_MATERIALS_SAVED',len(R['saved']),flush=True)
