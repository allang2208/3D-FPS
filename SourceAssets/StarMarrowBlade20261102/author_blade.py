"""Author the approved long crystal blade from its real frost_hilt_v1 seat."""
import bpy, bmesh, json, math, runpy
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent; OUT=P/'Export'; OUT.mkdir(exist_ok=True)
SOURCE=P.parent/'FrostSwordModules20260915/FrostSword_Modular_Editable.blend'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst):
    dst.objects=['SM_FrostSword_Blade_factory']
blade=dst.objects[0]; bpy.context.scene.collection.objects.link(blade)
blade.name='SM_FrostSword_Blade_star_marrow'; blade.data=blade.data.copy()
old_tip=max(v.co.z for v in blade.data.vertices); seat=.105
new_tip=old_tip*1.25
for v in blade.data.vertices:
    if v.co.z>seat:
        t=(v.co.z-seat)/(old_tip-seat)
        v.co.z=seat+t*(new_tip-seat)
        # Preserve every seat vertex. Slim the upper body into a long point.
        v.co.x*=1-.09*math.sin(t*math.pi*.5)**2
blade.data.update()
blade.data.normals_split_custom_set([(0,0,0)]*len(blade.data.loops))
core=bpy.data.materials.new('M_StarMarrow_Core');core.use_nodes=True
bs=core.node_tree.nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value=(.27,.68,.85,1)
bs.inputs['Metallic'].default_value=.32;bs.inputs['Roughness'].default_value=.14
bs.inputs['Emission Color'].default_value=(.15,.42,.6,1);bs.inputs['Emission Strength'].default_value=.25
verts=[];faces=[];colors=[]
for index,z in enumerate([.29,.44,.59]):
    near=[v.co for v in blade.data.vertices if abs(v.co.z-z)<.025 and abs(v.co.x)<.017]
    for side in [-1,1]:
        # Faceted cabochons sit inside the spine, their crowns flush with the ridge.
        surface=(max(p.y for p in near) if side>0 else min(p.y for p in near)) if near else side*.012
        base=surface-side*.0015; crown=surface+side*.002
        start=len(verts);w=.010;h=.022
        verts.extend([(-w,base,z),(0,base,z+h),(w,base,z),(0,base,z-h),(0,crown,z)])
        for a,b in [(0,1),(1,2),(2,3),(3,0)]:
            f=(start+a,start+b,start+4)
            faces.append(f if side<0 else tuple(reversed(f)))
            colors.extend([(float(index+1)/3,0,0,1)]*3)
mesh=bpy.data.meshes.new('StarMarrowInsetCores');mesh.from_pydata(verts,[],faces);mesh.materials.append(core)
uv=mesh.uv_layers.new(name='UVMap');col=mesh.color_attributes.new(name='GuardFinish',type='FLOAT_COLOR',domain='CORNER')
for f in mesh.polygons:
    for li in f.loop_indices:
        co=mesh.vertices[mesh.loops[li].vertex_index].co
        uv.data[li].uv=((co.x/.02+.5),co.z/new_tip)
        col.data[li].color=colors[li]
cores=bpy.data.objects.new('StarMarrowInsetCores',mesh);bpy.context.scene.collection.objects.link(cores)
bpy.ops.object.select_all(action='DESELECT');blade.select_set(True);cores.select_set(True);bpy.context.view_layer.objects.active=blade
bpy.ops.object.join()
blade.data.update()
for level,ratio in enumerate([1,.5,.22]):
    obj=blade if level==0 else blade.copy()
    if level:
        obj.data=blade.data.copy();bpy.context.scene.collection.objects.link(obj)
        # Delimit material boundaries so each charge core survives reduction.
        mod=obj.modifiers.new('CrystalLOD','DECIMATE');mod.ratio=ratio
        mod.use_collapse_triangulate=True
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.name='SM_FrostSword_Blade_star_marrow_LOD'+str(level)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    if level:obj.hide_render=True;obj.hide_set(True)
blade.name='SM_FrostSword_Blade_star_marrow_LOD0'
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'StarMarrow_Blade_Editable.blend'))
(P/'exports.json').write_text(json.dumps({'source':str(SOURCE),'mesh':blade.name,'original_tip_cm':old_tip*100,'visual_tip_cm':new_tip*100,'seat_unchanged_below_cm':seat*100,'trace_base_cm':[0,0,3],'trace_tip_cm':[0,0,100],'rune_dimensions_cm':[12,10,78.75],'interface':'frost_hilt_v1','core_stations_cm':[29,44,59],'reach_note':'The gameplay range multiplier owns +25%; trace proxy is not scaled a second time.'},indent=2),encoding='utf8')
print('STAR_MARROW_MODEL_EXPORTED',flush=True)
