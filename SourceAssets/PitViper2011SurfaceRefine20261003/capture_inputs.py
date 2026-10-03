"""Read current 2011 production inputs for scoped surface editing."""
import json
from pathlib import Path
import unreal as u

O=Path(__file__).parent;P=O.parents[1];E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong project')
(O/'Input').mkdir(exist_ok=True)
result={'meshes':{},'materials':{},'graphs':{},'game_tested':False}
catalog=json.loads((P/'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8-sig'))
weapon=next(w for w in catalog['weapons'] if w['id']=='ue_pit_viper2011')
result['grip_binding']=weapon['pistol_grip_surface']
paths=['/Game/Weapons/PitViper2011/Integrated20261002/'+v for v in
       ('Single/SK_PitViper2011_Manny','Dual/r/SK_Dual_PitViper2011_r','Dual/l/SK_Dual_PitViper2011_l')]
for directory in ('Attachments20261002','VipGrip20261002','SICompensator20261003'):
    for path in E.list_assets('/Game/Weapons/PitViper2011/'+directory,True,False):
        if str(E.find_asset_data(path).asset_class_path.asset_name)=='StaticMesh':paths.append(path)

def describe(mat):
    path=mat.get_path_name()
    if path in result['materials']:return
    base=mat.get_base_material();bp=base.get_path_name();params={}
    for kind in ('scalar','vector','texture'):
        params[kind]={}
        for name in getattr(L,'get_'+kind+'_parameter_names')(base):
            prefix='get_material_instance_' if isinstance(mat,u.MaterialInstanceConstant) else 'get_material_default_'
            value=getattr(L,prefix+kind+'_parameter_value')(mat,name)
            params[kind][str(name)]=(value.get_path_name() if value else None) if kind=='texture' else [value.r,value.g,value.b,value.a] if kind=='vector' else value
    result['materials'][path]={'base':bp,'class':type(mat).__name__,'parameters':params}
    if bp in result['graphs']:return
    rows=[]
    for node in L.get_material_expressions(base):
        row={'name':node.get_name(),'class':node.get_class().get_name()}
        for name in ('description','code','parameter_name','default_value','r','const_a','const_b'):
            try:
                value=node.get_editor_property(name)
                row[name]=value if isinstance(value,(str,float,int,bool)) else str(value)
            except Exception:pass
        try:
            tex=node.get_editor_property('texture')
            if tex:row['texture']=tex.get_path_name()
        except Exception:pass
        rows.append(row)
    result['graphs'][bp]=rows

for path in paths:
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing current production mesh '+path)
    slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
    result['meshes'][mesh.get_path_name()]=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]
    for slot in slots:
        if slot.material_interface and slot.material_interface.get_path_name().startswith('/Game/Weapons/'):
            describe(slot.material_interface)
for part in ('pistol_grip_granular','pistol_grip_diamond','pistol_grip_quickdot'):
    describe(u.load_asset('/Game/Weapons/PistolGripSurface20260927/Materials/M_'+part))
(O/'Input/current.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print('PIT_VIPER_SURFACE_PRODUCTION_INPUTS_READ',len(result['meshes']),len(result['materials']),flush=True)
