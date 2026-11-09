"""Save corrected import-slot bindings and the two fitted left-hand reaches."""
from pathlib import Path
import unreal as u,json,runpy,pickle,hashlib
r=Path(__file__).resolve().parent
root=r.parent
E=u.EditorAssetLibrary
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE is running; preserve its session before saving M249 assets')
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith('/Game/Weapons/M249/')]
if dirty:raise RuntimeError('Preserve unsaved M249 packages '+str(dirty))
hashes=json.loads((r/'before_hashes.json').read_text())
owned=['SK_M249_V7.uasset','SM_M249_magnifier.uasset','A_M249_reload.uasset','A_M249_reload_empty.uasset']
for path,digest in hashes.items():
    if Path(path).name in owned and hashlib.sha256((root.parents[1]/path).read_bytes()).hexdigest()!=digest:
        raise RuntimeError('M249 asset changed since this repair began: '+path)
report={}
for path,prop in [('/Game/Weapons/M249/SK_M249_V7','materials'),('/Game/Weapons/M249/Assembly/SM_M249_magnifier','static_materials')]:
    mesh=u.load_asset(path);slots=mesh.get_editor_property(prop);rows=[]
    for i,slot in enumerate(slots):
        name=str(slot.get_editor_property('imported_material_slot_name'))
        if not name or name=='None':raise RuntimeError('Missing imported identity '+path)
        old=str(slot.material_slot_name)
        if name.startswith('M249_'):
            material='M_M249_Reticle' if name=='M249_MagnifierReticle' else 'M_M249_Glass' if name=='M249_MagnifierGlass' else 'M_M249_OpticHousing' if name=='M249_OpticalHousing' else 'M_M249_Surface'
            slot.material_interface=u.load_asset('/Game/Weapons/M249/Materials/'+material)
        slot.material_slot_name=name;slots[i]=slot
        rows.append(dict(index=i,old=old,name=name,material=slot.material_interface.get_path_name()))
    mesh.set_editor_property(prop,slots)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+path)
    report[path]=rows
runpy.run_path(str(root/'import_motion.py'),init_globals={'only_roles':{'reload','reload_empty'}})
(r/'saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
# Read back saved native keys for the requested full-clip collision check.
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
geometry=pickle.load(open(r/'geometry.pkl','rb'));names=geometry['names']
after=r/'after';after.mkdir(exist_ok=True)
geometry['slots']=[str(s.material_slot_name) for s in mesh.materials]
with (after/'geometry.pkl').open('wb') as out:pickle.dump(geometry,out)
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for role in ('reload','reload_empty'):
    clip=u.load_asset('/Game/Weapons/M249/Animations/A_M249_'+role)
    model=clip.get_editor_property('data_model_interface');rate=model.get_frame_rate();fps=rate.numerator/rate.denominator
    frames=[[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(clip,names,i/fps,False,mesh)] for i in range(model.get_number_of_keys())]
    with (after/(role+'_local.pkl')).open('wb') as out:pickle.dump(dict(fps=fps,frames=frames),out)
print('M249_REPAIR06_SAVED',flush=True)
