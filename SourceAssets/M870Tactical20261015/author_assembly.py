"""Create the M870 workbench components from whole source shells."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;X=O/'Assembly';X.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Original/Source/source/M870_Tactical.fbx'))
source=next(o for o in bpy.context.scene.objects if o.type=='MESH');source.data.transform(source.matrix_world);source.matrix_world=Matrix.Identity(4)
source.data.materials[0].name='M870_OriginalSurface';info=json.loads((O/'source_geometry.json').read_text())[0];groups={}
for i,c in enumerate(info['islands']):
 lo,hi=c['lo'],c['hi'];pump=(lo[1]>=1.209 and hi[1]<=3.088 and hi[2]<=.604) or (lo[1]>=.175 and hi[1]<=1.627 and lo[2]>=.445 and hi[2]<=.548)
 group='pump' if pump else 'bolt' if i in {8,46,111,200,240,241,242,243,244} else 'trigger' if i in {17,73,74} else 'stock' if hi[1]<=-1.60 else 'barrel' if lo[1]>=.19 and lo[2]>=.52 else 'body'
 groups.setdefault(group,set()).update(c['ids'])
flat=Matrix(((0,0,.1,0),(0,-.1,0,0),(.1,0,0,0),(0,0,0,1)));pts=[flat@v.co for v in source.data.vertices];lo=Vector([min(v[k] for v in pts) for k in range(3)]);hi=Vector([max(v[k] for v in pts) for k in range(3)]);frame=Matrix.Translation(Vector((.82-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,.97-lo.z)))@flat
recipe=dict(id='assemble_m870',output='ue_m870',inputs=[dict(item='ironIngot',count=16),dict(item='copperIngot',count=5),dict(item='wood',count=2),dict(item='search_assembly_component_box',count=2)],camera=[20,0,215],look_at=[75,0,99],position_tolerance_cm=5,angle_tolerance_deg=18,calibration_seconds=5.5,parts=[]);manifest=[]
labels=dict(body='机匣与弹仓',stock='枪托',barrel='枪管组件',pump='泵动护木',bolt='枪机组件',trigger='扳机')
for group,ids in groups.items():
 ob=source.copy();ob.data=source.data.copy();bpy.context.scene.collection.objects.link(ob);ob.name='SM_M870_Assembly_'+group
 bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ids],context='VERTS');bm.to_mesh(ob.data);bm.free();ob.data.transform(frame)
 lo=Vector([min(v.co[k] for v in ob.data.vertices) for k in range(3)]);hi=Vector([max(v.co[k] for v in ob.data.vertices) for k in range(3)]);center=(lo+hi)/2;extent=(hi-lo)*50
 ob.data.transform(Matrix.Diagonal((1,-1,1,1))@Matrix.Translation(-center));ob.data.flip_normals()
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;file=X/(ob.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 path='/Game/Weapons/M870/Tactical20261015/Assembly/'+ob.name;manifest.append(dict(file=str(file),name=ob.name,path=path))
 if group=='body':recipe.update(body_mesh=path,body_position=list(center*100))
 else:recipe['parts'].append(dict(id=group,name=labels[group],mesh=path,target=list(center*100),extent=list(extent),loose=[59,0,95.3+extent.z],angle=0,radius=max(3.5,min(extent.x,extent.y)+1.5)))
 ob.location=Vector((center.x,-center.y,center.z))
lanes=[[],[]]
for i,part in sorted(enumerate(recipe['parts']),key=lambda p:p[1]['extent'][1],reverse=True):
 lane=min(range(2),key=lambda n:sum(x[1] for x in lanes[n]));ex,ey,_=part['extent'];angle=15 if ey>12 else [35,-40,55,-30,45][i];angle*=(-1 if lane else 1);span=2*(abs(ex*math.sin(math.radians(angle)))+abs(ey*math.cos(math.radians(angle))))+5;lanes[lane].append((part,span,angle))
for lane,entries in enumerate(lanes):
 y=-sum(e[1] for e in entries)/2
 for part,span,angle in entries:part['loose']=[57 if lane==0 else 110,y+span/2,part['loose'][2]];part['angle']=angle;y+=span
bpy.data.objects.remove(source,do_unlink=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(X/'M870_Assembly_Editable.blend'))
(X/'manifest.json').write_text(json.dumps(manifest,indent=2));(X/'recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf-8');print('M870_ASSEMBLY_AUTHORED',len(manifest))
