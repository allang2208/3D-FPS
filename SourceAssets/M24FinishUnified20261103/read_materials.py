"""Read the active M24 assembly's saved material slots and effective parameters."""
import unreal as u, json, hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
L=u.MaterialEditingLibrary
R={'meshes':{},'materials':{},'masters':{}}
root='/Game/Weapons/M24/'
paths={'body':root+'MotionMagazine20261027/SK_M24_MotionV9'}
for key in ['m24_custom_scope_6x','m24_factory_suppressor','m24_cheekrest']:
    paths[key]=root+'Surface20261027/SM_M24_'+key
paths['iron']=root+'MotionPolish20261027/SM_M24_m24_palma_iron'
paths['mag10']=root+'MotionMagazine20261027/SM_M24_m24_extended_mag_10'
for key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','eoth_holographic','kv_scope_4x','thermal_scope','lpvo_ring','thermal_selector']:
    paths[key]=root+'CommonOptics20261028/Meshes/SM_M24_'+key
paths['advanced']=root+'AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action'
for key in ['phantom_reargrip','stable_antislip_reargrip','balanced_reargrip']:
    paths[key]=root+'RearGrip20261029/Meshes/SM_M24_'+key
for key in ['ReceiverStock_Advanced','ReceiverStock_Native','AdvancedFront_ForIndependentGrip','PistolGrip_Default','PistolGrip_balanced','PistolGrip_phantom','PistolGrip_stable']:
    paths[key]=root+'ReceiverGripRebuild20261031/Meshes/SM_M24_'+key
for key in ['Base','LegA','LegB']:paths['Bipod_'+key]=root+'Bipod20261029/SM_M24_Bipod_'+key
def digest(a):
    path=a.get_path_name().split('.')[0]
    if not path.startswith('/Game/'):return None
    p=Path(u.Paths.project_content_dir())/(path[6:]+'.uasset')
    return hashlib.sha256(p.read_bytes()).hexdigest()
def material(m):
    path=m.get_path_name()
    if path in R['materials']:return
    base=m.get_base_material();bp=base.get_path_name()
    data={'master':bp,'sha256':digest(m),'parameters':{}}
    if isinstance(m,u.MaterialInstance):
        data['parent']=m.get_editor_property('parent').get_path_name()
        for kind in ['scalar','vector','texture']:
            values={}
            for name in getattr(L,'get_'+kind+'_parameter_names')(base):
                v=getattr(L,'get_material_instance_'+kind+'_parameter_value')(m,name)
                values[str(name)]=v.get_path_name() if isinstance(v,u.Object) else [v.r,v.g,v.b,v.a] if isinstance(v,u.LinearColor) else v
            data['parameters'][kind]=values
    R['materials'][path]=data
    if bp not in R['masters']:
        R['masters'][bp]={'sha256':digest(base),'blend':str(base.get_editor_property('blend_mode')),
          'skeletal':base.get_editor_property('used_with_skeletal_mesh'),'codes':[], 'parameters':[]}
        for n in L.get_material_expressions(base):
            if isinstance(n,u.MaterialExpressionCustom):R['masters'][bp]['codes'].append({'name':str(n.get_editor_property('description')),'code':n.get_editor_property('code'),'inputs':[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]})
            if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter,u.MaterialExpressionTextureSampleParameter2D)):
                R['masters'][bp]['parameters'].append(str(n.get_editor_property('parameter_name')))
for key,path in paths.items():
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing active assembly mesh '+path)
    slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
    R['meshes'][key]={'path':path,'sha256':digest(mesh),'slots':[]}
    for s in slots:
        m=s.material_interface
        R['meshes'][key]['slots'].append({'slot':str(s.material_slot_name),'material':m.get_path_name() if m else None})
        if m:material(m)
    print('M24_MATERIAL_READ',key,flush=True)
material(u.load_asset(root+'CarbonBolt20261029/Materials/MI_M24_CarbonBolt'))
(O/'materials_before.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('M24_MATERIAL_INVENTORY',len(R['meshes']),len(R['materials']),len(R['masters']),flush=True)
