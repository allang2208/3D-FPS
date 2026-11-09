"""Read current M249 feed meshes, effective materials and graph semantics."""
import unreal as u, json, hashlib
from pathlib import Path
r=Path(__file__).resolve().parent
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
out={'meshes':{},'materials':{},'textures':{},'graphs':{},'hashes':{},'live':[]}
def path(a): return a.get_path_name() if a else None
def record(a):
    p=path(a).split('.')[0]
    f=Path(u.Paths.project_content_dir())/(p.removeprefix('/Game/')+'.uasset')
    if f.exists():out['hashes'][p]=hashlib.sha256(f.read_bytes()).hexdigest()
def material(a):
    if not a or path(a) in out['materials']:return
    record(a);m=a.get_base_material();record(m)
    row={'base':path(m),'type':a.get_class().get_name()}
    if isinstance(a,u.MaterialInstanceConstant):
        row.update(parent=path(a.parent),scalars={str(n):L.get_material_instance_scalar_parameter_value(a,n) for n in L.get_scalar_parameter_names(a)},vectors={str(n):list(L.get_material_instance_vector_parameter_value(a,n).to_tuple()) for n in L.get_vector_parameter_names(a)},textures={str(n):path(L.get_material_instance_texture_parameter_value(a,n)) for n in L.get_texture_parameter_names(a)})
        for t in row['textures'].values():
            if not t or t in out['textures']:continue
            tex=u.load_asset(t);record(tex)
            out['textures'][t]={'srgb':bool(tex.get_editor_property('srgb')),'compression':str(tex.get_editor_property('compression_settings'))}
    out['materials'][path(a)]=row
    if path(m) not in out['graphs']:
        out['graphs'][path(m)]={'usage':{k:bool(m.get_editor_property(k)) for k in ('used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing','automatically_set_usage_in_editor')},'blend':str(m.get_editor_property('blend_mode')),'customs':[{'name':str(n.get_editor_property('description')),'code':n.get_editor_property('code')} for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)]}
targets=['/Game/Weapons/M249/SK_M249_V7']+['/Game/Weapons/M249/SideMagazine20261108/Meshes/'+n for n in ('SM_m249_side_mag_30','SM_m249_side_mag_45','SM_M249_SidePort')]
for p in E.list_assets('/Game/Weapons/M249',True,False):
    name=p.rsplit('/',1)[-1].split('.')[0]
    if name.lower()=='sm_m249_box':targets.append(p)
for p in sorted(set(targets)):
    a=u.load_asset(p);record(a)
    slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
    out['meshes'][path(a)]=[{'slot':str(s.material_slot_name),'material':path(s.material_interface)} for s in slots]
    for s in slots:
        if not isinstance(a,u.SkeletalMesh) or str(s.material_slot_name).startswith('M249_'):material(s.material_interface)
for p in ('/Game/Weapons/M249/Surface20261108/Materials/MI_M249_CommonRail','/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanPolymer','/Game/Weapons/WeaponSurface/Presets/MI_WS_CleanSatinSteel','/Game/Weapons/M249/SideMagazine20261108/Materials/MI_M249_SideMagazine'):
    a=u.load_asset(p)
    if a:material(a)
out['pie']=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
out['dirty_packages']=[x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if '/M249/' in x.get_name()]
world=u.EditorLevelLibrary.get_game_world()
if world:
    actor=u.GameplayStatics.get_player_character(world,0)
    if actor:
        for c in actor.get_components_by_class(u.MeshComponent):
            mesh=c.get_editor_property('skeletal_mesh_asset') if isinstance(c,u.SkeletalMeshComponent) else c.static_mesh if isinstance(c,u.StaticMeshComponent) else None
            if mesh and '/M249/' in path(mesh):
                out['live'].append({'component':path(c),'mesh':path(mesh),'materials':[path(c.get_material(i)) for i in range(c.get_num_materials())]})
(r/'current.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('M249_FINISH29_READ',len(out['meshes']),len(out['materials']),'PIE',out['pie'],flush=True)
