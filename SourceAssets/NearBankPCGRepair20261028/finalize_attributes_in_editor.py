"""Save instance data through the existing editor without changing its active world."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,math,collections,re,shutil
R=Path(__file__).resolve().parent;PROJECT=R.parents[1]
MAP='/Game/GameMaps/L_CyberpunkApartment';OWNER='CyberpunkApartment.NearBankNativePCG20261028'
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);game=ed.get_game_world()
if game:raise RuntimeError('Preserve active game; use isolated or background publication')
if game and any(a.actor_has_tag(OWNER) for a in u.GameplayStatics.get_all_actors_of_class(game,u.Actor)):
    raise RuntimeError('Native district is in the active game; preserve active scene')
if any(p.get_path_name()==MAP for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()):raise RuntimeError('Preserve unsaved apartment')
runpy.run_path(str(R/'attach_native_attributes.py'),run_name='__main__')
manifest=json.loads((R/'publish_manifest.json').read_text());groups=collections.defaultdict(lambda:collections.defaultdict(list))
for row in manifest['rows']:
    key=(row['mesh'],tuple(row['materials']))
    for t in row['transforms']:
        groups[(math.floor(t['p'][0]/20000),math.floor(t['p'][1]/20000))][key].append(t)
assets=json.loads((R/'publish_assets.json').read_text());bylabel={r['label']:r for r in assets['blocks']}
E=u.EditorAssetLibrary;S=u.get_engine_subsystem(u.SubobjectDataSubsystem);F=u.SubobjectDataBlueprintFunctionLibrary
plans={};saved=[]
backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')/'MaterialAttributes';backup.mkdir(parents=True,exist_ok=True)
shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
for (cx,cy),batch in sorted(groups.items()):
    label=f'NBPCG_NativeBlock_{cx+20:02d}_{cy+20:02d}';bp=u.load_asset(bylabel[label]['path']);items={}
    for i,((mesh,mats),transforms) in enumerate(sorted(batch.items())):
        stride=max(len(t.get('custom',[])) for t in transforms)
        items[f'NativeMesh_{i:03d}']=dict(mesh=mesh,count=len(transforms),stride=stride,data=[v for t in transforms for v in (t.get('custom',[])+[0.0]*stride)[:stride]])
    plans[label]=items
    for h in S.k2_gather_subobject_data_for_blueprint(bp):
        name=str(F.get_variable_name(F.get_data(h)));p=items.get(name)
        if not p:continue
        c=F.get_object(F.get_data(h))
        if c.get_instance_count()!=p['count'] or c.static_mesh.get_path_name()!=p['mesh']:raise RuntimeError('Generated component changed '+label+'/'+name)
        c.modify();c.set_num_custom_data_floats(p['stride'])
        if p['stride']:c.set_editor_property('per_instance_sm_custom_data',p['data'])
    if not u.BlueprintEditorLibrary.compile_blueprint(bp):raise RuntimeError('Cannot save instance template '+label)
    if not u.EditorLoadingAndSavingUtils.save_packages([bp.get_outer()],False):raise RuntimeError('Cannot save instance template '+label)
    saved.append(label)
    print('NATIVE_TEMPLATE_ATTRIBUTES_SAVED',label,flush=True)
world=u.load_asset(MAP)
if not world or world==game:raise RuntimeError('Cannot open inactive apartment asset')
changed=0
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    items=plans.get(a.get_actor_label())
    if not items:continue
    if not a.actor_has_tag(OWNER):raise RuntimeError('Unexpected actor owner')
    for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
        match=re.search(r'NativeMesh_\d+',c.get_name());p=items.get(match.group(0)) if match else None
        if not p:continue
        if c.get_instance_count()!=p['count'] or c.static_mesh.get_path_name()!=p['mesh']:raise RuntimeError('Saved actor component changed '+a.get_actor_label()+'/'+c.get_name())
        c.modify();c.set_num_custom_data_floats(p['stride'])
        if p['stride']:c.set_editor_property('per_instance_sm_custom_data',p['data'])
        changed+=1
    a.modify()
if not changed:raise RuntimeError('Inactive map actor components unavailable; templates remain saved')
if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Cannot save inactive apartment')
d=json.loads((R/'installed.json').read_text());d.update(native_material_attributes_preserved=True,attribute_components_saved=changed,active_game_preserved=game.get_path_name() if game else None,saved_at=datetime.now().astimezone().isoformat());(R/'installed.json').write_text(json.dumps(d,indent=2),encoding='utf8')
print('NATIVE_ATTRIBUTES_SAVED_TO_INACTIVE_MAP',changed,len(saved),flush=True)
