"""Author always-evaluated blade sockets for the M27 damage sweeps."""
from pathlib import Path
import json
import unreal as u

def configure_contacts(mesh):
    # UE's socket arrays are protected from Python. The native authoring method
    # owns both the always-animated contact sockets and the 15-body physics fit.
    if not u.MantisM27Monster.prepare_physics(mesh):
        raise RuntimeError('M27 native contact/physics authoring failed.')

def finish():
    path='/Game/Monsters/MantisM27/ProductionV1/SK_MantisM27'
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            if u.find_object(None,path+'.SK_MantisM27'):
                raise RuntimeError('M27 is loaded during PIE; preserve the active package until PIE ends.')
            print('M27_CONTACT_TARGET_UNLOADED_USE_BACKGROUND',flush=True)
            return
    mesh=u.load_asset(path); configure_contacts(mesh)
    for asset in [mesh.get_editor_property('physics_asset'),mesh]:
        if not u.EditorAssetLibrary.save_loaded_asset(asset,False): raise RuntimeError('M27 contact/physics asset did not save.')
    receipt=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/ProductionV1/ue_production_receipt.json')
    report=json.loads(receipt.read_text(encoding='utf-8')); report['blade_sockets_force_animation']=True
    receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M27_BLADE_SOCKETS_SAVED',flush=True)

if __name__=='__main__': finish()
