"""2011-only surface parameters and catalog bindings used on reimport."""
from pathlib import Path
import json

O=Path(__file__).parent;P=O.parents[1]
D='/Game/Weapons/PitViper2011/SurfaceRefine20261003'
GRAIN=D+'/Textures/T_PV2011_QuietMachining_Grain'
BODY='/Game/Weapons/PitViper2011/Integrated20261002/Materials/'
WS_BASE='/Game/Weapons/WeaponSurface/Master/M_WeaponSurface'
GRIPS=('pistol_grip_granular','pistol_grip_diamond','pistol_grip_quickdot')
VIP_OLD='/Game/Weapons/PitViper2011/VipGrip20261002/Materials/M_PitViper2011_VipViperGrip'
VIP_NEW=D+'/Materials/M_PV2011_ViperQuiet'
MATERIAL_REMAP={VIP_OLD:VIP_NEW}
for part in GRIPS:
    MATERIAL_REMAP['/Game/Weapons/PistolGripSurface20260927/Materials/M_'+part]=D+'/Materials/M_PV2011_'+part
for kind in ('laser','flashlight'):
    MATERIAL_REMAP['/Game/Weapons/M1911/Tactical20260913/Materials/M_M1911_'+kind+'_Body']=D+'/Materials/M_PV2011_'+kind+'_Body'

def ws_parameters(path):
    p=path.split('.')[0]
    if p.startswith(BODY):
        name=p.removeprefix(BODY).removeprefix('MI_PitViper2011_')
        rough={'h_190':.38,'stell':.34,'Magazine_stell':.34,'copper':.24,'brass':.26,
               'polymer':.50,'Magazine_polymer':.50}[name]
        fine=.009 if name in ('h_190','stell','Magazine_stell') else .004 if name in ('copper','brass') else .010
    elif p.endswith('/MI_SI_2011_CleanAnodized'):rough=.38;fine=.009
    elif p.endswith('/MI_PitViper2011_VipChampagne'):rough=.38;fine=.004
    elif p.endswith('/MI_SI_GrayLaserMark'):rough=.66;fine=0.
    else:raise RuntimeError('Unexpected 2011 WS surface '+p)
    return {'Roughness':rough,'GrainTileCm':8.,'GrainRoughness':fine,'MottleRoughness':0.,
            'MottleColor':0.,'Stipple':0.,'ScratchAmount':0.,'HandlingPolish':0.}

def apply_ws(u,material):
    L=u.MaterialEditingLibrary
    for name,value in ws_parameters(material.get_path_name()).items():L.set_material_instance_scalar_parameter_value(material,name,value)
    tex=u.load_asset(GRAIN)
    if not tex:raise RuntimeError('Save 2011 microfinish texture before material parameters')
    L.set_material_instance_texture_parameter_value(material,'GrainTexture',tex)
    L.update_material_instance(material)

def augment_weapon(weapon):
    binding=weapon['pistol_grip_surface'];variants=binding.setdefault('variants',{})
    for part in GRIPS:
        variants.setdefault(part,{})['material']=D+'/Materials/M_PV2011_'+part
        variants[part].setdefault('mesh',binding['mesh'])
    variants['pit_viper_vip_scales']['material']=VIP_NEW
    return weapon

def publish_bindings():
    path=P/'Content/ColdSteelData/gunsmith.json';text=path.read_text(encoding='utf-8-sig')
    pos=text.index('"ue_pit_viper2011"',text.index('"weapons"'));start=text.rfind('{',0,pos)
    weapon,size=json.JSONDecoder().raw_decode(text[start:]);weapon=augment_weapon(weapon)
    result=text[:start]+json.dumps(weapon,ensure_ascii=False,indent=2)+text[start+size:]
    if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Preserve concurrent catalog changes')
    path.write_text(result,encoding='utf8')

def restore_saved(u):
    receipt=O/'import_receipt.json'
    if not receipt.exists() or json.loads(receipt.read_text(encoding='utf8')).get('status')!='imported_and_saved':return
    rows=json.loads((O/'Input/current.json').read_text(encoding='utf8'))
    for path,entry in rows['materials'].items():
        if path.startswith('/Game/Weapons/PitViper2011/') and entry['base'].split('.')[0]==WS_BASE:
            material=u.load_asset(path);apply_ws(u,material)
            if not u.EditorLoadingAndSavingUtils.save_packages([material.get_outermost()],False):raise RuntimeError('Cannot restore 2011 surface '+path)
    for path in rows['meshes']:
        mesh=u.load_asset(path)
        if not isinstance(mesh,u.StaticMesh):continue
        slots=list(mesh.static_materials);changed=False
        for i,slot in enumerate(slots):
            src=slot.material_interface.get_path_name().split('.')[0] if slot.material_interface else ''
            if src in MATERIAL_REMAP:
                slot.material_interface=u.load_asset(MATERIAL_REMAP[src]);slots[i]=slot;changed=True
        if changed:
            mesh.set_editor_property('static_materials',slots)
            if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Cannot restore 2011 attachment finish '+path)
    publish_bindings()
