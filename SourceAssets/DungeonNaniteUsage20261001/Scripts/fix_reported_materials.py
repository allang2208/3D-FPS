"""Persist Nanite usage only for the twelve materials in the user's warning list."""
import hashlib,json,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
for folder in ('Backup','Receipts'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
groups={
    '/Game/Props/SquareAltar20260922/Materials/':[
        'M_Altar_PolishedMolding','M_Altar_WhiteMarble','M_Altar_SatinGold','M_Altar_BlueSapphire'],
    '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopSculpt/Materials/':[
        'M_WSSculpt_Machined','M_WSSculpt_RubberGrip'],
    '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopDetail/Materials/':[
        'M_WSDetail_PaintRed','M_WSDetail_BareEdge','M_WSDetail_Whiteboard'],
    '/Game/Dungeons/AtmosphereV2/Services/Materials/':['M_Service_Hardware','M_Service_Gasket'],
    '/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopSurface/Materials/':['M_WSFinish_ExposedEdge'],
}
targets=[folder+name for folder,names in groups.items() for name in names]
materials=[]
for path in targets:
    material=u.load_asset(path)
    if not isinstance(material,u.Material):raise RuntimeError('Expected reported base material '+path)
    materials.append((path,material))
report=dict(stage='saving',materials=[],tests_run=False,map_check_run=False,editor_started=False)
receipt=ROOT/'Receipts/materials-saved.json'
for path,material in materials:
    source=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    relative=source.relative_to(PROJECT);backup=ROOT/'Backup'/relative
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
    before=bool(material.get_editor_property('used_with_nanite'))
    material.modify();material.set_editor_property('used_with_nanite',True)
    # Compile the required shader usage even if the editor already enabled it in memory.
    errors=u.MaterialEditingLibrary.recompile_material(material)
    if errors:raise RuntimeError('Material compile failed '+path+': '+str(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(material,False):raise RuntimeError('Material save failed '+path)
    report['materials'].append(dict(path=path,previous_loaded_nanite=before,used_with_nanite=True,
        saved=True,prior_file_sha256=digest,backup=str(backup)))
    receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
report['stage']='materials_saved'
receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('REPORTED_NANITE_MATERIALS_SAVED',len(report['materials']),flush=True)
