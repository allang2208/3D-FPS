"""Repair the active V7 impact in place; preserve rock, flight and low fire."""
import json, shutil, sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import API, LIB, ref, assignments, setdata
from build_fireball_flames import FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_slow_burn import smooth
E=u.EditorAssetLibrary
AUTHOR=u.DragonBreathAuthorLibrary if hasattr(u,'DragonBreathAuthorLibrary') else u.RainAssetEditor
u.RainAssetEditor=AUTHOR
OUT=ROOT/'SourceAssets/MeteorVisibilityRepair20261114'
DEST='/Game/Skills/FireMagic20260921/MeteorImpactReferenceV7'
N,A='Particles.NormalizedAge','Particles.Age'
H='clamp(sqrt(User.ImpactRadius/652.5),.85,1.25)'
VEC4='/Script/CoreUObject.Vector4f'

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    names=['NS_MeteorPressureV7','M_PressureRaysV7','T_MeteorPressureFieldsV7']
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(DEST+'/'+n for n in names):
        raise RuntimeError('Preserve unsaved meteor target')
    backup=OUT/'Before';backup.mkdir(exist_ok=True)
    for name in names:
        source=ROOT/'Content'/DEST.removeprefix('/Game/')/(name+'.uasset')
        target=backup/source.name
        if not target.exists():shutil.copy2(source,target)
    system=u.load_asset(DEST+'/NS_MeteorPressureV7')
    contract=json.loads((ROOT/'SourceAssets/MeteorImpactReferenceV7_20261114/Blast/atlas-manifest.json').read_text(encoding='utf8'))
    first,last=contract['playback_windows']['fire'];denominator=contract['frames']-1
    fire_age=f'(({first}+.35+({last-first}-.35)*pow({N},.72))/{denominator})'
    core_age=f'(({first}+.35+({last-first}*.55)*{N})/{denominator})'

    def update(en,values,life=None):
        assignments(system,en,'ParticleSpawnScript',dict(values,**({'Particles.Lifetime':(FLOAT,life)} if life else {})))
        assignments(system,en,'ParticleUpdateScript',values)

    assignments(system,'RefContactImpulse','ParticleSpawnScript',{'Particles.Lifetime':(FLOAT,'.14')})
    update('RefRadialPressureFan',{
        'Particles.SpriteSize':(VEC2,f'float2(720,430)*{H}*(.65+.35*(1-exp(-{A}*42)))'),
        'Particles.Position':(POSITION,'User.LocalUp*18'),
        'Particles.Color':(COLOR,f'float4(1,.82,.52,.88*(1-{smooth(.20,1,N)}))')},'.32')
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,'RefRadialPressureFan',renderer=0),
            {'PivotInUVSpace':{'X':.5,'Y':.90}})
    update('RefWhiteHotCore',{'Particles.DynamicMaterialParameter':(VEC4,f'float4({core_age},0,2.5*(1-{N})+.5,0)')},'.26')
    update('RefPressureFireCrown',{'Particles.DynamicMaterialParameter':(VEC4,f'float4({fire_age},0,1.45-.8*{N},0)')})
    material=u.load_asset(DEST+'/M_PressureRaysV7')
    for node in LIB.get_material_expressions(material):
        if isinstance(node,u.MaterialExpressionCustom) and node.get_editor_property('description')=='MeteorV7.Shape':
            node.set_editor_property('code',(ROOT/'Tools/Skills/meteor_reference_v7_rays.hlsl').read_text(encoding='utf8'))
    texture=u.load_asset(DEST+'/T_MeteorPressureFieldsV7')
    E.set_metadata_tag(texture,'Meteor.AtlasContract',json.dumps(contract))
    E.set_metadata_tag(system,'Meteor.VisibilityRepair','20261114: separate fire frames 0..9.65 from smoke; ground-rooted 320 ms fan')
    from meteor_renderer_bindings import bind_impact_attributes
    bind_impact_attributes(system)
    if not AUTHOR.compile_material_assets([material]):raise RuntimeError('Pressure fan material compile failed')
    if not AUTHOR.compile_rain(system,True):raise RuntimeError('Meteor Niagara compile failed')
    saved=[]
    for asset in [material,texture,system]:
        if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
        saved.append(asset.get_path_name())
        print('METEOR_VISIBILITY_SAVED '+asset.get_path_name(),flush=True)
    receipt=dict(complete=True,saved_assets=saved,fire_source_window=[first,last],
        original_crown_reached_last_fire_frame_at_seconds=.07442759126183306,
        crown_lifetime_seconds=.82,contact_seconds=.14,radial_fan_seconds=.32,
        native_code_changed=False,runtime_path_changed=False,new_particles=0,new_lights=0,
        preserved=['rock and fragments','V6 mantle and trail','V4 low fire','gameplay values','sound','camera'],
        interactive_editor_opened=False,game_started=False,runtime_tested=False)
    (OUT/'repair-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('METEOR_VISIBILITY_REPAIR_COMPLETE',flush=True)

if __name__=='__main__':run()
