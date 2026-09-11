"""Landmark-guided anatomy sculpt. Authored pixel landmarks are reprojected to the existing skin."""
import bpy,json,sys,math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910');out=r/'sculpt_v06'
bpy.ops.wm.open_mainfile(filepath=str(r/'realism_v05/HandBrain_Refined_Baked.blend'))
rig=bpy.data.objects['SK_HandBrain'];rig.animation_data.action=bpy.data.actions['Idle'];rig.animation_data.action_slot=bpy.data.actions['Idle'].slots[0];bpy.context.scene.frame_set(1)
body=bpy.data.objects['HandBrain_Body'];bpy.context.view_layer.objects.active=body
bpy.ops.mesh.customdata_custom_splitnormals_clear();body.data.calc_loop_triangles()
bvh=BVHTree.FromPolygons([v.co for v in body.data.vertices],[t.vertices for t in body.data.loop_triangles],all_triangles=True)
views={'left':(Vector((0,-6,1)),Vector((1,0,0)),Vector((0,1,0))), 'right':(Vector((0,6,1)),Vector((-1,0,0)),Vector((0,-1,0))), 'back':(Vector((-6,0,1)),Vector((0,-1,0)),Vector((1,0,0)))}
def pick(view,pixel):
 origin,right,direction=views[view];start=origin+right*((pixel[0]/1400-.5)*2.18)+Vector((0,0,(.5-pixel[1]/1400)*2.18))
 hit,n,idx,dist=bvh.ray_cast(start,direction)
 if hit is None:raise ValueError((view,pixel))
 return hit,n
features=[];rejected=[];finger_count=0
def feature(view,pix,axis,L,W,amp,kind):
 p,n=pick(view,pix);a=axis-n*axis.dot(n)
 if a.length<.001:return
 a.normalize();b=n.cross(a).normalized()
 features.append(dict(center=list(p),normal=list(n),axis=list(a),side=list(b),length=L,width=W,amplitude=amp,kind=kind))
data=json.loads((out/'landmarks.json').read_text())
for view,hands in data.items():
 for h in hands:
  wrist,wn=pick(view,h['wrist'])
  for xy in h['fingers']:
   b=np.array(xy[:2],float);t=np.array(xy[2:],float);base,bn=pick(view,b);tip,tn=pick(view,t);axis=tip-base;length=axis.length
   if not .045<length<.36:rejected.append([view,xy,length]);continue
   finger_count+=1
   for fraction,amp in [(.10,.0030),(.43,.0032),(.73,.0024)]:
    feature(view,b+(t-b)*fraction,axis,.012,.011,amp,'bone')
   for fraction in [.27,.59]:feature(view,b+(t-b)*fraction,axis,.012,.010,-.0019,'shaft')
   for fraction in [.43,.73]:
    for offset in [-.030,.0,.030]:feature(view,b+(t-b)*(fraction+offset),axis,.0009,.009,-.00065,'crease')
   feature(view,b+(t-b)*.87,axis,min(.015,length*.13),.009,.001,'nail')
   # Tendons fan from each metacarpal toward the wrist, following the visible hand.
   tendon_axis=base-wrist
   for fraction in [.32,.52,.72]:feature(view,np.array(h['wrist'])*(1-fraction)+b*fraction,tendon_axis,.018,.0035,.0018,'tendon')
  feature(view,h['wrist'],Vector((1,0,.3)),.015,.022,.0025,'wrist')
(out/'projected_features.json').write_text(json.dumps({'fingers':finger_count,'hands':sum(map(len,data.values())),'rejected':rejected,'features':features},indent=2))
def sculpt(obj,detail):
 count=len(obj.data.vertices);coords=np.empty(count*3,dtype=np.float32);obj.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
 normals=np.empty(count*3,dtype=np.float32);obj.data.vertices.foreach_get('normal',normals);normals=normals.reshape(-1,3)
 change=np.zeros_like(coords);nails=np.zeros(count,dtype=np.float32)
 for f in features:
  if not detail and f['kind'] in ['crease','nail']:continue
  c=np.array(f['center']);a=np.array(f['axis']);b=np.array(f['side']);n=np.array(f['normal']);L=f['length'];W=f['width']
  bound=max(L,W)*3+.025;ids=np.where(np.all(np.abs(coords-c)<bound,axis=1))[0]
  d=coords[ids]-c;x=d@a;y=d@b;z=d@n
  gate=np.clip((normals[ids]@n-.2)/.6,0,1)*np.exp(-.5*(z/.012)**2)
  if f['kind']=='nail':
   rr=((x/L)**4+(y/W)**4)**.25;plate=np.clip((1.12-rr)/.15,0,1)*gate
   amount=.0010*plate-.0012*np.exp(-((rr-1.15)/.15)**2)*gate
   nails[ids]=np.maximum(nails[ids],plate)
  else:amount=f['amplitude']*np.exp(-.5*((x/L)**2+(y/W)**2))*gate
  change[ids]+=amount[:,None]*n
  if f['kind'] in ['shaft','bone']:
   lateral=(-.22 if f['kind']=='shaft' else .13)*y*np.exp(-.5*((x/L)**2+(y/W)**2))*gate
   change[ids]+=lateral[:,None]*b
 length=np.linalg.norm(change,axis=1);change*=np.minimum(1,.007/np.maximum(length,1e-9))[:,None]
 obj.data.vertices.foreach_set('co',(coords+change).ravel());obj.data.update()
 attr=obj.data.attributes.get('SculptNail') or obj.data.attributes.new('SculptNail','FLOAT','POINT');attr.data.foreach_set('value',nails)
 return {'vertices':count,'moved':int((length>1e-5).sum()),'max_delta_m':float(np.linalg.norm(change,axis=1).max())}
# Broad anatomical changes exist on the runtime geometry, not only in a shader.
lowstats=sculpt(body,False)
high=body.copy();high.data=body.data.copy();bpy.context.collection.objects.link(high);high.name='HandBrain_Sculpt_High'
for m in list(high.modifiers):high.modifiers.remove(m)
bpy.context.view_layer.objects.active=high
sub=high.modifiers.new('Sculpt surface resolution','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=2
bpy.ops.object.modifier_apply(modifier=sub.name)
# Broad shape is already on the low mesh: only high-frequency carving is added here.
saved=features;features=[f for f in saved if f['kind'] in ['crease','nail']];highstats=sculpt(high,True);features=saved
for i,m in enumerate(high.data.materials):
 m=m.copy();high.data.materials[i]=m;p=m.node_tree.nodes.get('Principled BSDF');nodes=m.node_tree.nodes;links=m.node_tree.links
 # Re-baking a low-mesh tangent normal on subdivided tangents creates faceting.
 # Bake the new sculpt geometry itself; retain subtle procedural pores separately.
 for link in list(p.inputs['Normal'].links):links.remove(link)
 tc=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=700;noise.inputs['Detail'].default_value=2;links.new(tc.outputs['Object'],noise.inputs['Vector'])
 bump=nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00035;bump.inputs['Strength'].default_value=.3;links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs[0],p.inputs['Normal'])
 attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='SculptNail'
 mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';links.new(attr.outputs['Fac'],mix.inputs[0]);links.new(p.inputs['Base Color'].links[0].from_socket,mix.inputs[1]);mix.inputs[2].default_value=(.16,.135,.065,1);links.new(mix.outputs[0],p.inputs['Base Color'])
 m['bake_base_node']=mix.name;m['bake_base_socket']='Color'
 rough=p.inputs['Roughness'].links[0].from_socket;m['bake_rough_node']=rough.node.name;m['bake_rough_socket']=rough.name
high.hide_render=True;high.hide_set(True)
(out/'sculpt_report.json').write_text(json.dumps({'low':lowstats,'high':highstats,'fingers':finger_count,'hands':sum(map(len,data.values())),'rejected':rejected,'bones':len(rig.data.bones),'actions':{a.name:list(a.frame_range) for a in bpy.data.actions}},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'HandBrain_Sculpt_Source.blend'))
if '--skip-render' in sys.argv:sys.exit(0)
sys.path.insert(0,str(r/'hunyuan_v01'));import studio
s=bpy.context.scene;cam=studio.setup(1400);s.cycles.samples=24
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
s.cycles.device='GPU'
studio.aim(cam,(0,-6,1),(0,0,1));cam.data.ortho_scale=2.18
s.render.filepath=str(out/'Left_geometry.png');bpy.ops.render.render(write_still=True)
body.hide_render=True;high.hide_render=False;high.hide_set(False)
studio.aim(cam,(0,-6,1.06),(0,0,1.06));cam.data.ortho_scale=.75
s.render.filepath=str(out/'Hand_high_closeup.png');bpy.ops.render.render(write_still=True)
print('HANDBRAIN_ANATOMY_SCULPT_COMPLETE')
