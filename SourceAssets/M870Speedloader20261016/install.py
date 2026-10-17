"""Save the M870 speedloader assets (commandlet, UE closed).

1. SM_M870_LoaderGuide: the SUPER90 guide mesh (UVs, materials) with the fitted
   M870 vertex positions from guide.json.
2. A_M870_loader_{normal,empty}_{1..7}: new clips on the M870 skeleton (template
   A_M870_cycle duplicated, notifies/curves cleared, all 68 bone tracks written).
3. DA_M870_{vertical,canted,prism,angled}: the 14 loader layers appended; every
   existing entry kept as plain values (retained clips restored).
New assets only: an existing target that lacks this batch's tag is left untouched.
"""
import json, hashlib, shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent; P = O.parents[1]
E = u.EditorAssetLibrary; G = u.GeometryScript_AssetUtils; Q = u.GeometryScript_MeshQueries
ROOT = '/Game/Weapons/M870/Speedloader20261016'
TAG = 'M870Speedloader20261016'
TEMPLATE = '/Game/Weapons/M870/Tactical20261015/Animations/A_M870_cycle'
S90_GUIDE = '/Game/Weapons/Super90/Speedloader20261007/SM_Super90_LoaderGuide'
PROFILE = '/Game/Weapons/M870/CommonFurniture20261016/Profiles/DA_M870_'
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    # Short batch through the shared editor gate: never during PIE, never over unsaved edits.
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE active; no asset changed.')
    dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
             if p.get_name().startswith(('/Game/Weapons/M870/CommonFurniture20261016/Profiles/', '/Game/Weapons/M870/Speedloader20261016'))]
    if dirty: raise RuntimeError('Unsaved edits on targets; no asset changed: ' + str(dirty))
receipt = dict(completed=False, saved=[], runtime_tested=False)
def record(): (O / 'install_receipt.json').write_text(json.dumps(receipt, indent=2))
def file_of(path): return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
def save(asset):
    if not E.save_loaded_asset(asset, False): raise RuntimeError('Could not save ' + asset.get_path_name())
    receipt['saved'].append(asset.get_path_name()); record()
def ours(path):
    if not E.does_asset_exist(path): return None
    a = u.load_asset(path)
    if not E.get_metadata_tag(a, TAG): raise RuntimeError('Existing asset not from this batch; left untouched: ' + path)
    return a
def backup(path):
    src = file_of(path); dst = O / 'Before' / src.relative_to(P)
    if src.exists() and not dst.exists(): dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)


# 1. Guide
guide = json.loads((O / 'guide.json').read_text())
src = u.load_asset(S90_GUIDE)
dm, st = G.copy_mesh_from_static_mesh(src, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if st != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot read the SUPER90 guide')
if Q.get_vertex_count(dm) != len(guide['positions']): raise RuntimeError('Guide vertex count changed since read_inputs.py')
pl = u.GeometryScript_List.convert_array_to_vector_list([u.Vector(*p) for p in guide['positions']])
u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm, pl)
split = u.GeometryScriptSplitNormalsOptions(); split.set_editor_property('split_by_opening_angle', True); split.set_editor_property('opening_angle_deg', 35.)
u.GeometryScript_Normals.compute_split_normals(dm, split, u.GeometryScriptCalculateNormalsOptions())
guide_path = ROOT + '/SM_M870_LoaderGuide'
mesh = ours(guide_path)
if mesh is None:
    # Start from the SUPER90 guide asset itself: same materials, build and collision settings.
    if not E.duplicate_asset(S90_GUIDE, guide_path): raise RuntimeError('Cannot create ' + guide_path)
    mesh = u.load_asset(guide_path)
opts = u.GeometryScriptCopyMeshToAssetOptions(); opts.set_editor_property('enable_recompute_normals', False)
opts.set_editor_property('enable_recompute_tangents', True); opts.set_editor_property('replace_materials', False)
_, st = G.copy_mesh_to_static_mesh(dm, mesh, opts, u.GeometryScriptMeshWriteLOD())
if st != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot write the M870 guide')
E.set_metadata_tag(mesh, TAG, 'SUPER90 guide refitted to the M870 loading port (author_guide.py)')
save(mesh)
print('M870_LOADER_GUIDE_SAVED', guide_path, flush=True)

# 2. Clips
clips = json.loads((O / 'clips.json').read_text()); names = json.loads((O / 'inputs.json').read_text())['m870']['names']
for role, clip in clips.items():
    path = ROOT + '/Animations/A_M870_loader_' + role
    anim = ours(path)
    if anim is None:
        if not E.duplicate_asset(TEMPLATE, path): raise RuntimeError('Cannot create ' + path)
        anim = u.load_asset(path)
    u.AnimationLibrary.remove_all_animation_notify_tracks(anim)
    u.AnimationLibrary.remove_all_curve_data(anim)
    frames = clip['frames']; rows = clip['rows']
    ctrl = anim.get_editor_property('controller')
    ctrl.open_bracket('M870 speedloader ' + role, False)
    try:
        ctrl.set_frame_rate(u.FrameRate(60, 1), False)
        ctrl.set_number_of_frames(u.FrameNumber(frames), False)
        for bone in names:
            pos = [u.Vector(*r[bone][:3]) for r in rows]; rot = [u.Quat(*r[bone][3:7]) for r in rows]; scl = [u.Vector(*r[bone][7:10]) for r in rows]
            if not ctrl.set_bone_track_keys(bone, pos, rot, scl, False):
                ctrl.add_bone_curve(bone, False)
                if not ctrl.set_bone_track_keys(bone, pos, rot, scl, False): raise RuntimeError('Cannot write %s %s' % (role, bone))
    finally:
        ctrl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(anim): raise RuntimeError('Finalize failed ' + role)
    if abs(anim.get_play_length() - frames / 60.) > 1e-4: raise RuntimeError('Unexpected length ' + role)
    E.set_metadata_tag(anim, TAG, 'R27 SUPER90 loader on M870: own grip/pump, port offset, pump-rack empty tail (author_clips.py)')
    save(anim)
    print('M870_LOADER_CLIP_SAVED', role, frames, flush=True)

# 3. Foregrip layers
loader_bases = {ROOT + '/Animations/A_M870_loader_' + r for r in clips}
for family in ('vertical', 'canted', 'prism', 'angled'):
    path = PROFILE + family; asset = u.load_asset(path)
    if not asset: raise RuntimeError('Missing ' + path)
    payload = dict(family=str(asset.get_editor_property('family')), clips=[]); retained = {}
    for c in asset.get_editor_property('clips'):
        base = c.get_editor_property('base').get_path_name()
        if base.split('.')[0] in loader_bases: continue
        payload['clips'].append(dict(base=base, duration=float(c.get_editor_property('duration')),
            tracks=[dict(bone=str(t.get_editor_property('bone')), times=list(t.get_editor_property('times')),
                         values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')]))
        old = c.get_editor_property('retained')
        if old: retained[base] = old.get_path_name()
    new = json.loads((O / 'Profiles' / (family + '.json')).read_text())
    payload['clips'] += [dict(base=e['base'], duration=e['duration'], tracks=e['tracks']) for e in new['clips']]
    backup(path)
    if not asset.set_shared_clips_from_json(json.dumps(payload)): raise RuntimeError('Grip profile merge failed ' + family)
    if retained:
        entries = list(asset.get_editor_property('clips'))
        for i, entry in enumerate(entries):
            b = entry.get_editor_property('base').get_path_name()
            if b in retained: entry.set_editor_property('retained', u.load_asset(retained[b])); entries[i] = entry
        asset.set_editor_property('clips', entries)
    E.set_metadata_tag(asset, TAG, 'loader normal/empty 1-7 foregrip layers appended; existing entries retained')
    save(asset)
    print('M870_LOADER_PROFILE_SAVED', family, len(payload['clips']), flush=True)
receipt['completed'] = True; record()
print('M870_LOADER_INSTALL_COMPLETE', len(receipt['saved']), flush=True)
