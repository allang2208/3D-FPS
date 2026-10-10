"""Save isolated Wizard/Jason retarget inputs; never edit the imported pack."""
import importlib.util
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ThirdPersonWizardDrink20261010'
DEST='/Game/Characters/JasonPlayer20261003/WizardDrink20261010'
lib=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('WIZARD_RETARGET_REQUIRES_END_PLAY')
source=u.load_asset('/Game/BattleWizardPBR/Meshes/WizardSM')
target=u.load_asset(cfg['body_mesh'])
clip=u.load_asset('/Game/BattleWizardPBR/Animations/PotionDrinkAnim')

def save(asset):
    if not lib.save_loaded_asset(asset,False): raise RuntimeError('Save failed '+asset.get_path_name())

def create(name,kind,factory):
    if lib.does_asset_exist(DEST+'/Rig/'+name): raise RuntimeError('Keep existing authoring asset '+name)
    return assets.create_asset(name,DEST+'/Rig',kind,factory)

def rig(name,mesh,jason):
    asset=create(name,u.IKRigDefinition,u.IKRigDefinitionFactory())
    c=u.IKRigController.get_controller(asset);c.set_skeletal_mesh(mesh);c.set_retarget_root('pelvis')
    chains={'Spine':('spine_01','spine_05' if jason else 'spine_03'),
        'Neck':('neck_01','neck_02' if jason else 'neck_01'),'Head':('head','head')}
    for side in ('l','r'):
        for label,a,b in [('Clavicle','clavicle','clavicle'),('Arm','upperarm','hand'),('Leg','thigh','foot'),('Toe','ball','ball')]:
            chains[label+'_'+side]=(a+'_'+side,b+'_'+side)
    # Wizard uses a simplified hand. Existing V7-derived fingers remain the
    # final gameplay grip, so no missing donor finger chains are synthesized.
    for label,(a,b) in chains.items(): c.add_retarget_chain(label,a,b,'')
    save(asset);return asset

src=rig('IK_Wizard_Drink',source,False);dst=rig('IK_Jason_Drink',target,True)
retarget=create('RTG_Wizard_Jason_Drink',u.IKRetargeter,u.IKRetargetFactory())
c=u.IKRetargeterController.get_controller(retarget)
c.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,src);c.set_ik_rig(u.RetargetSourceOrTarget.TARGET,dst)
c.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source);c.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
c.add_default_ops();c.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose=c.create_retarget_pose('Jason_Wizard_Aligned',u.RetargetSourceOrTarget.TARGET)
c.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET);c.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET);save(retarget)
inputs=u.IKRetargetBatchOperationInputs()
inputs.assets_to_retarget=[lib.find_asset_data(clip.get_path_name())]
inputs.source_mesh=source;inputs.target_mesh=target;inputs.ik_retarget_asset=retarget
inputs.prefix='J_';inputs.target_path=DEST+'/Donor';inputs.include_referenced_assets=False;inputs.overwrite_existing_files=False
donor=next(d.get_asset() for d in u.IKRetargetBatchOperation.run_batch_retarget(inputs) if isinstance(d.get_asset(),u.AnimSequence))
save(donor)
spec=importlib.util.spec_from_file_location('wizard_read',ROOT/'Tools/PlayerBody/read_wizard_drink20261010.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
data=json.loads((OUT/'inputs.json').read_text())
data['source']=reader.read(source.get_path_name(),{'drink':clip.get_path_name()},True)
native=reader.read(target.get_path_name(),{'drink':donor.get_path_name()},True)
native['clips'].update(data['target']['clips']);data['target']=native
data['retarget_asset']=retarget.get_path_name()
(OUT/'inputs.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('WIZARD_RETARGET_SAVED',donor.get_path_name())
