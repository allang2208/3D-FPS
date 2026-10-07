"""Reconnect the canonical F6 Blueprint through the existing editor bridge."""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/BindingV2')
REPORT=ROOT/'ue_binding_receipt.json'
OWNER='/Game/Monsters/MantisM27'
BP_PATH=OWNER+'/BP_MantisM27'

def connect():
    report=json.loads(REPORT.read_text(encoding='utf-8'))
    try:
        if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
                print('M27_BINDING_V2_CONNECT_PENDING_PIE',flush=True)
                return
        if not report['assets_saved']:raise RuntimeError('BindingV2 asset import is incomplete.')
        u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([OWNER+'/BindingV2'],True)
        mesh=u.load_asset(report['mesh'])
        clips={role:u.load_asset(info['asset']) for role,info in report['clips'].items()}
        if not mesh or not all(clips.values()):raise RuntimeError('BindingV2 packages unavailable for connection.')
        bp=u.load_asset(BP_PATH)
        if not bp:raise RuntimeError('Existing M27 F6 Blueprint unavailable.')
        u.BlueprintEditorLibrary.compile_blueprint(bp)
        defaults=u.get_default_object(bp.generated_class())
        previous={'visual_mesh':str(defaults.get_editor_property('visual_mesh').get_path_name())}
        defaults.set_editor_property('visual_mesh',mesh)
        for prop,role in [('idle_clip','Idle'),('walk_clip','Walk'),('attack_clip','LeftSlash'),
                          ('left_slash_clip','LeftSlash'),('right_slash_clip','RightSlash'),('death_clip','Death')]:
            defaults.set_editor_property(prop,clips[role])
        component=defaults.get_editor_property('mesh')
        component.set_skeletal_mesh_asset(mesh)
        component.set_editor_property('override_materials',[])
        combat=defaults.get_editor_property('combat')
        combat.set_editor_property('hit_clip',clips['Hit']);combat.set_editor_property('dizzy_clip',clips['Dizzy'])
        knockdown=defaults.get_editor_property('knockdown')
        for prop,role in [('fall_clip','Fall'),('get_up_clip','GetUp'),('prone_get_up_clip','ProneGetUp')]:
            knockdown.set_editor_property(prop,clips[role])
        u.EditorAssetLibrary.set_metadata_tag(bp,'ProductionRevision','BindingV2; connected foot/scythe weights; user review pending')
        if not u.EditorAssetLibrary.save_loaded_asset(bp,False):raise RuntimeError('M27 canonical Blueprint save failed.')
        report.pop('connect_error',None)
        report.update(saved=True,blueprint_connected=True,blueprint=bp.get_path_name(),f6_entry='MantisM27',
                      previous_references=previous,stage='BindingV2 mesh, matching clips and canonical F6 Blueprint saved; no runtime test performed')
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('M27_BINDING_V2_CONNECTED_AND_SAVED '+str(REPORT),flush=True)
    except Exception as error:
        report['connect_error']=str(error)
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        raise

if __name__=='__main__':connect()
