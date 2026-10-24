"""Reusable precision light fixture and open, soft-fading beam shell."""
import bpy,math,json
from pathlib import Path
R=Path(__file__).resolve().parent;bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
M={k:bpy.data.materials.new(k) for k in ['StaticMetal','Yoke','HeadMetal','Lens','Beam']};groups={}
def cube(g,p,d,mat,bevel=.04):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.scale=d;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 mod=o.modifiers.new('Housing edges','BEVEL');mod.width=bevel;mod.segments=2;bpy.ops.object.modifier_apply(modifier=mod.name);o.data.materials.append(M[mat]);groups.setdefault(g,[]).append(o)
def cylinder(g,p,r,depth,mat,rot=(0,0,0),vertices=32):
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=p,rotation=rot);o=bpy.context.object;o.data.materials.append(M[mat]);groups.setdefault(g,[]).append(o)
cube('Base',(0,0,.12),(2.6,2.6,.24),'StaticMetal');cylinder('Base',(0,0,.42),.72,.60,'StaticMetal')
cylinder('Base',(0,0,.86),.83,.28,'Yoke');cube('Base',(0,0,1.12),(.64,2.3,.32),'Yoke')
for s in [-1,1]:
 cube('Base',(0,s*1.02,2.02),(.52,.24,1.8),'Yoke')
 cylinder('Base',(0,s*1.03,3),.35,.32,'Yoke',(math.pi/2,0,0))
for x in [-1,1]:
 for y in [-1,1]:cylinder('Base',(x,y,.27),.095,.08,'StaticMetal',vertices=12)
cube('Base',(.6,0,.48),(.48,.74,.62),'StaticMetal')
cylinder('Head',(0,0,-.1),.66,1.12,'HeadMetal',vertices=48)
cylinder('Head',(0,0,.49),.73,.14,'HeadMetal',vertices=48)
cylinder('Head',(0,0,.575),.60,.025,'Lens',vertices=48)
for z in [-.54,-.38,-.22,-.06]:cylinder('Head',(0,0,z),.70,.045,'HeadMetal',vertices=48)
for s in [-1,1]:cylinder('Head',(0,s*.82,0),.24,.40,'HeadMetal',(math.pi/2,0,0))
records=[]
for key,parts in groups.items():
 bpy.ops.object.select_all(action='DESELECT')
 for o in parts:o.select_set(True)
 bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_AP9_'+key
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
 mesh=ob.data;mesh.update()
 groups[key]=ob
# 400 m source length, no end caps; top dissipates instead of showing a disk.
v=[];faces=[];segments=48;rings=12
for j in range(rings+1):
 t=j/rings;z=.58+(400-.58)*t;r=.60+19.4*t
 for i in range(segments):a=i*math.tau/segments;v.append((r*math.cos(a),r*math.sin(a),z))
for j in range(rings):
 for i in range(segments):k=(i+1)%segments;faces.append((j*segments+i,j*segments+k,(j+1)*segments+k,(j+1)*segments+i))
mesh=bpy.data.meshes.new('Beam');mesh.from_pydata(v,[],faces);mesh.update();ob=bpy.data.objects.new('SM_AP9_Beam',mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(M['Beam']);uv=mesh.uv_layers.new(name='BeamUV')
for f in mesh.polygons:
 f.use_smooth=True;j=f.index//segments;i=f.index%segments
 for li,co in zip(f.loop_indices,[(i/segments,j/rings),((i+1)/segments,j/rings),((i+1)/segments,(j+1)/rings),(i/segments,(j+1)/rings)]):uv.data[li].uv=co
groups['Beam']=ob
for key,ob in groups.items():
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Production triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 path=R/'Meshes'/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
 records.append(dict(key=key,name=ob.name,fbx=str(path),triangles=len(ob.data.polygons)))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Searchlights_Source.blend'));(R/'assembly.json').write_text(json.dumps(records,indent=2),encoding='utf8');print('AP9_FIXTURES_AUTHORED',flush=True)
