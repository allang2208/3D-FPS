"""Prepare a precise retirement plan; keep current inputs and production records."""
import json
from pathlib import Path
P=Path(__file__).resolve().parents[2];O=P/'SourceAssets/PitViper2011Publication20261003'
O.mkdir(exist_ok=True);entries={}
def add(file,reason,replacement):
    if not file.is_file():return
    path=file.resolve();relative=path.relative_to(P).as_posix()
    entries[relative]={'path':relative,'reason':reason,'replacement':replacement}
def folder(relative,reason,replacement):
    for file in sorted((P/relative).rglob('*')):add(file,reason,replacement)
for batch in sorted((P/'SourceAssets').glob('PitViper*')):
    if batch==O:continue
    for file in sorted(batch.rglob('*')):
        if any(n.startswith('Before') for n in file.relative_to(batch).parts):
            add(file,'Superseded pre-change snapshot; current sources and saved packages remain in their production locations',
                'Current '+batch.name+' authoring/import records; recoverable rollback remains in trash')
for batch in ('PitViper2011VipGrip20261002','PitViper2011GripRebuild20261003'):
    for component in ('Exports','Icons','Textures'):
        folder('SourceAssets/'+batch+'/'+component,'Rejected or superseded short grip skin / icon / texture output',
            'SourceAssets/PitViper2011ViperLongitudinalGrip20261003 for VIP; PitViper2011CommonLongitudinalGrips20261003 for shared skins')
for name in ('SM_PitViper2011_GripSurface.fbx','SM_PitViper2011_GripSurface_Editable.blend'):
    add(P/'SourceAssets/PitViper2011Attachments20261002/Exports'/name,
        'Initial narrow shared grip mesh superseded by longitudinal fitted skin',
        'SourceAssets/PitViper2011CommonLongitudinalGrips20261003/Exports/'+name)
folder('SourceAssets/PitViper2011SIChamfer20261003','Superseded upper-shoulder SI interface, replaced by native muzzle body extension',
    'SourceAssets/PitViper2011SIBodyExtension20261003 and Tools/Weapons/pit_viper_si_extension.py')
add(P/'Tools/Weapons/pit_viper_si_interface.py','Unused helper of the superseded upper-shoulder SI interface',
    'Tools/Weapons/pit_viper_si_extension.py')
add(P/'SourceAssets/PitViper2011GripRebuild20261003/author_grips.py','Short-skin producer now followed by two authoritative long-skin authors; replace with forwarding entry',
    'Current VIP and common longitudinal author_grip.py producers')
add(P/'SourceAssets/PitViper2011GripRebuild20261003/import_rebuilt.py','Broad legacy import entry recreated old surfaces and shared material setup; replace with the two current scoped save entries',
    'Current VIP import_assets.py and common import_grip.py')
for name in ('diagnose_source.py','source_diagnosis.json','asset_diagnosis.json','icon_source.json','icon_delivery.json'):
    add(P/'SourceAssets/PitViper2011GripRebuild20261003'/name,'Completed diagnosis or delivery record describes the retired short skin',
        'Current longitudinal authoring/import/icon receipts')
for name in ('icon_source.json','icon_delivery.json'):
    add(P/'SourceAssets/PitViper2011VipGrip20261002'/name,'Original short-skin icon record superseded by current long-skin icon',
        'SourceAssets/PitViper2011ViperLongitudinalGrip20261003/icon_delivery.json')
for kind in ('BaseColor','Normal','ORM'):
    add(P/'SourceAssets/PitViper2011SurfaceRefine20261003/Textures'/('T_PV2011_ViperQuiet_'+kind+'.png'),
        'Old short-atlas VIP maps no longer used by the current texture recipe',
        'SourceAssets/PitViper2011ViperLongitudinalGrip20261003/Textures/T_PV2011_ViperQuiet_'+kind+'.png')
folder('SourceAssets/PitViper2011FireAudio20261002/History','Superseded normal-shot processing versions; retained loudness reference has moved to Inputs',
    'Current Audio/Masters plus Inputs/SuppressedLoudnessReference_float.wav')
add(P/'SourceAssets/PitViper2011Integration20261002/prepare_authoring_recipe.py',
    'Initial code generator would overwrite the adopted authoring recipe and later fire changes',
    'SourceAssets/PitViper2011Integration20261002/author_pit_viper.py')
external=Path('C:/Users/allan/.codex/generated_images/01a0fb54-2e91-7602-9a0b-39b3c5c8d00f/exec-2424a719-30b1-4362-b54f-5df8f58971ee.png')
if external.exists():
    entries['external/obsolete-long-grip-card.png']={'path':str(external),'destination_relative':'external/obsolete-long-grip-card.png',
        'reason':'First longitudinal card included a lower projecting foot rejected by the user magazine-boundary correction',
        'replacement':'SourceAssets/PitViper2011ViperLongitudinalGrip20261003/Icons/ue_pit_viper2011_reargrip_pit_viper_vip_scales.png'}
plan={'archive_root':str(P/'trash/pit-viper2011-closeout-20261003'),'files':list(entries.values())}
(O/'archive-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
print('PIT_VIPER_RETIREMENT_PLAN',len(entries),'files',sum((Path(v['path']) if Path(v['path']).is_absolute() else P/v['path']).stat().st_size for v in entries.values()),'bytes')
