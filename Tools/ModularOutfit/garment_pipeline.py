"""File-side candidate contracts and fail-closed publication for new sleeves.

The gate consumes saved UE mesh snapshots, never author-space substitutes.
Run with Python 3.11 (numpy). UE production lives in garment_ue.py.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
LIBRARY = PROJECT / 'SourceAssets/GarmentFoundation20260929/library.json'
TYPES = {'short_fitted', 'long_thick', 'loose'}
ACTION_GROUPS = ['idle_ads', 'reload', 'equip_inspect', 'sprint', 'melee', 'traversal', 'casting']

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def asset_file(path):
    package = path.split('.')[0]
    if not package.startswith('/Game/') or '..' in package.split('/'):
        raise ValueError('Expected a project asset: ' + path)
    return PROJECT / 'Content' / (package[6:] + '.uasset')

def fingerprint(manifest):
    # Evidence is invalidated by any contract, candidate, action or asset change.
    copy = {k:v for k,v in manifest.items() if k not in ('evidence', 'publication')}
    assets = {k:digest(asset_file(v['asset'])) for k,v in manifest['candidates'].items()}
    for profile,candidate in manifest['candidates'].items():
        if candidate.get('native_source'):assets['native:'+profile]=digest(asset_file(candidate['native_source']))
    for groups in manifest['actions'].values():
        for clips in groups.values():
            for clip in clips:assets[clip]=digest(asset_file(clip))
    return hashlib.sha256(json.dumps([copy, assets], sort_keys=True).encode()).hexdigest()

def mesh_issues(d, limits):
    import numpy as np
    issues = []; p = np.asarray(d['positions'], float); f = np.asarray(d['triangles'], int)
    if p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all():
        return ['nonfinite_or_invalid_positions']
    if f.ndim != 2 or f.shape[1] != 3 or f.min(initial=0)<0 or f.max(initial=0)>=len(p):
        return ['invalid_triangle_indices']
    if len(d['weights']) != len(p):return ['weight_vertex_count']
    if not len(f):return ['empty_mesh']
    area = np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]), axis=1)*.5
    if np.any(area < 1e-10):issues.append('degenerate_faces')
    edge = np.linalg.norm(p[f]-p[np.roll(f,1,axis=1)],axis=2)
    if edge.max() > limits['max_rest_edge_cm']:issues.append('oversized_rest_edge')
    seen = set(); duplicates = 0
    for face in f:
        key = tuple(sorted(tuple(np.round(p[v],5)) for v in face))
        if key in seen:duplicates+=1
        seen.add(key)
    if duplicates:issues.append('coincident_duplicate_faces:' + str(duplicates))
    for i,weights in enumerate(d['weights']):
        if not weights or any(not math.isfinite(v) or v<0 for v in weights.values()) or abs(sum(weights.values())-1)>.002:
            issues.append('invalid_weights:'+str(i));break
        if not set(weights).issubset(d['rest']):issues.append('unknown_weight_bone:'+str(i));break
        left=sum(v for n,v in weights.items() if n.endswith('_l'))
        right=sum(v for n,v in weights.items() if n.endswith('_r'))
        if min(left,right)>.05:issues.append('cross_arm_weights:'+str(i));break
    return issues

def init(path, kind, template, profiles, item):
    if Path(path).exists():raise RuntimeError('Candidate manifest already exists')
    library=read(LIBRARY); entry=library['templates'][template]
    if entry['status']!='structural_baseline':raise RuntimeError('Unusable template')
    if kind not in TYPES:raise ValueError(kind)
    config=read(PROJECT/'Content/ColdSteelData/modular_outfits.json')
    old=config['items'].get(item, {})
    known={v['rig_profile'] for v in config['profiles'].values()}
    if not set(profiles).issubset(known):raise RuntimeError('Unknown target profile')
    if 'Body' in profiles:raise RuntimeError('World-body garment requires its own full-body authoring pipeline')
    write(path, dict(version=1,item=item,kind=kind,template=template,
        template_asset=entry['asset'],template_sha256=digest(asset_file(entry['asset'])),
        thickness_cm=None,minimum_clearance_cm=None,wrist_overlap_cm=None,
        shoulder_opening='open_to_torso',hem='inner_outer_rim',
        layer_contract=[],physics_contract=None,expected_profiles=profiles,
        previous={p:old.get('rig_meshes',{}).get(p) for p in profiles},
        local_corrections={p:[] for p in profiles},
        native_fit_review={p:None for p in profiles},
        coverage={'first_person':None,'world':None},glove_combinations=[],
        actions={p:{group:[] for group in ACTION_GROUPS} for p in profiles},
        not_applicable={p:{} for p in profiles},
        limits={'max_rest_edge_cm':4.,'max_rest_edge_by_lod_cm':[4.,6.,6.],'max_posed_edge_cm':8.,'max_edge_stretch':5.},
        candidates={},evidence={}))

def gate(path):
    m=read(path); errors=[]; snapshots={}
    for k in ('thickness_cm','minimum_clearance_cm','wrist_overlap_cm'):
        if not isinstance(m.get(k),(int,float)) or not math.isfinite(m[k]) or m[k]<0:errors.append('missing_dimension:'+k)
    if not m.get('layer_contract'):errors.append('missing_layer_correspondence')
    if m['kind']=='loose' and not m.get('physics_contract'):errors.append('loose_requires_motion_contract')
    if m['coverage']['first_person'] is None or m['coverage']['world'] is None:errors.append('missing_coverage')
    if not m.get('glove_combinations'):errors.append('missing_glove_combinations')
    if set(m['candidates']) != set(m['expected_profiles']):errors.append('incomplete_profile_set')
    if digest(asset_file(m['template_asset']))!=m['template_sha256']:errors.append('template_changed')
    for profile in m['expected_profiles']:
        if not m.get('native_fit_review',{}).get(profile):errors.append('pending_native_fit_review:'+profile)
        for group in ACTION_GROUPS:
            clips=m['actions'][profile].get(group,[])
            reason=m['not_applicable'][profile].get(group)
            if not clips and not reason:errors.append('uncovered_action:'+profile+':'+group)
            for clip in clips:
                if not asset_file(clip).exists():errors.append('missing_clip:'+clip)
        candidate=m['candidates'].get(profile)
        if not candidate:continue
        if candidate.get('local_corrections')!=m['local_corrections'][profile]:errors.append('unapplied_local_corrections:'+profile)
        file=asset_file(candidate['asset'])
        if not file.exists():errors.append('missing_asset:'+profile);continue
        if digest(file)!=candidate.get('asset_sha256'):errors.append('asset_changed:'+profile)
        for lod in range(3):
            ref=candidate.get('snapshots',{}).get(str(lod))
            if not ref:errors.append('missing_saved_lod:'+profile+':'+str(lod));continue
            snap=Path(ref['path'])
            if not snap.is_file() or digest(snap)!=ref['sha256']:errors.append('snapshot_changed:'+profile);continue
            d=read(snap)
            if d.get('source')!=candidate['asset'] or d.get('asset_sha256')!=candidate['asset_sha256'] or d.get('lod')!=lod:
                errors.append('snapshot_not_of_candidate:'+profile);continue
            limits=dict(m['limits']);limits['max_rest_edge_cm']=limits.get('max_rest_edge_by_lod_cm',[limits['max_rest_edge_cm']]*3)[lod]
            issues=mesh_issues(d,limits);errors.extend(profile+':LOD'+str(lod)+':'+x for x in issues)
            snapshots[profile+':'+str(lod)]=dict(vertices=len(d['positions']),triangles=len(d['triangles']),issues=issues)
    stamp=fingerprint(m) if set(m['candidates'])==set(m['expected_profiles']) else None
    # Visual/clearance observations must be tied to this exact saved candidate.
    for stage in ('motion','layer_clearance','runtime_visual'):
        record=m.get('evidence',{}).get(stage)
        if not record:errors.append('pending:'+stage);continue
        evidence_path=Path(record['path'])
        if not evidence_path.is_file() or digest(evidence_path)!=record['sha256']:
            errors.append('evidence_changed:'+stage);continue
        evidence=read(evidence_path)
        if evidence.get('fingerprint')!=stamp or evidence.get('status')!='pass':errors.append('evidence_not_pass:'+stage)
        required={(p,g,c) for p in m['expected_profiles'] for g,clips in m['actions'][p].items() for c in clips}
        covered={tuple(x) for x in evidence.get('covered_actions',[])}
        if not required.issubset(covered):errors.append('evidence_action_gaps:'+stage)
        if set(evidence.get('profiles',[]))!=set(m['expected_profiles']):errors.append('evidence_profile_gaps:'+stage)
        if stage=='motion':
            covered_lods={(r['profile'],r['group'],r['clip'],r['lod']) for r in evidence.get('rows',[]) if r.get('samples',0)>1}
            if not {(p,g,c,l) for p,g,c in required for l in range(3)}.issubset(covered_lods):errors.append('motion_lod_gaps')
            for row in evidence.get('rows',[]):
                if not all(math.isfinite(row.get(k,float('nan'))) for k in ('max_edge_cm','max_stretch')) or row['max_edge_cm']>m['limits']['max_posed_edge_cm'] or row['max_stretch']>m['limits']['max_edge_stretch']:errors.append('motion_threshold_failure');break
        if stage!='motion':
            if set(evidence.get('glove_combinations',[]))!=set(m['glove_combinations']):errors.append('evidence_glove_gaps:'+stage)
            if not evidence.get('observations') or not evidence.get('artifacts'):errors.append('missing_observations:'+stage)
            checks=['inner_outer_clearance','skin_clearance','cuff_overlap'] if stage=='layer_clearance' else ['camera_intrusion','ads_transition','lod_switch','runtime_deformation']
            if not all(evidence.get('checks',{}).get(k) is True for k in checks):errors.append('missing_required_checks:'+stage)
            for ref in evidence.get('artifacts',[]):
                if not Path(ref['path']).is_file() or digest(ref['path'])!=ref['sha256']:errors.append('artifact_changed:'+stage)
    result=dict(status='pass' if not errors else 'blocked',fingerprint=stamp,errors=errors,snapshots=snapshots)
    write(Path(path).with_suffix('.gate.json'),result);return result

def publish(path):
    m=read(path);result=gate(path)
    if result['status']!='pass':raise RuntimeError('Candidate not ready: '+', '.join(result['errors']))
    config_path=PROJECT/'Content/ColdSteelData/modular_outfits.json';raw=config_path.read_bytes();c=json.loads(raw.decode('utf-8-sig'))
    if m['item'] not in c['items']:raise RuntimeError('Create item and recipe through the item pipeline first')
    recipe=c['items'][m['item']];mapping=recipe['rig_meshes']
    for profile,candidate in m['candidates'].items():
        if mapping.get(profile)!=m['previous'][profile]:raise RuntimeError('Concurrent outfit edit:'+profile)
        if digest(asset_file(candidate['asset']))!=candidate['asset_sha256']:raise RuntimeError('Candidate changed')
        mapping[profile]=candidate['asset']
    recipe['covers']=m['coverage']['first_person'];recipe['world_covers']=m['coverage']['world']
    if config_path.read_bytes()!=raw:raise RuntimeError('Config changed during publication')
    Path(path).with_suffix('.config-before.json').write_bytes(raw);write(config_path,c)
    m['publication']={'fingerprint':result['fingerprint'],'assets':{k:v['asset'] for k,v in m['candidates'].items()}};write(path,m)

def review_template(path, stage, output):
    if Path(output).exists():raise RuntimeError('Review file already exists')
    m=read(path)
    checks=['inner_outer_clearance','skin_clearance','cuff_overlap'] if stage=='layer_clearance' else ['camera_intrusion','ads_transition','lod_switch','runtime_deformation']
    write(output,dict(status='pending',fingerprint=fingerprint(m),profiles=m['expected_profiles'],
        covered_actions=[],required_actions=[[p,g,c] for p in m['expected_profiles'] for g,clips in m['actions'][p].items() for c in clips],
        glove_combinations=[],required_glove_combinations=m['glove_combinations'],
        checks={k:False for k in checks},observations=[],artifacts=[]))

if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    create=sub.add_parser('init');create.add_argument('manifest');create.add_argument('--kind',choices=sorted(TYPES),required=True);create.add_argument('--template',required=True);create.add_argument('--profiles',nargs='+',required=True);create.add_argument('--item',required=True)
    for name in ('gate','publish'):
        p=sub.add_parser(name);p.add_argument('manifest')
    review=sub.add_parser('review-template');review.add_argument('manifest');review.add_argument('--stage',choices=['layer_clearance','runtime_visual'],required=True);review.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command=='init':init(args.manifest,args.kind,args.template,args.profiles,args.item)
    elif args.command=='gate':
        result=gate(args.manifest);print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['status']=='pass' else 2)
    elif args.command=='review-template':review_template(args.manifest,args.stage,args.output)
    else:publish(args.manifest)
