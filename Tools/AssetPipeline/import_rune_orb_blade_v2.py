"""Import the slender reference-derived blade and blue shatter fragment.
Editor authoring only: no PIE, screenshots, or validation rendering.
"""
import json
from pathlib import Path
import unreal

if str(Path(unreal.Paths.project_dir()).resolve()).replace('\\','/').lower() != 'd:/fps3d/fpsgame':
    raise RuntimeError('Expected the FPSGAME project for this import')

SOURCE = Path('D:/FPS3D/FPSGAME/SourceAssets/RuneOrbBlade20260921')
DEST = '/Game/Weapons/RuneOrbBlade20260921'
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary

def color(m, value):
    e = lib.create_material_expression(m, unreal.MaterialExpressionConstant3Vector)
    e.constant = unreal.LinearColor(*value, 1)
    return e

def scalar(m, value):
    e = lib.create_material_expression(m, unreal.MaterialExpressionConstant)
    e.r = value
    return e

def material(name, base, glow, rim, roughness):
    m = unreal.load_asset(DEST+'/'+name) or tools.create_asset(name,DEST,unreal.Material,unreal.MaterialFactoryNew())
    for e in list(lib.get_material_expressions(m)):
        lib.delete_material_expression(m,e)
    m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('two_sided',False)
    lib.connect_material_property(color(m,base),'',unreal.MaterialProperty.MP_BASE_COLOR)
    lib.connect_material_property(scalar(m,roughness),'',unreal.MaterialProperty.MP_ROUGHNESS)
    lib.connect_material_property(scalar(m,.12),'',unreal.MaterialProperty.MP_METALLIC)
    # View-angle rim follows the actual bevels; no world-space noise swimming on flight.
    fresnel=lib.create_material_expression(m,unreal.MaterialExpressionFresnel)
    fresnel.set_editor_property('exponent',3.2)
    multiply=lib.create_material_expression(m,unreal.MaterialExpressionMultiply)
    lib.connect_material_expressions(fresnel,'',multiply,'A')
    lib.connect_material_expressions(color(m,rim),'',multiply,'B')
    add=lib.create_material_expression(m,unreal.MaterialExpressionAdd)
    lib.connect_material_expressions(color(m,glow),'',add,'A')
    lib.connect_material_expressions(multiply,'',add,'B')
    lib.connect_material_property(add,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m

materials = {
    'M_RuneBlade_Crystal': material('M_RuneBlade_Crystal',(.008,.10,.32),(.025,.25,.90),(.06,.40,.85),.20),
    'M_RuneBlade_Edge': material('M_RuneBlade_Edge',(.04,.38,.68),(.20,1.40,2.0),(.08,.45,.8),.18),
    'M_RuneBlade_Core': material('M_RuneBlade_Core',(.48,.86,1),(1.92,3.44,4),(.10,.15,.20),.20),
    'M_RuneBlade_Shards': material('M_RuneBlade_Shards',(.015,.16,.48),(.077,.836,2.2),(.12,.6,1.0),.16),
}

report={}
for name in ('SM_RuneOrbBlade','SM_RuneBladeShard'):
    task=unreal.AssetImportTask()
    task.filename=str(SOURCE/(name+'.fbx'))
    task.destination_path=DEST
    task.destination_name=name
    task.automated=True
    task.replace_existing=True
    task.save=True
    opts=unreal.FbxImportUI()
    opts.import_mesh=True
    opts.import_materials=True
    opts.import_textures=False
    opts.import_as_skeletal=False
    opts.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
    opts.automated_import_should_detect_type=False
    opts.static_mesh_import_data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    opts.static_mesh_import_data.combine_meshes=True
    opts.static_mesh_import_data.generate_lightmap_u_vs=True
    opts.static_mesh_import_data.auto_generate_collision=False
    task.options=opts
    tools.import_asset_tasks([task])
    mesh=unreal.load_asset(DEST+'/'+name)
    if not isinstance(mesh,unreal.StaticMesh):
        raise RuntimeError('Mesh import failed: '+name)
    slots=[]
    for i,slot in enumerate(mesh.static_materials):
        key=str(slot.material_slot_name)
        if key not in materials:
            raise RuntimeError('Unexpected material slot: '+key)
        mesh.set_material(i,materials[key])
        slots.append(key)
    ns=mesh.get_editor_property('nanite_settings');ns.enabled=False
    mesh.set_editor_property('nanite_settings',ns)
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    report[name]={'path':mesh.get_path_name(),'slots':slots,'bounds':str(mesh.get_bounds()),'triangles':mesh.get_num_triangles(0)}

# Native defaults are protected and the actor layout changed; normal rebuild/reload
# activates these packages. Do not mutate live CDOs through a reflection workaround.
report['native_reload_required']=True

(SOURCE/'import-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('RUNE_BLADE_V2_IMPORTED '+json.dumps(report))
