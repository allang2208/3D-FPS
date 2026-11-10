"""Save axis-resolved sockets and register the V6 build component. No gameplay."""
import unreal as u,json,itertools,math,shutil,datetime
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ArcaneWorkbenchV6_20261107')
assert Path(u.Paths.project_dir()).resolve()==R.parents[1].resolve()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE running')
meshpath='/Game/Building/ArcaneWorkbenchV6_20261107/Meshes/SM_ArcaneWorkbench_V6'
mesh=u.load_asset(meshpath)
if mesh is None:raise RuntimeError('Missing imported mesh')
if mesh.get_outermost() in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Target mesh dirty before socket authoring')
source=json.loads((R/'Receipts/source-geometry.json').read_text(encoding='utf-8'))['geometry'][0]
imported=json.loads((R/'Receipts/imported-geometry.json').read_text(encoding='utf-8'))
orig=source['first_vertices'];actual=imported['first_vertices']
matches=[]
for p in itertools.permutations(range(3)):
 for s in itertools.product((-1,1),repeat=3):
  err=max(abs(s[i]*a[p[i]]-b[i]) for a,b in zip(orig,actual) for i in range(3))
  if err<0.001:matches.append((p,s,err))
if len(matches)!=1:raise RuntimeError('Import axis transform is ambiguous: '+str(matches))
perm,sign,error=matches[0]
def convert(v):return [sign[i]*v[perm[i]] for i in range(3)]
focus=convert([0,-5.2,96.85]);front=convert([0,-1,0]);up=convert([0,0,1]);along=convert([1,0,0])
if up!=[0,0,1]:raise RuntimeError('Imported bench is not Z-up')
# 435.6 cm eye distance keeps the 120 cm displayed weapon within the remaining
# viewport when the right inventory occupies 36% and the left panel is present.
eye=[focus[i]+front[i]*325.0+up[i]*290.0 for i in range(3)]
look=[focus[i]-eye[i] for i in range(3)]
yaw=math.degrees(math.atan2(look[1],look[0]));pitch=math.degrees(math.atan2(look[2],math.hypot(look[0],look[1])))
itemyaw=math.degrees(math.atan2(along[1],along[0]))
transforms={'ArcaneItem':(focus,[0,itemyaw,0]),'ArcaneCamera':(eye,[pitch,yaw,0])}
mesh.modify()
for name,(loc,rot) in transforms.items():
 socket=mesh.find_socket(name)
 if socket is None:
  socket=u.new_object(u.StaticMeshSocket,outer=mesh,name=name+'_Socket');socket.set_editor_property('socket_name',name);mesh.add_socket(socket)
 socket.set_editor_property('relative_location',u.Vector(*loc))
 socket.set_editor_property('relative_rotation',u.Rotator(*rot))
 socket.set_editor_property('relative_scale',u.Vector(1,1,1))
 socket.set_editor_property('tag','ArcaneWorkbenchV6_20261107')
 got=mesh.find_socket(name).get_editor_property('relative_location')
 if max(abs(a-b) for a,b in zip(loc,[got.x,got.y,got.z]))>0.001:raise RuntimeError('Socket write failed: '+name)
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Socket mesh save failed')
receipt={'stage':'sockets_saved','source_geometry_to_ue':{'permutation':perm,'sign':sign,'sample_max_error_cm':error,'samples':len(orig)},'source_fbx_node_rotation_z_degrees':180.00000500895632,'source_item_cm':[0,-5.2,96.85],'mesh_local_item_cm':focus,'mesh_local_front':front,'mesh_local_up':up,'sockets':{k:{'location_cm':v[0],'rotation_pitch_yaw_roll':v[1]} for k,v in transforms.items()},'camera_fov_degrees':55,'camera_eye_distance_cm':math.hypot(325,290),'layout_note':'Authored projection margin for 36% right inventory; no gameplay or visual acceptance performed.','tests_run':False}
(R/'Receipts/sockets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
# Back up the clean palette before the requested targeted registration.
backup=R/'Before';backup.mkdir(exist_ok=True)
palette_file=R.parents[1]/'Content/Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset'
backup_file=backup/('DA_VoxelBuildPalette_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.uasset')
shutil.copy2(palette_file,backup_file)
register=R/'Scripts/register_v6.py'
exec(compile(register.read_text(encoding='utf-8'),str(register),'exec'),{'__name__':'__main__'})
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
rows=[x for x in palette.get_editor_property('components') if str(x.get_editor_property('id'))=='arcane_workbench']
if len(rows)!=1:raise RuntimeError('Expected exactly one registered prefab')
row=rows[0]
if meshpath not in str(row.get_editor_property('mesh')):raise RuntimeError('Palette mesh readback failed')
foot=row.get_editor_property('footprint');off=row.get_editor_property('pivot_offset_cm')
registered=json.loads((R/'Receipts/registration.json').read_text(encoding='utf-8'))
registered.update({'palette_backup':str(backup_file),'readback_mesh':str(row.get_editor_property('mesh')),'footprint_cells':[foot.x,foot.y,foot.z],'pivot_offset_cm':[off.x,off.y,off.z],'display_name':str(row.get_editor_property('display_name')),'material_category':str(row.get_editor_property('material')),'saved_package':str(palette_file),'scene_or_savegame_modified':False})
(R/'Receipts/registration.json').write_text(json.dumps(registered,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'stage':'registered','mesh':meshpath,'sockets':receipt['sockets'],'prefab':registered},ensure_ascii=False))