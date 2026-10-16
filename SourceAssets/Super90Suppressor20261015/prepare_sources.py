"""Reuse the established exterior authoring and background asset pipeline."""
from pathlib import Path
O=Path(__file__).parent
bird=O.parent/'Super90Birdcage20261015'
choke=O.parent/'Super90Choke20261015'
for name in ('author_icon.py','package_runtime.py','install_assets.py','install.ps1','build_game.ps1','build_editor.ps1'):
    text=(bird/name).read_text(encoding='utf-8-sig')
    text=text.replace('Super90Birdcage20261015','Super90Suppressor20261015')
    text=text.replace('shotgun_birdcage_flash_hider','shotgun_suppressor')
    text=text.replace('Birdcage','Suppressor').replace('birdcage','suppressor').replace('BIRDCAGE','SUPPRESSOR')
    if name=='install.ps1':
        text=text.replace('install_assets.py','install_all.py').replace('install_bridge_03.json','install_bridge_01.json')
    if name=='install_assets.py':
        text=text.replace("('Muzzle',7.4),('AimGuide',8.4)","('Muzzle',27.8),('AimGuide',28.8)")
        text=text.replace("'muzzle_socket_cm':[7.4,0,0]","'muzzle_socket_cm':[27.8,0,0]")
    (O/name).write_text(text,encoding='utf-8-sig' if name.endswith('.ps1') else 'utf-8')

text=(choke/'author_model.py').read_text(encoding='utf-8')
text=text[:text.index('model_collection = collection')]
text=text.replace('Choke_Box01','Suppressor01').replace('Choke','Suppressor').replace('choke','suppressor')
text=text.replace("shutil.copy2(SOURCE_IMAGE, REFERENCE / 'user_shape_reference.png')",'')
text=text.replace("'body_start': .013","'body_start': .024").replace("'body_end': .248","'body_end': .278")
text=text.replace("'half_width': .023","'half_width': .029").replace("'half_height': .032","'half_height': .041")
text=text.replace("'vertical_center': -.012","'vertical_center': -.0225")
text=text.replace("'top_corner_radius': .010","'top_corner_radius': .012").replace("'bottom_corner_radius': .004","'bottom_corner_radius': .008")
text=text.replace("'body_seams': [.069, .122, .175, .238]","'body_seams': [.041, .252, .268]")
text=text.replace("(.0140, .0131, 3)","(.018, .0148, 3), (.026, .0148, 3)")
text=text.replace("z = -.034","z = -.050")
text=text.replace("shader = material.node_tree.nodes.get('Principled BSDF')", """nodes=material.node_tree.nodes;nodes.clear()
    shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial')
    material.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface'])""")
text += '''
def side_details(target):
    result=[]
    # Shallow external styling ribs and identification panel; no internal assembly.
    for side in (-1,1):
        for index,z in enumerate((-.015,-.024,-.033)):
            bpy.ops.mesh.primitive_cube_add(size=1,location=(.145,side*.0288,z))
            obj=bpy.context.object;obj.name=f'Suppressor_SideRib_{side}_{index}'
            obj.dimensions=(.172,.0014,.0020)
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
            obj.data.materials.append(MATERIALS[1])
            bevel=obj.modifiers.new('Soft machined rib edges','BEVEL');bevel.width=.00065;bevel.segments=3
            obj.modifiers.new('Planar rib normals','WEIGHTED_NORMAL')
            result.append(obj)
    return result

model_collection=collection('01_Editable_Exterior')
parts=author_parts(128,model_collection)+side_details(model_collection)
for obj in parts:
    obj['asset_family']='Shared_Shotgun_Muzzle'
    obj['variant']='shotgun_suppressor'
lods={'LOD0':export_mesh(parts,'LOD0')}
for level,count in [('LOD1',64),('LOD2',32)]:
    c=collection('Source_'+level)
    simple=author_parts(count,c)+side_details(c)
    lods[level]=export_mesh(simple,level)
    for obj in simple:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(c)
helpers=collection('02_Assembly_Markers')
for name,x in [('Mount_Origin',0),('Visual_Front',.278)]:
    marker=bpy.data.objects.new(name,None);marker.location=(x,0,0)
    marker.empty_display_type='ARROWS';marker.empty_display_size=.02
    helpers.objects.link(marker);marker.hide_render=True
helpers.hide_viewport=True
select(parts)
source_file=ROOT/'ShotgunSuppressor01_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source_file))
report={'status':'model_and_exports_saved','editable_source':str(source_file),
    'parameters_in_blender_metres':PARAMS,'lods':lods,
    'materials':[{'name':n,'base_color_linear':c,'roughness':r,'metallic':m} for n,c,r,m in MATERIAL_RECIPES],
    'tip_cm':27.8,'source_reference':'Original cosmetic shotgun suppressor exterior, shared SUPER90 visual seat',
    'normal_texture':None,'engine_imported':False,'runtime_tested':False}
(ROOT/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPPRESSOR_MODEL_SAVED',json.dumps(lods),flush=True)
'''
(O/'author_model.py').write_text(text,encoding='utf-8')
