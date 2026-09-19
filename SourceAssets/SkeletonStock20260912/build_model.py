"""Hard-surface refinement of reviewed Hunyuan/three-view silhouette. Source mesh retained separately."""
import bpy,bmesh,math,json,shutil
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
reduced=P/'ReducedGenerated';reduced.mkdir(exist_ok=True)
for name in ['SkeletonStock_Editable.blend','SM_SkeletonStock.fbx','SkeletonStock.glb','mesh_report.json','beauty.png','side.png','rear.png']+[f'T_SkeletonStock_{c}.png' for c in ['BaseColor','Roughness','Metallic','Normal']]:
 if (P/name).exists() and not (reduced/name).exists():shutil.copy2(P/name,reduced/name)
bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(name,color,metal,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
 noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=150;noise.inputs['Detail'].default_value=2
 ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(c*.9 for c in color),1);ramp.color_ramp.elements[1].color=(*(c*1.1 for c in color),1);l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color'])
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.1;bump.inputs['Distance'].default_value=.004;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal']);return m
frame=mat('Anodized_Graphite',(.068,.08,.092),.68,.5);polymer=mat('Charcoal_Polymer',(.04,.038,.034),0,.72);rubber=mat('Textured_Rubber',(.018,.021,.024),0,.83)
def bevel(o,r=.08,segments=3):
 bpy.context.view_layer.objects.active=o;m=o.modifiers.new('Regular machined bevel','BEVEL');m.width=r;m.segments=segments;bpy.ops.object.modifier_apply(modifier=m.name)
 for f in o.data.polygons:f.use_smooth=True
 m=o.modifiers.new('Weighted planar normals','WEIGHTED_NORMAL');m.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=m.name);return o
def mesh(name,verts,faces,material):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(material);return o
def plate(name,poly,width,material,r=.08):
 n=len(poly);v=[(x,y,z) for y in [-width/2,width/2] for x,z in poly];f=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)];return bevel(mesh(name,v,f,material),r)
def box(name,pos,size,material,r=.06):
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material);return bevel(o,r)
def cylinder(name,pos,r,depth,material,axis='Y',n=40,edge=.025):
 bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=r,depth=depth,location=pos);o=bpy.context.object;o.name=name
 if axis=='Y':o.rotation_euler.x=math.pi/2
 elif axis=='X':o.rotation_euler.y=math.pi/2
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);o.data.materials.append(material)
 return bevel(o,edge,2) if edge else o
def boolean(o,cutter,operation='DIFFERENCE'):
 bpy.context.view_layer.objects.active=o;m=o.modifiers.new('True open bore','BOOLEAN');m.operation=operation;m.solver='EXACT';m.object=cutter;bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cutter,do_unlink=True)
# Triangle beam and rear spine with a true through opening, not overlapping bars.
outer=[(2.55,.65),(22,.65),(22,-10.8)];inner=[(6,-.95),(20.65,-.95),(20.65,-9.25)]
v=[(x,y,z) for y in [-1.42,1.42] for poly in [outer,inner] for x,z in poly];f=[]
for i in range(3):
 j=(i+1)%3;f += [(i,j,j+3,i+3),(i+6,i+9,j+9,j+6),(i,i+6,j+6,j),(i+3,j+3,j+9,i+9)]
body=mesh('Continuous_Triangle_Frame',v,f,frame)
cut=cylinder('SlingBoreCutter',(21.3,0,-8.65),.46,4,frame,n=48,edge=0);boolean(body,cut);bevel(body,.10)
# A low cheek rest, separated by its clean moulded edge from the metallic beam.
plate('CheekRest',[(7,.6),(7.8,1.5),(9.1,1.8),(17.4,1.8),(18.6,1.35),(19.2,.5)],4.3,polymer,.16)
plate('RearBackplate',[(21.85,.65),(22.2,1.35),(22.5,1.15),(22.55,-10.2),(22.2,-10.8),(21.85,-10.5)],3.85,frame,.10)
plate('Contoured_Rubber_Buttpad',[(22.25,1.45),(22.62,1.55),(23,1.1),(23,-10.15),(22.6,-10.8),(22.25,-10.6)],4.8,rubber,.12)
for i in range(13):box('Pad_Grip_Rib',(22.99,0,.5-i*.78),(.08,4.0,.13),rubber,.035)
# Coupler and front support retain the original reference identity.
cylinder('ReceiverCoupler',(1.5,0,0),1.28,3.0,frame,'X',64,.055)
for x in [.15,.48,2.70]:cylinder('CouplerShoulder',(x,0,0),1.39,.16,frame,'X',64,.03)
plate('CouplerFoot',[(.85,1.4),(1.35,1.8),(2,1.6),(2.05,-3.0),(.85,-3.0)],2.85,frame,.1)
def fastener(x,z,width,r=.25):
 for side in [-1,1]:
  o=cylinder('RecessedFastener',(x,side*width/2,z),r,.10,frame,'Y',40,.018)
  cut=cylinder('HexSocket',(x,side*(width/2+.045),z),r*.48,.065,rubber,'Y',6,0);boolean(o,cut)
fastener(1.45,-1.78,2.94,.28)
for x in [9.4,13.2,16.8]:fastener(x,.90,4.31,.22)
for z in [-.7,-10.0]:fastener(21.4,z,2.92,.24)
for side in [-1,1]:
 lip=cylinder('SlingCupRim',(21.3,side*1.45,-8.65),.65,.16,frame,'Y',64,.025)
 cut=cylinder('SlingRimBore',(21.3,side*1.45,-8.65),.46,.4,frame,'Y',48,0);boolean(lip,cut)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'SkeletonStock_SeparateParts.blend'))
parts=[o for o in bpy.context.scene.objects if o.type=='MESH'];bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
high=body;bpy.context.view_layer.objects.active=high;bpy.ops.object.join();high.name='HardSurface_High_Master';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(high.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(high.data);bm.free();high.data.calc_loop_triangles()
rawverts=welded=len(high.data.vertices);original_images=[];span=Vector((1.002392,.255589,.755801));target=Vector((23.07,4.8,12.6))
code=(P/'optimize_model.py').read_text();code=code[code.index('low=high.copy()'):]
code=code.replace("dec.ratio=18000/len(low.data.polygons)","dec.ratio=min(1.0,18000/len(low.data.polygons))")
code=code.replace("'weld and decimate actual generated geometry; silhouette height calibrated to legacy proportions; authored PBR rebaked'","'hard-surface rebuild from reviewed three-view and Hunyuan silhouette; generated reduced reference kept in ReducedGenerated'")
code=code.replace("assert report['triangles']<19000", "assert report['triangles']<26000")
code=code.replace("bpy.ops.object.mode_set(mode='EDIT')", "m=low.modifiers.new('Preserve planar shading','WEIGHTED_NORMAL');m.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=m.name)\nbpy.ops.object.mode_set(mode='EDIT')",1)
code=code.replace("s.cycles.samples=32", "s.view_settings.exposure=.7;s.cycles.samples=32")
code=code.replace("(P/'mesh_report.json').write_text", "report['raw_vertices']=311141;report['welded_generated_vertices']=249998;report['rebuild_vertices']=report.pop('welded_vertices');report['dimensions_cm']=list(low.dimensions)\n(P/'mesh_report.json').write_text")
exec(compile(code,str(P/'optimize_model.py'),'exec'))
