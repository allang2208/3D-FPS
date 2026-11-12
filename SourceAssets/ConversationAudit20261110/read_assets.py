"""Read-only completion check for this conversation's saved character/optic assets."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ConversationAudit20261110'
def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
def path(obj):
    return obj.get_path_name() if obj else None
def lookup(value, selector):
    for key in selector:
        value = value[key]
    return value

report = {}
config = read('Content/ColdSteelData/modular_outfits.json')
published = read('SourceAssets/ST6FemaleCollar20261108/published.json')
saved = read('SourceAssets/ST6FemaleCollar20261108/saved_assets.json')
routes = [lookup(config, selector) for selector in published['owned_paths']]
expected = set(published['mesh_map'].values())
meshes = []
for target in sorted(expected):
    mesh = u.load_asset(target)
    meshes.append(dict(path=target, loaded=bool(mesh), lods=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(mesh) if mesh else 0))
report['st6'] = dict(routes=len(routes), current_unique=len(set(routes)), routes_match=all(p in expected for p in routes),
                     saved_completed=saved.get('completed'), meshes=meshes)
report['mantis'] = {}
for bp in ['/Game/Monsters/MantisM27/BP_MantisM27', '/Game/Monsters/MantisM27/ClawV17/BP_MantisM27_ClawReviewV17']:
    cls = u.EditorAssetLibrary.load_blueprint_class(bp)
    cdo = u.get_default_object(cls) if cls else None
    props = ['left_slash_clip','right_slash_clip','pounce_windup_clip','pounce_flight_clip','pounce_land_clip']
    report['mantis'][bp] = {p:path(cdo.get_editor_property(p)) for p in props} if cdo else None

def find_option(value):
    if isinstance(value,dict):
        if value.get('id') == 'highland_peakwatch_3_6x':
            return value
        for key, child in value.items():
            if key == 'highland_peakwatch_3_6x':
                return child
            result = find_option(child)
            if result is not None:
                return result
    elif isinstance(value,list):
        for child in value:
            result = find_option(child)
            if result is not None:
                return result
    return None
report['peakwatch_option'] = find_option(read('Content/ColdSteelData/bow-gunsmith.json'))
report['peakwatch_assets'] = {}
for target in ['/Game/Weapons/WoodSteelLongbow20261026/Scope3to6V12/SM_Highland_Peakwatch3to6',
               '/Game/Weapons/SharedPhysicalOptics20261030/M_PhysicalScopeLens',
               '/Game/ColdSteelData/AttachmentIcons20260913/FramedBows/bow_woodsteel_sight_highland_peakwatch_3_6x']:
    asset=u.load_asset(target)
    report['peakwatch_assets'][target]=dict(loaded=bool(asset),class_name=asset.get_class().get_name() if asset else None)
(OUT/'assets-readback.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('CONVERSATION_ASSETS_READBACK_COMPLETE')
