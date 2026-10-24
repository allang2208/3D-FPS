"""Read saved Kaitlin assets in bounded, non-saving commandlet batches."""
import gc
import json
import math
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME'); W = P / 'SourceAssets/KaitlinPlayer20261023'; A = W / 'Audit'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
body = read(P / 'Content/ColdSteelData/player_body.json'); female = body['body_variants']['kaitlin']
plan = {}
for folder in ('WorldGarments', 'Backpacks'):
    saved = read(W / folder / 'saved_assets.json')
    for source, row in read(W / folder / 'manifest.json').items():
        plan[saved[source]] = {'kind': 'world', 'geometry': row['geometry']}
for source, target in read(W / 'ViewSkin/saved_assets.json').items():
    plan[target] = {'kind': 'view', 'source': source}
plan[female['body_mesh']] = {'kind': 'body'}
face = female['heads']['kaitlin']['mesh']
plan[face] = {'kind': 'face'}
for role, target in female['clips'].items():
    plan.setdefault(target, {'kind': 'animation', 'source': body['clips'][role], 'roles': []})['roles'].append(role)
for row in read(W / 'groom_recipes.json'):
    plan[row['binding']] = {'kind': 'binding', 'face': face, 'groom': row['asset']}
    plan[row['asset']] = {'kind': 'load'}
    for path in row.get('materials', []): plan[path] = {'kind': 'load'}
for recipe in female['head_equipment'].values():
    for key in ('mesh', 'skeletal_mesh', 'static_mesh'):
        if recipe.get(key): plan.setdefault(recipe[key], {'kind': 'load'})
result_path = A / 'assets.json'
report = read(result_path) if result_path.exists() else {'assets': {}, 'failures': []}
full = u.load_asset(read(W / 'full_body_receipt.json')['mesh'])
target_skeleton = full.skeleton
native_bones = read(W / 'NativeGeometry/MHC_Kaitlin_Body.json')['bones']
cloth_targets = set(read(W / 'robe_cloth_saved.json'))
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
G, B, Q, L = u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights, u.GeometryScript_MeshQueries, u.GeometryScript_List


def geometry(asset):
    dm, outcome = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('source LOD unreadable')
    return dm


def inspect(path, spec):
    asset = u.load_asset(path)
    if not asset: raise RuntimeError('load failed')
    row = {'kind': spec['kind'], 'class': asset.get_class().get_name(), 'errors': []}
    errors = row['errors']
    if spec['kind'] in ('world', 'view', 'body', 'face'):
        if not isinstance(asset, u.SkeletalMesh): raise RuntimeError('not a skeletal mesh')
        row['skeleton'] = asset.skeleton.get_path_name()
        row['lods'] = S.get_lod_count(asset)
        row['materials'] = [{'slot': str(m.material_slot_name), 'asset': m.material_interface.get_path_name() if m.material_interface else None} for m in asset.materials]
        if any(m['asset'] is None for m in row['materials']): errors.append('empty material')
        if spec['kind'] in ('world', 'body'):
            if asset.skeleton != target_skeleton: errors.append('wrong female skeleton')
            if row['lods'] != 3: errors.append('expected 3 LODs')
            dm = geometry(asset)
            _, bones = B.get_all_bones_info(dm)
            row['bones'] = len(bones)
            if [str(b.name) for b in bones] != [b['name'] for b in native_bones]: errors.append('bone order differs')
            else:
                delta = max((b.world_transform.translation-u.Vector(*n['position'])).length() for b,n in zip(bones,native_bones))
                row['bind_position_error_cm'] = delta
                if delta > .01: errors.append('male or incorrect bind proportions')
            _, positions, _ = Q.get_all_vertex_positions(dm, False)
            points = L.convert_vector_list_to_array(positions)
            row['vertices'] = len(points); row['triangles'] = dm.get_triangle_count()
            if not points or not all(math.isfinite(v) for p in points for v in (p.x,p.y,p.z)): errors.append('invalid geometry')
            if spec['kind'] == 'world':
                authored = read(Path(spec['geometry']))
                if len(points) != len(authored['positions']): errors.append('authored vertex count differs')
                else:
                    delta = max((p-u.Vector(*q)).length() for p,q in zip(points,authored['positions']))
                    row['authored_position_error_cm'] = delta
                    if delta > .01: errors.append('saved positions differ from fit')
                if [m['slot'] for m in row['materials']] != [m['slot'] for m in authored['materials']]: errors.append('material slot order differs')
            else:
                expected = read(W / 'Body/segmented_body.json')
                if [m['slot'] for m in row['materials']] != [m['slot'] for m in expected['materials']]: errors.append('body coverage slot order differs')
                if row['vertices'] != 30455: errors.append('incomplete female body')
                actual_ids = [u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(dm.get_triangle_count())]
                if actual_ids != expected['triangle_materials']: errors.append('body coverage triangles differ')
            row['cloth_assets'] = [c.get_path_name() for c in asset.get_editor_property('mesh_clothing_assets')]
            if path in cloth_targets and len(row['cloth_assets']) != 1: errors.append('robe cloth not bound')
            if path in cloth_targets:
                for cloth in asset.get_editor_property('mesh_clothing_assets'):
                    physics = cloth.get_editor_property('physics_asset')
                    if not physics: errors.append('robe collision missing')
                    else:
                        # The owning array is not exposed to Python; the saved
                        # instanced setup objects still expose their geometry.
                        setups = [s for s in u.ObjectIterator(u.Object)
                                  if s.get_outer()==physics and s.get_class().get_name()=='SkeletalBodySetup']
                        count = sum(len(s.get_editor_property('agg_geom').get_editor_property('sphyl_elems')) for s in setups)
                        row['cloth_collision_capsules'] = count
                        if count != len(read(W/'robe_collision.json')['capsules']): errors.append('female robe collision count differs')
            if spec['kind']=='body' or path in cloth_targets:
                row['render_triangles'] = []
                for lod in range(row['lods']):
                    render, outcome = G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=lod))
                    count = render.get_triangle_count()
                    row['render_triangles'].append(count)
                    if outcome!=u.GeometryScriptOutcomePins.SUCCESS or not count: errors.append('empty render LOD '+str(lod))
        elif spec['kind'] == 'view':
            source = u.load_asset(spec['source'])
            if source.skeleton != asset.skeleton: errors.append('view skeleton changed')
            row['morphs'] = sorted(m.get_name() for m in asset.get_editor_property('morph_targets'))
            if row['morphs'] != sorted(m.get_name() for m in source.get_editor_property('morph_targets')): errors.append('view corrective morphs changed')
            if any('/SkinV9/' in (m['asset'] or '') for m in row['materials']): errors.append('male view skin retained')
        elif spec['kind'] == 'face':
            dm = geometry(asset); _, bones = B.get_all_bones_info(dm)
            positions = {str(b.name):b.world_transform.translation for b in bones}
            # Native MetaHuman face retains unweighted lower-spine archetype
            # joints. CopyPose replaces that complete chain; only weighted
            # shared joints and the neck/head attachment must agree in bind.
            _, vectors, _ = Q.get_all_vertex_positions(dm,False)
            used = set()
            for vertex in range(len(L.convert_vector_list_to_array(vectors))):
                _, weights, valid = B.get_vertex_bone_weights(dm,vertex)
                if not valid: errors.append('face weights missing'); break
                used.update(w.bone_index for w in weights if w.weight>0)
            common = {str(b.name) for b in bones if b.index in used} & {b['name'] for b in native_bones}
            common.update(('spine_04','spine_05','neck_01','neck_02','head'))
            deltas = {b['name']:(positions[b['name']]-u.Vector(*b['position'])).length() for b in native_bones if b['name'] in common and b['name'] in positions}
            row['body_chain_bind_errors_cm'] = deltas
            if len(deltas)!=len(common) or max(deltas.values(),default=0)>.01: errors.append('face/body bind chain mismatch')
    elif spec['kind'] == 'animation':
        if not isinstance(asset, u.AnimSequence): raise RuntimeError('not an animation')
        source = u.load_asset(spec['source'])
        row['source'] = spec['source']; row['roles'] = spec['roles']
        row['skeleton'] = asset.get_editor_property('skeleton').get_path_name()
        if asset.get_editor_property('skeleton') != target_skeleton: errors.append('wrong animation skeleton')
        for key in ('sequence_length', 'rate_scale', 'enable_root_motion', 'force_root_lock', 'root_motion_root_lock'):
            actual, expected = asset.get_editor_property(key), source.get_editor_property(key)
            row[key] = str(actual)
            if actual != expected: errors.append(key + ' differs from source')
        names = lambda a: [str(n) for n in u.AnimationLibrary.get_animation_notify_event_names(a)]
        row['notifies'] = names(asset)
        if names(asset) != names(source): errors.append('notify names differ')
        length = asset.get_editor_property('sequence_length')
        names = ['root','pelvis','spine_05','head','hand_l','hand_r','foot_l','foot_r']
        for fraction in (0,.25,.5,.75,1):
            poses = u.AnimationLibrary.get_bone_poses_for_time(asset,names,length*fraction,False)
            if len(poses) != len(names): errors.append('missing sampled bone pose')
            if not all(math.isfinite(v) for p in poses for v in (p.translation.x,p.translation.y,p.translation.z,p.rotation.x,p.rotation.y,p.rotation.z,p.rotation.w)):
                errors.append('non-finite sampled pose')
    elif spec['kind'] == 'binding':
        for key, expected in [('target_skeletal_mesh',spec['face']), ('groom',spec['groom'])]:
            value = asset.get_editor_property(key)
            row[key] = value.get_path_name() if value else None
            if row[key] != expected: errors.append('wrong '+key)
    return row


count = 0
for path, spec in plan.items():
    if path in report['assets']: continue
    try: row = inspect(path, spec)
    except Exception as exc: row = {'kind': spec['kind'], 'errors': [str(exc)]}
    report['assets'][path] = row
    if row['errors']: report['failures'].append({'asset': path, 'errors': row['errors']})
    result_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('KAITLIN_ASSET_READ',len(report['assets']),len(plan),path,'ERRORS',row['errors'],flush=True)
    gc.collect(); u.SystemLibrary.collect_garbage()
    count += 1
    if count >= 32: break
remaining = sum(path not in report['assets'] for path in plan)
report['complete'] = remaining == 0
report['passed'] = report['complete'] and not report['failures']
result_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
(W / 'audit_assets_status.json').write_text(json.dumps({'remaining':remaining,'complete':remaining==0}),encoding='utf-8')
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world,'Editor.AsyncAssetCompilationFinishAll')
print('KAITLIN_ASSET_AUDIT_BATCH',remaining,'remaining;',len(report['failures']),'failures',flush=True)
