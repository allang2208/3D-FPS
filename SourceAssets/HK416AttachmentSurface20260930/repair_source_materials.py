"""Correct the attachment atlas assignment without changing geometry or UVs."""
import bpy,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'HK416Reworked20260930';B=O/'Before';B.mkdir(exist_ok=True)
auth_path=S/'authoring.json';auth=json.loads(auth_path.read_text())
mapping={'M_HK416_Laser_Grip':'Accs_1004','M_HK416_Flash_Light':'Accs_1001'}
if not (B/'authoring.json').exists():shutil.copy2(auth_path,B/'authoring.json')
auth['material_groups'].update(mapping);auth_path.write_text(json.dumps(auth,indent=2))
report={'materials':mapping,'parts':{},'geometry_changed':False,'uv_changed':False}
for part in ('vertical','flashlight','laser'):
    fbx=Path(auth['static'][part]['fbx']);file=fbx.with_name(fbx.stem+'_Editable.blend')
    for src in (fbx,file):
        dst=B/src.name
        if not dst.exists():shutil.copy2(src,dst)
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    with bpy.data.libraries.load(str(file),link=False) as (_,dst):dst.objects=list(_.objects)
    objects=[ob for ob in dst.objects if ob]
    for ob in objects:bpy.context.scene.collection.objects.link(ob)
    rows=[]
    for mat in list(bpy.data.materials):
        if mat.name not in mapping:continue
        group=mapping[mat.name];nodes=mat.node_tree.nodes;links=mat.node_tree.links
        bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
        bs.inputs['Emission Color'].default_value=(0,0,0,1)
        has_emission=False
        for node in list(nodes):
            if node.type!='TEX_IMAGE' or not node.image:continue
            old=Path(bpy.path.abspath(node.image.filepath));suffix=old.stem.split('_')[-1]
            replacement=S/'Original/textures'/(group+'_'+suffix+old.suffix)
            if not replacement.exists():
                if suffix!='emissive':raise RuntimeError(str(replacement))
                nodes.remove(node);continue
            node.image=bpy.data.images.load(str(replacement),check_existing=True)
            node.image.colorspace_settings.name='sRGB' if suffix in ('albedo','emissive') else 'Non-Color'
            rows.append({'material':mat.name,'channel':suffix,'image':str(replacement)})
            has_emission|=suffix=='emissive'
        emission=S/'Original/textures'/(group+'_emissive.jpg')
        if emission.exists() and not has_emission:
            tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(emission),check_existing=True);tex.image.colorspace_settings.name='sRGB'
            links.new(tex.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=.2
        mat['texture_group']=group
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=next(o for o in objects if o.type=='MESH')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    bpy.data.libraries.write(str(file),set(objects),fake_user=True)
    report['parts'][part]={'editable':str(file),'fbx':str(fbx),'textures':rows}
(O/'source_repair.json').write_text(json.dumps(report,indent=2));print('HK416_ATTACHMENT_SOURCE_MATERIALS_CORRECTED',flush=True)
