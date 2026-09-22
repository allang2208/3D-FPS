"""Adapt user-selected Fab meshes, preserving source UVs and preparing workshop placement."""
from pathlib import Path
import bpy, bmesh, json, math, re
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored'
PREV=ROOT.parent/'DungeonWorkshopSurface20260921'
WORLD=Matrix(((-1,0,0,10),(0,-1,0,0),(0,0,1,0),(0,0,0,1)))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
MATS={}
with bpy.data.libraries.load(str(PREV/'Authored/DungeonWorkshopSurfaceDetails.blend'),link=False) as (src,dst):
    dst.materials=['WSFinish_GroundSteel','WSFinish_Grip','WSFinish_SheetPaint']
for mat in dst.materials:
    MATS[mat.name.removeprefix('WSFinish_')]=mat
MATS['Machined']=MATS['GroundSteel']
exec(compile((PREV/'Scripts/modeling.py').read_text(),'modeling.py','exec'),globals())

atlas=bpy.data.materials.new('FabGarage_Atlas');atlas.use_nodes=True
p=next(n for n in atlas.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
p.inputs['Base Color'].default_value=(.22,.24,.23,1)
p.inputs['Roughness'].default_value=.58
# The texture binder attaches the publisher's original atlas when it is available.

source=bpy.data.collections.new('EDITABLE_FAB_TOOLS');scene.collection.children.link(source)
export=bpy.data.collections.new('ENGINE_EXPORTS');scene.collection.children.link(export)
manifest=dict(source_blend=str(OUT/'DungeonWorkshopFabTools.blend'),objects=[],placements=[],
              source_listing='https://www.fab.com/listings/eba94efa-c186-4004-83ba-d420d35f8f90',
              source_seller='Vladyslav Chykunov',material_aliases={},tests_run=False,renders_run=False,
              textures_ready=False)
old=json.loads((PREV/'Authored/manifest.json').read_text())
manifest['material_aliases'].update(old['material_aliases'])
assets=json.loads((PREV/'Receipts/asset-import.json').read_text())
manifest['material_aliases'].update({'WSFinish_'+k:v for k,v in assets['materials'].items()})

def export_mesh(ob,name,actor=None,replace=False):
    active(ob)
    for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    tri=ob.modifiers.new('Final tangent triangulation','TRIANGULATE');tri.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=tri.name)
    ob.name=name
    path=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
    entry=dict(name=name,fbx=str(path),materials=[re.sub(r'[.]\d{3}$','',m.name) for m in ob.data.materials],
               triangles=len(ob.data.polygons),collision=False,cast_shadow=True,actor=actor,replace=replace)
    manifest['objects'].append(entry)
    return entry

templates={};source_metrics={}
for row in json.loads((ROOT/'Receipts/source-inputs.json').read_text())['objects']:
    path=ROOT/'Sources'/row['file'];before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path),use_custom_normals=True)
    ob=next(o for o in set(bpy.data.objects)-before if o.type=='MESH')
    active(ob);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    mins=Vector([min(v.co[i] for v in ob.data.vertices) for i in range(3)])
    maxs=Vector([max(v.co[i] for v in ob.data.vertices) for i in range(3)])
    center=(mins+maxs)*.5
    for v in ob.data.vertices:v.co-=center
    name='Hammer' if row['file']=='Hummer.fbx' else path.stem
    ob.name='Source_'+name
    for coll in list(ob.users_collection):coll.objects.unlink(ob)
    source.objects.link(ob)
    ob.data.materials.clear();ob.data.materials.append(atlas)
    for f in ob.data.polygons:f.material_index=0
    # Keep the atlas and source profile intact. Angle-limited radii add real edge highlights.
    mod=ob.modifiers.new('Small manufactured edge radii','BEVEL')
    mod.width={'Hand_Saw':.00025,'Wrench':.00045,'Nail_Puller':.00065,'Hammer':.00065}.get(name,.00045)
    mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.40;mod.harden_normals=True
    mod.use_clamp_overlap=True
    normal=ob.modifiers.new('Weighted machined surface normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=35
    templates[name]=ob
    source_metrics[name]=dict(center=list(center),bounds=[list(mins-center),list(maxs-center)])
    evaluated=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
    copy=bpy.data.objects.new('SM_WSFab_'+name,mesh);export.objects.link(copy)
    export_mesh(copy,'SM_WSFab_'+name)
    copy.hide_render=True;copy.hide_set(True)
    ob.hide_render=True;ob.hide_set(True)

placed=bpy.data.collections.new('WORKSHOP_TOOL_PLACEMENT');scene.collection.children.link(placed)
wall_specs=[
    ('Nail_Puller',1.77,1.715,-2.0),('Bolt_Cutter',2.075,1.70,1.5),
    ('Pipe_Wrench',2.405,1.79,-3.0),('Adjustable_Wrench',2.675,1.81,2.0),
    ('Hammer',2.980,1.79,-3.0),('Pliers',3.215,1.82,4.0),
    ('Wrench',3.405,1.805,-2.0),('Screwdriver',3.640,1.78,3.5),
    ('Hand_Saw',2.08,1.29,-88.0)]

def place(name,zone,c,basis,angle=0):
    original=templates[name];ob=original.copy();ob.data=original.data.copy();placed.objects.link(ob)
    ob.name=zone+'_'+name;ob.hide_render=False;ob.hide_set(False)
    rotation=Matrix(basis).transposed().to_4x4()@Matrix.Rotation(math.radians(angle),4,'Z')
    local=Matrix.Translation(Vector(c))@rotation
    ob.matrix_world=WORLD@local
    # Preserve the exact export convention by exporting a placed copy as world-baked geometry.
    dg=bpy.context.evaluated_depsgraph_get()
    me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
    me.transform(ob.matrix_world)
    baked=bpy.data.objects.new('Placed_'+zone+'_'+name,me);export.objects.link(baked)
    entry=export_mesh(baked,'SM_WSFab_'+zone+'_'+name,'DGN_WSFab_'+zone+'_'+name)
    baked.hide_render=True;baked.hide_set(True)
    manifest['placements'].append(dict(name=name,zone=zone,center=list(c),angle=angle,asset=entry['name']))
    return local

for name,y,z,angle in wall_specs:
    # Wall faces local +X. Source +Z faces the viewer, source +Y is tool length.
    # 4 mm clearance to the actual back surface, not a constant centre offset.
    thickness=-source_metrics[name]['bounds'][0][2]
    cx=.177+thickness+.004
    local=place(name,'Wall',(cx,y,z),((0,1,0),(0,0,1),(1,0,0)),angle)
    span=source_metrics[name]['bounds'][1][1]-source_metrics[name]['bounds'][0][1]
    if name=='Hand_Saw':
        anchors=[(-.023,-span*.35),(.017,span*.34)]
    elif name in ('Wrench','Adjustable_Wrench'):
        anchors=[(0,span*.5-.025)]
    elif name=='Nail_Puller':anchors=[(0,span*.29)]
    else:anchors=[(-.022,span*.27),(.022,span*.27)]
    for ax,ay in anchors:
        p=local@Vector((ax,ay,0))
        box('Mounts','Small folded hook mounting tab',(.179,p.y,p.z-.012),(.0025,.018,.036),'SheetPaint',.0012)
        sweep('Mounts','Bent steel retaining hook',[(.177,p.y,p.z),(.185,p.y,p.z),
              (cx+thickness*.5,p.y,p.z-.006),(cx+thickness+.006,p.y,p.z-.002),
              (cx+thickness+.007,p.y,p.z+.010)],.0022,'GroundSteel',20)
        cylinder('Mounts','Hook fastening screw',(.180,p.y,p.z-.022),(.183,p.y,p.z-.022),.0033,'GroundSteel',24)

# Different purposeful working positions, leaving the vise and parts tray accessible.
for name,x,y,angle in [('Wrench',1.12,3.65,-17),('Screwdriver',1.43,3.55,23),
                      ('Pliers',.58,3.30,-28),('Chisel',.47,2.66,8)]:
    lo=source_metrics[name]['bounds'][0][2]
    place(name,'Bench',(x,y,.942-lo+.001),((1,0,0),(0,1,0),(0,0,1)),angle)

# Retain the detailed vise, ratchet, sockets, oil cans, caliper and parts tray.
with bpy.data.libraries.load(str(PREV/'Authored/DungeonWorkshopSurfaceDetails.blend'),link=False) as (src,dst):
    dst.collections=[n for n in src.collections if n.startswith(('SOURCE_BenchDetail','SOURCE_ToolMarkings'))]
for col in dst.collections:
    if not col.objects:continue
    scene.collection.children.link(col);col.hide_viewport=False;col.hide_render=False
    if col.name.startswith('SOURCE_BenchDetail'):
        removals=('Continuous drop-forged combination wrench','Moulded six-lobe screwdriver grip',
                  'Grip collar and finger stop','Hardened screwdriver shaft','Ground slotted blade',
                  'Recessed grip fluting','Forged pliers half','Tapered dipped grip',
                  'Cutting jaw serration','Flush joint rivet','Rivet inset')
        retained=[o for o in col.objects if not o.name.startswith(removals)]
        for ob in list(col.objects):
            if ob not in retained:bpy.data.objects.remove(ob,do_unlink=True)
        group='BenchRetained';actor='DGN_Room_WS_BenchDetail'
    else:
        # Original five size tags described a uniform wrench set; preserve drawer/header/socket labels.
        retained=[]
        for ob in list(col.objects):
            pts=[ob.matrix_world@v.co for v in ob.data.vertices]
            cz=sum(p.z for p in pts)/len(pts) if pts else 0
            if 1.99<cz<2.04:bpy.data.objects.remove(ob,do_unlink=True)
            else:retained.append(ob)
        group='LabelsRetained';actor='DGN_WSTools_ToolMarkings'
    dg=bpy.context.evaluated_depsgraph_get();copies=[]
    for ob in retained:
        me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
        if any(m.type=='REMESH' for m in ob.modifiers):
            uv=me.uv_layers.active or me.uv_layers.new(name='UVMap')
            for face in me.polygons:
                axis=max(range(3),key=lambda a:abs(face.normal[a]));ds=[a for a in range(3) if a!=axis]
                for li in face.loop_indices:
                    p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[ds[0]]/.18,p[ds[1]]/.18)
        me.transform(WORLD@ob.matrix_world)
        new=bpy.data.objects.new(ob.name+'_retained',me);export.objects.link(new);copies.append(new)
    active(copies[0])
    for ob in copies:ob.select_set(True)
    bpy.ops.object.join();export_mesh(copies[0],'SM_WSFab_'+group,actor,True)
    col.hide_render=True;col.hide_viewport=True

dg=bpy.context.evaluated_depsgraph_get();copies=[]
for ob in PARTS['Mounts']:
    me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
    me.transform(WORLD@ob.matrix_world)
    new=bpy.data.objects.new(ob.name+'_export',me);export.objects.link(new);copies.append(new)
    ob.hide_render=True;ob.hide_set(True)
active(copies[0])
for ob in copies:ob.select_set(True)
bpy.ops.object.join();export_mesh(copies[0],'SM_WSFab_Mounts','DGN_WSFab_Mounts')
manifest['hide_actors']=['DGN_Room_WS_HandTools','DGN_WSTools_ToolWear']
manifest['source_metrics']=source_metrics
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonWorkshopFabTools.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('FAB_TOOLS_AUTHORED '+json.dumps(dict(assets=len(manifest['objects']),placed=len(manifest['placements']),textures_ready=False,renders_run=False)))
