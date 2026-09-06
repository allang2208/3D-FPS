import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'foreman-motion-v04-20260906/foreman-motion-v04.blend'))
a=bpy.data.objects['ForemanRig'];body=bpy.data.objects['ForemanBody'];s=bpy.context.scene
a.animation_data.action=None
for track in a.animation_data.nla_tracks:track.mute=True
for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
report={'bones':{},'weights':{},'controlled_poses':{}}
for n in ['clavicle.L','upper_arm.L','forearm.L','hand.L','clavicle.R','upper_arm.R','forearm.R','hand.R']:
 b=a.data.bones[n];report['bones'][n]={'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None,'length':b.length}
weights=[]
for v in body.data.vertices:weights.append({body.vertex_groups[g.group].name:g.weight for g in v.groups})
arm_names=[n for n in body.vertex_groups.keys() if any(k in n for k in ['clavicle','upper_arm','forearm','hand'])]
core=[v.index for v in body.data.vertices if abs(v.co.x)<.56 and 1.28<v.co.z<1.85 and v.co.y<-.20]
leaks=[(i,sum(weights[i].get(n,0) for n in arm_names)) for i in core]
report['weights']={'vertices':len(weights),'max_sum_error':max(abs(sum(w.values())-1) for w in weights),'max_influences':max(sum(x>1e-5 for x in w.values()) for w in weights),'front_torso_region_vertices':len(core),'front_torso_arm_weight_gt_25_percent':sum(w>.25 for i,w in leaks),'front_torso_arm_weight_max':max((w for i,w in leaks),default=0),'finger_bones':[b.name for b in a.data.bones if any(x in b.name.lower() for x in ['finger','thumb','index'])]}
# Vertex-weight map: blue torso, green upper arm/clavicle, orange forearm, magenta hand.
attr=body.data.color_attributes.new(name='AuditWeights',type='FLOAT_COLOR',domain='POINT')
for i,w in enumerate(weights):
 torso=max(0,1-sum(w.get(n,0) for n in arm_names));upper=sum(v for n,v in w.items() if 'upper_arm' in n or 'clavicle' in n);fore=sum(v for n,v in w.items() if 'forearm' in n);hand=sum(v for n,v in w.items() if 'hand' in n)
 attr.data[i].color=(.06*torso+.1*upper+fore+hand,.30*torso+.9*upper+.35*fore+.1*hand,.9*torso+.1*upper+.04*fore+.7*hand,1)
mat=bpy.data.materials.new('Audit weight colors');mat.use_nodes=True;nodes=mat.node_tree.nodes;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=.85;c=nodes.new('ShaderNodeVertexColor');c.layer_name='AuditWeights';mat.node_tree.links.new(c.outputs['Color'],bs.inputs['Base Color']);body.data.materials.clear();body.data.materials.append(mat)
bpy.data.objects['Whip'].hide_render=True
s.render.engine='CYCLES';s.cycles.samples=12;s.render.resolution_x=900;s.render.resolution_y=700;s.render.resolution_percentage=100
cam=s.camera;cam.data.ortho_scale=2.5
# Bones are drawn as emissive rods with joint balls, positioned in front for visibility.
markers=[]
for n,data in report['bones'].items():
 h=Vector(data['head']);t=Vector(data['tail']);h.y=-.55;t.y=-.55
 cu=bpy.data.curves.new(n,'CURVE');cu.dimensions='3D';cu.bevel_depth=.009;sp=cu.splines.new('POLY');sp.points.add(1);sp.points[0].co=(*h,1);sp.points[1].co=(*t,1);o=bpy.data.objects.new(n+' marker',cu);s.collection.objects.link(o);markers.append(o)
 bm=bpy.data.materials.new(n+' marker');bm.diffuse_color=(1,.1,.03,1);bm.use_nodes=True;nd=next(n for n in bm.node_tree.nodes if n.type=='BSDF_PRINCIPLED');nd.inputs['Base Color'].default_value=(1,.1,.03,1);nd.inputs['Emission Color'].default_value=(1,.15,.01,1);nd.inputs['Emission Strength'].default_value=2;cu.materials.append(bm)
 for p in [h,t]:
  bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=.022,location=p);o=bpy.context.object;o.data.materials.append(bm);markers.append(o)
def render(name,side=False):
 cam.location=(4,-1,1.8) if side else (0,-6,1.65);cam.rotation_euler=(Vector((0,0,1.65))-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(R/(name+'.png'));bpy.ops.render.render(write_still=True)
render('rest-weight-map')
for o in markers:o.hide_render=True
render('rest-side',True)
rest=[v.co.copy() for v in body.data.vertices]
for name,bone,angle in [('elbow-R-90','forearm.R',math.pi/2),('shoulder-R-90','upper_arm.R',math.pi/2),('wrist-R-45','hand.R',math.pi/4)]:
 for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
 pb=a.pose.bones[bone];pb.rotation_mode='XYZ';pb.rotation_euler.x=angle;bpy.context.view_layer.update()
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();moving=[(me.vertices[i].co-rest[i]).length for i in core];report['controlled_poses'][name]={'front_torso_max_displacement_m':max(moving,default=0),'front_torso_vertices_moving_over_2cm':sum(d>.02 for d in moving)};ev.to_mesh_clear();render(name)
(R/'audit-report.json').write_text(json.dumps(report,indent=2));print('RIG_AUDIT',json.dumps(report))
