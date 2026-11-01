import bpy,json,gzip,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).resolve().parent
D=json.load(gzip.open(O/'saved_geometry.json.gz','rt'))
def basis(x,z):
 x=Vector(x).normalized();z=(Vector(z)-x*Vector(z).dot(x)).normalized();y=z.cross(x)
 return Matrix((x,y,z)).transposed()
def m24mount(b):
 sr=Vector((-.0254083425,.1819224795,17.7973091602));sf=Vector((-.0254083425,-41.1078542471,17.7973091602));sm=Vector((.0000016143,-18.4658959508,5.5959127843))
 r=Matrix(b['WPN_RearSight']['world']).translation;f=Matrix(b['WPN_FrontSight']['world']).translation;m=Matrix(b['WPN_SOCKET_Magazine']['world']).translation
 rot=basis(f-r,r-m)@basis(sf-sr,sr-sm).transposed();scale=(f-r).length/(sf-sr).length
 return Matrix.Translation(r-rot@(sr*scale))@rot.to_4x4()@Matrix.Scale(scale,4)
def mat(name,color,metal=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.45
 return m
def object_mesh(name,v,fs,ma):
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],fs);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(ma);return ob
def light(pos,power,size,target):
 d=bpy.data.lights.new('softbox','AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new('softbox',d);bpy.context.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def render(name,center,scale,side=1,oblique=False):
 c=Vector(center);cam=bpy.context.scene.camera;cam.location=c+Vector((side*1.5,-.18 if oblique else 0,.2 if oblique else .03));cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
 bpy.context.scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
report={}
for key,row in D.items():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
 scene.render.resolution_x=1100;scene.render.resolution_y=550;scene.render.resolution_percentage=100
 scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.15,.15,.15,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
 scene.view_settings.view_transform='AgX'
 h=row['host'];s=row['stock'];v=np.array(h['positions']);f=np.array(h['triangles']);mi=np.array(h['material_ids'])
 hidden={i for i,m in enumerate(h['materials']) if m['slot'] in ('M24_FactoryStock','SVD_FactoryStock','KVInhibitor_stock') or m['slot'].startswith('MI_Manny')}
 keep=f[~np.isin(mi,list(hidden))];old=f[np.isin(mi,[i for i,m in enumerate(h['materials']) if 'FactoryStock' in m['slot'] or m['slot']=='KVInhibitor_stock'])]
 mount=m24mount(h['bones']) if key=='M24' else Matrix(h['bones']['WPN_root']['world'])@Matrix.Scale(.01,4)
 sv=np.array([list(mount@Vector(p)) for p in s['positions']]);sf=np.array(s['triangles']);sm=np.array(s['material_ids'])
 interface=np.unique(sf[sm==1]);iv=sv[interface];stock_tree=BVHTree.FromPolygons([Vector(p) for p in sv],sf[sm==0].tolist(),all_triangles=True);host_tree=BVHTree.FromPolygons([Vector(p) for p in v],keep.tolist(),all_triangles=True)
 hostdist=np.array([host_tree.find_nearest(Vector(p))[3] for p in iv]);stockdist=np.array([stock_tree.find_nearest(Vector(p))[3] for p in iv])
 near=iv[hostdist<.11];contact=near.mean(0) if len(near) else iv.mean(0)
 report[key]={'stock_component_matrix':list(map(list,mount)),'host_surface_contact_vertices_under_1_1_mm':len(near),'interface_unique_vertices':len(iv),
 'interface_host_distance_cm':{'min':float(hostdist.min()),'median':float(np.median(hostdist)),'max':float(hostdist.max())},
 'interface_stock_distance_cm':{'min':float(stockdist.min()),'median':float(np.median(stockdist)),'max':float(stockdist.max())},
 'native_rear_y_cm':float(v[np.unique(old),1].max()),'replacement_rear_y_cm':float(sv[:,1].max()),
 'host_surface_contact_center_cm':contact.tolist(),'hidden_materials':[h['materials'][i]['slot'] for i in sorted(hidden)]}
 object_mesh('Actual_saved_weapon',v*.01,keep.tolist(),mat('Receiver',(.25,.29,.32),.6))
 object_mesh('Actual_saved_skeleton_stock',sv*.01,sf[sm==0].tolist(),mat('Stock',(.04,.20,.22),.5))
 object_mesh('Actual_saved_adapter',sv*.01,sf[sm==1].tolist(),mat('Adapter',(.5,.26,.05),.6))
 center=(v[np.unique(keep)].mean(0)+sv.mean(0))*.005
 light((1,-.3,1),240,1,center);light((-1,.2,.6),150,1,center)
 camera=bpy.data.cameras.new('Camera');camera.type='ORTHO';co=bpy.data.objects.new('Camera',camera);bpy.context.collection.objects.link(co);scene.camera=co
 allpoints=np.concatenate((v[np.unique(keep)],sv));lo=allpoints.min(0)*.01;hi=allpoints.max(0)*.01
 render(key+'_assembled',(lo+hi)*.5,float(hi[1]-lo[1])*1.12)
 render(key+'_seam_right',contact*.01,.36,1,True)
 render(key+'_seam_left',contact*.01,.36,-1,True)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(key+'_actual_asset_fit.blend')))
(O/'fit_metrics.json').write_text(json.dumps(report,indent=2))
print('STOCK_FIT_RENDER_COMPLETE',flush=True)
