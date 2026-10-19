"""Save the fitted, mechanically separated source assembly (no preview rendering)."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12K20261017')
g=json.loads((O/'Authoring/source_geometry.json').read_text());islands=json.loads((O/'Authoring/source_islands.json').read_text())
faceparts={}
for ii,a in enumerate(islands):
 b=a['bone'];part='Body'
 if b=='mag_02':part='Magazine'
 elif b=='bolt_01':part='Bolt'
 elif b=='safety_06':part='Safety'
 elif b=='magrelease_05':part='MagRelease'
 elif b in ('bullet_03','bullets_04'):part='ShellBrass' if any(m in (9,10,12,13) for m in a['materials']) else 'ShellPlastic'
 elif ii==21:part='Trigger'
 elif ii==1:part='Stock'
 elif ii==8:part='RearGrip'
 elif ii==4:part='Handguard'
 for fi in a['faces']:faceparts[fi]=part
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
for part in sorted(set(faceparts.values())):
 fs=[i for i in faceparts if faceparts[i]==part];ids=sorted({v for i in fs for v in g['triangles'][i]});im={v:i for i,v in enumerate(ids)}
 def pos(p):return (-p[2]*.0125+.0008,-p[0]*.0125-.1152,p[1]*.0125-.0123)
 # Two axis sign changes give a proper rotation into Blender, preserving winding.
 mesh=bpy.data.meshes.new('Saiga12K_'+part);mesh.from_pydata([pos(g['positions'][v]) for v in ids],[],[[im[v] for v in g['triangles'][i]] for i in fs]);mesh.update()
 ob=bpy.data.objects.new('Saiga12K_'+part,mesh);scene.collection.objects.link(ob)
 for p in mesh.polygons:p.use_smooth=True
 mesh.normals_split_custom_set([(-g['normals'][v][2],-g['normals'][v][0],g['normals'][v][1]) for fi in fs for v in g['triangles'][fi]])
 uv=mesh.uv_layers.new(name='UVMap')
 for f in mesh.polygons:
  for li in f.loop_indices:
   p=g['positions'][ids[mesh.loops[li].vertex_index]];uv.data[li].uv=(p[0]*.05,p[1]*.05)
 mat=bpy.data.materials.new('Saiga12K_'+part);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');poly=part in ('Stock','RearGrip','Handguard','Magazine','ShellPlastic')
 color=(.024,.025,.026,1) if poly else (.045,.048,.05,1)
 if part=='ShellBrass':color=(.35,.23,.08,1)
 if part=='ShellPlastic':color=(.19,.025,.018,1)
 bs.inputs['Base Color'].default_value=color;bs.inputs['Metallic'].default_value=0 if poly else 1;bs.inputs['Roughness'].default_value=.63 if poly else .32
 mesh.materials.append(mat)
 ob['runtime_bone']='WPN_SOCKET_Magazine' if part.startswith('Shell') or part=='Magazine' else 'WPN_bolt' if part=='Bolt' else 'WPN_Trigger' if part=='Trigger' else 'WPN_root'
 ob['source_author']='TastyTony / CC BY 4.0'
scene['authoring_contract']='Gun subassembly in shared WPN_root coordinates. Runtime V9 arms, native bind and exact weights are assembled by Tools/Saiga12K/produce_assets.py.'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Authoring/Saiga12K_FittedParts.blend'))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=str(O/'Exports/Saiga12K_FittedParts.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
print('SAIGA_EDITABLE_SOURCE_SAVED')
