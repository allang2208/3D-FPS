"""Offline geometry views for the requested physical port check. No game launch."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
D=json.loads((O/'ports_before.json').read_text())
(O/'Geometry').mkdir(exist_ok=True);(O/'Views').mkdir(exist_ok=True)
report={}
def matrix(t):return Matrix.LocRotScale(Vector(t['p']),Quaternion((t['q'][3],*t['q'][:3])),Vector(t['s']))
for key,row in D['weapons'].items():
 if not row.get('export'):continue
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=row['export'],use_anim=False)
 r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
 ref=row['mesh_reference'];pairs=[n for n in ref if n in r.data.bones]
 src=np.array([list(r.matrix_world@r.data.bones[n].matrix_local.translation)+[1] for n in pairs])
 dst=np.array([ref[n]['p'] for n in pairs])
 fit=np.linalg.lstsq(src,dst,rcond=None)[0]
 error=float(np.max(np.linalg.norm(src@fit-dst,axis=1)))
 if error>.1:raise RuntimeError(f'{key}: FBX/reference mismatch {error} cm')
 root=matrix(ref['WPN_root']);inv=root.inverted()
 markers={n:list(inv@Vector(v['p'])*100) for n,v in ref.items()}
 rear=Vector(markers['WPN_RearSight']);front=Vector(markers['WPN_FrontSight']);muzzle=Vector(markers['WPN_SOCKET_Muzzle'])
 forward=(front-rear).normalized();up=(rear-muzzle)-forward*(rear-muzzle).dot(forward);up.normalize()
 side=up.cross(forward).normalized();basis=Matrix((forward,side,up))
 port=basis@Vector(markers['WPN_SOCKET_Eject'])
 points=[];faces=[];matindices=[];material_names=[]
 for ob in list(bpy.context.scene.objects):
  if ob.type!='MESH':continue
  allowed={g.index for g in ob.vertex_groups if g.name.startswith('WPN_') or g.name.startswith('PKM_')}
  own=[any(g.group in allowed and g.weight>.2 for g in v.groups) for v in ob.data.vertices]
  vertices=[]
  for v in ob.data.vertices:
   p=ob.matrix_world@v.co;ue=np.array([*p,1])@fit
   vertices.append(inv@Vector(ue)*100)
  used={i for p in ob.data.polygons if all(own[v] for v in p.vertices) for i in p.vertices}
  mapping={old:len(points)+i for i,old in enumerate(sorted(used))}
  points.extend([list(vertices[i]) for i in sorted(used)])
  offset=len(material_names);material_names.extend([m.name if m else 'None' for m in ob.data.materials])
  for p in ob.data.polygons:
   if all(i in mapping for i in p.vertices):faces.append([mapping[i] for i in p.vertices]);matindices.append(offset+p.material_index)
 np.savez_compressed(O/'Geometry'/(key+'.npz'),vertices=np.array(points),faces=np.array(faces,dtype=object),material_indices=np.array(matindices),materials=np.array(material_names))
 # All following geometry uses centimetres in a semantic gun frame.
 for ob in list(bpy.context.scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
 me=bpy.data.meshes.new(key);me.from_pydata([basis@Vector(p) for p in points],[],faces);me.update()
 ob=bpy.data.objects.new(key,me);bpy.context.collection.objects.link(ob)
 for name in material_names:
  m=bpy.data.materials.new(name);m.diffuse_color=(.43,.46,.49,1);me.materials.append(m)
 for poly,mi in zip(me.polygons,matindices):poly.material_index=mi;poly.use_smooth=True
 bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.28,location=port)
 mark=bpy.context.object;mark.name='CURRENT_EJECTION_PORT';mark.show_in_front=True;mark.color=(1,.025,.02,1)
 scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
 scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.35
 scene.display.shading.color_type='OBJECT';ob.color=(.45,.48,.51,1)
 scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
 scene.display.shading.cavity_type='BOTH';scene.display.shading.background_type='WORLD'
 scene.world=bpy.data.worlds.new('PortCheckWorld');scene.world.color=(.07,.07,.07)
 scene.render.resolution_x=1100;scene.render.resolution_y=700;scene.render.resolution_percentage=100
 camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
 camdata.type='ORTHO';camdata.lens=50;camdata.clip_end=2000
 small=key in ('m1911','g18','pit_viper2011','dw715','rsh12')
 width=27 if small else 62
 target=port.copy();target.y=0
 for suffix,offset in [('side_p',(0,100,8)),('side_n',(0,-100,8)),('top',(0,8,100))]:
  cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
  camdata.ortho_scale=width;scene.render.filepath=str(O/'Views'/f'{key}_{suffix}.png')
  bpy.ops.render.render(write_still=True)
 report[key]={'fbx_reference_error_cm':error,'root_markers_cm':markers,'basis_rows':[list(v) for v in basis],
     'port_semantic_cm':list(port),'materials':material_names,'vertices':len(points),'faces':len(faces)}
 (O/'geometry_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('CASING_GEOMETRY',key,'port',list(port),'error_cm',error,flush=True)
