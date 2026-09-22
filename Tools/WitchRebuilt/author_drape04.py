"""Restore one continuous skirt anchor and add an upper-garment simulation proxy."""
import bpy,bmesh,json,sys
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'DrapeGrip20260922'
sys.path.insert(0,str(Path(__file__).parent))
def apply(rig):
    OUT.mkdir(parents=True,exist_ok=True)
    lower=bpy.data.objects['Witch_OriginalRobe_Render'];proxy=bpy.data.objects['WitchRebuilt_SimulationProxy']
    # A continuous robe cannot be driven as separate trouser legs. Waist anchors
    # plus cloth/body collisions control the lower sheet; no calf/foot targets.
    for obj in (lower,proxy):
        obj.vertex_groups.clear();g=obj.vertex_groups.new(name='pelvis')
        g.add(list(range(len(obj.data.vertices))),1.,'REPLACE')
    proxy.data.materials.clear();proxy.data.materials.append(bpy.data.materials.new('WitchRebuilt_LowerSimulationProxy'))
    existing=bpy.data.objects.get('WitchRebuilt_UpperSimulationProxy')
    if existing:bpy.data.objects.remove(existing,do_unlink=True)
    upper=bpy.data.objects['Witch_UpperRobe'];up=upper.copy();up.data=upper.data.copy();up.name='WitchRebuilt_UpperSimulationProxy'
    bpy.context.collection.objects.link(up)
    # Decimation is confined to the hidden simulation support. Render UVs and
    # sleeve/hood silhouette stay in the original upper garment.
    bpy.ops.object.select_all(action='DESELECT');up.hide_set(False);up.select_set(True);bpy.context.view_layer.objects.active=up
    for mod in list(up.modifiers):up.modifiers.remove(mod)
    dec=up.modifiers.new('SimulationDensity','DECIMATE');dec.ratio=.075;dec.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=dec.name)
    bm=bmesh.new();bm.from_mesh(up.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00005)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(up.data);bm.free()
    arm=up.modifiers.new('WitchRig','ARMATURE');arm.object=rig
    up.data.materials.clear();up.data.materials.append(bpy.data.materials.new('WitchRebuilt_UpperSimulationProxy'))
    up.hide_render=True;up.hide_set(True)
    rig['drape_revision']='Drape04'
    (OUT/'drape_source.json').write_text(json.dumps({'lower_render_vertices':len(lower.data.vertices),
        'lower_proxy_vertices':len(proxy.data.vertices),'upper_proxy_vertices':len(up.data.vertices),
        'lower_skin':'pelvis only; no separate left/right leg pulling','upper_skin':'Original sleeve/torso support, physical loose cloth',
        'actor_scale_changed':False},indent=2),encoding='utf-8')

def export(rig,vertex_colors=False):
    for include,name in [(False,'SK_WitchRebuilt.fbx'),(True,'SK_WitchRebuilt_ClothBuildSource.fbx')]:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj==rig or (obj.type=='MESH' and ('SimulationProxy' not in obj.name or include)):
                obj.hide_set(False);obj.select_set(True)
        bpy.context.view_layer.objects.active=rig
        bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery'/name),use_selection=True,object_types={'ARMATURE','MESH'},
            add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=False,
            axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',use_mesh_modifiers=True,mesh_smooth_type='FACE',
            **({'colors_type':'LINEAR','prioritize_active_color':True} if vertex_colors else {}))
    for obj in bpy.context.scene.objects:
        if 'SimulationProxy' in obj.name:obj.hide_render=True;obj.hide_set(True)

if __name__=='__main__':
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Before/Authoring/WitchRebuilt_Master.blend'))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST'
    apply(rig);export(rig);rig.data.pose_position='POSE'
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Master.blend'))
