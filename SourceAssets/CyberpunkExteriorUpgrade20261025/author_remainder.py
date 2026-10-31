"""Re-author only the remainder of the four old city batches; remove replaced lots."""
import bpy,ast,json,math,random,sys,runpy
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;PROJECT=R.parents[1];OLD=PROJECT/'SourceAssets/CyberpunkApartmentRebuild20261022'
layout=json.loads((R/'layout.json').read_text());skip=set(layout['replaced_indices'])
bpy.ops.wm.open_mainfile(filepath=str(OLD/'RefinementV19/LuminousSkyline_Source.blend'));scene=bpy.context.scene
mats={m.name:m for m in bpy.data.materials};groups={};buildings=[];ATLAS_METRES=(76.8,121.6);FLOOR=3.8
for ob in list(scene.objects):
    if ob.name in layout['affected_groups']:bpy.data.objects.remove(ob,do_unlink=True)
tree=ast.parse((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/author_scene.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'face','box','outline','shell','ring','beam','equipment','signage','tower'}],type_ignores=[]),'retained_grammar','exec'),globals())
baseface=face
tree=ast.parse((OLD/'RefinementV17/author_city.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'face','tier'}],type_ignores=[]),'retained_v17_facades','exec'),globals())
rows=json.loads((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/assembly.json').read_text())['buildings'];roles=['WarmBands','PearlVertical','AmberTerrace','BlueFrame','CopperArcade','QuietGlass'];tints=['Gold','Pearl','Amber','Blue','Gold','Teal']
for i,row in enumerate(rows):
    if i in skip or row['group'] not in layout['affected_groups']:continue
    row={k:row[k] for k in ['group','x','y','width','depth','height','style']};fi=(i*7+row['style']*3)%6;current_family=roles[fi];current_light='Light'+tints[fi];tower(row,i)

out=R/'Meshes';out.mkdir(exist_ok=True);records=[]
for key,data in groups.items():
    me=bpy.data.meshes.new(key);me.from_pydata(data['v'],[],data['f']);me.update();ob=bpy.data.objects.new(key,me);scene.collection.objects.link(ob);ob.location.y=-615
    order=list(dict.fromkeys(data['m']))
    for role in order:me.materials.append(mats[role])
    uv=me.uv_layers.new(name='ArchitecturalUV')
    for poly,role,coords in zip(me.polygons,data['m'],data['uv']):
        poly.material_index=order.index(role)
        for li,co in zip(poly.loop_indices,coords):uv.data[li].uv=co
    clone=ob.copy();clone.data=me.copy();scene.collection.objects.link(clone);clone.location=(0,0,0);clone.name='SM_Exterior_Remainder_'+key
    for v in clone.data.vertices:v.co=((-v.co.x+10)*1.25,-(v.co.y-615)*1.25,(v.co.z-90)*1.25)
    bpy.ops.object.select_all(action='DESELECT');clone.select_set(True);bpy.context.view_layer.objects.active=clone;mod=clone.modifiers.new('Triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    fbx=out/(clone.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    records.append(dict(key=key,name=clone.name,fbx=str(fbx),materials=order,triangles=len(clone.data.polygons)));bpy.data.objects.remove(clone,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'ExteriorRemainder_Source.blend'))
# The five established landmarks retain their profile and exact light/projector
# anchors. Weld their actual shells and manufacture rounded edges at real scale.
for index in range(5):
    key=f'Landmark_{index}';source=bpy.data.objects.get(key)
    if not source:raise RuntimeError('Missing retained landmark '+key)
    clone=source.copy();clone.data=source.data.copy();scene.collection.objects.link(clone);clone.location=(0,0,0);clone.name='SM_Exterior_Refined_'+key
    bpy.ops.object.select_all(action='DESELECT');clone.select_set(True);bpy.context.view_layer.objects.active=clone
    weld=clone.modifiers.new('Joined manufactured shells','WELD');weld.merge_threshold=.002;bpy.ops.object.modifier_apply(modifier=weld.name)
    bevel=clone.modifiers.new('Landmark edge radius','BEVEL');bevel.width=.075;bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(28);bevel.use_clamp_overlap=True;bevel.harden_normals=True;bpy.ops.object.modifier_apply(modifier=bevel.name)
    norm=clone.modifiers.new('Architectural weighted normals','WEIGHTED_NORMAL');norm.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=norm.name)
    for v in clone.data.vertices:v.co=((-v.co.x+10)*1.25,-(v.co.y-615)*1.25,(v.co.z-90)*1.25)
    tri=clone.modifiers.new('Production triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    # Bevel interpolation can collapse UVs onto the adjacent edge. Give only
    # these new sliver faces a non-degenerate local projection for tangent normals.
    uv=clone.data.uv_layers.active
    for poly in clone.data.polygons:
        coords=[uv.data[i].uv.copy() for i in poly.loop_indices]
        area=sum(a.x*b.y-b.x*a.y for a,b in zip(coords,coords[1:]+coords[:1]))
        if abs(area)<1e-10:
            dominant=max(range(3),key=lambda k:abs(poly.normal[k]));axes=[k for k in range(3) if k!=dominant]
            anchor=clone.data.vertices[clone.data.loops[poly.loop_indices[0]].vertex_index].co.copy()
            for li in poly.loop_indices:
                co=clone.data.vertices[clone.data.loops[li].vertex_index].co
                uv.data[li].uv=(coords[0].x+(co[axes[0]]-anchor[axes[0]])/4.,coords[0].y+(co[axes[1]]-anchor[axes[1]])/4.)
    fbx=out/(clone.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    records.append(dict(key=key,name=clone.name,fbx=str(fbx),materials=[m.name for m in clone.data.materials],triangles=len(clone.data.polygons),edge_radius_author_m=.075));bpy.data.objects.remove(clone,do_unlink=True)
(R/'remainder.json').write_text(json.dumps(dict(meshes=records,removed_indices=sorted(skip)),indent=2),encoding='utf8')
print('EXTERIOR_OLD_BATCHES_AUTHORED',len(records),'removed lots',len(skip),flush=True)
