"""Import the approved cosmetic into an isolated project before scoped publication."""
import json
import os
from pathlib import Path
import unreal as u

art = Path(__file__).resolve().parent
batch = Path(os.environ['CRESCENT_BATCH'])
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve() != (batch/'Host').resolve():
    raise RuntimeError('Use the isolated authoring project')
base = '/Game/Weapons/TacticalHatchet20261101'
root = base + '/ModulesV1/SwiftCrescentLeaf'
old = base + '/ModulesV1/Materials/M_TacticalHatchet_Head_SwiftCrescent_R4'
old_marks = base + '/CommonRunes20261104/Materials/'
A = u.AssetToolsHelpers.get_asset_tools()
E = u.MaterialEditingLibrary
L = u.EditorAssetLibrary
saved = []

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed '+asset.get_path_name())
    saved.append(asset.get_path_name())

def imported(file, folder, options=None):
    task = u.AssetImportTask()
    task.set_editor_properties(dict(filename=str(file),destination_path=folder,destination_name=file.stem,
                                    automated=True,replace_existing=True,save=False))
    if options:
        task.options=options
        task.factory=u.FbxFactory()
    A.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import failed '+str(file))
    return L.load_asset(folder+'/'+file.stem)

def duplicate(source,name):
    dest=root+'/Materials/'+name
    result=L.load_asset(dest) if L.does_asset_exist(dest) else A.duplicate_asset(name,root+'/Materials',L.load_asset(source))
    if not result:
        raise RuntimeError('Cannot author '+dest)
    return result

textures={}
for file in sorted((art/'Textures').glob('*.png')):
    role=file.stem.split('_')[-1]
    t=imported(file,root+'/Textures')
    normal=role=='Normal'
    t.set_editor_properties(dict(srgb=role=='BaseColor',never_stream=False,max_texture_size=2048,
        lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_WEAPON,
        compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else
            u.TextureCompressionSettings.TC_BC7 if role=='BaseColor' else u.TextureCompressionSettings.TC_MASKS))
    if normal:
        t.set_editor_property('flip_green_channel',True)
    if role.startswith('Rune'):
        t.set_editor_properties(dict(address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,
                                     lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR))
    save(t)
    textures[role]=t

def surface(source,name,marked):
    mat=duplicate(source,name)
    props=('MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_METALLIC','MP_FRONT_MATERIAL','MP_AMBIENT_OCCLUSION')
    queue=[E.get_material_property_input_node(mat,getattr(u.MaterialProperty,p)) for p in props]
    seen=set()
    changed=set()
    while queue:
        node=queue.pop()
        if not node or node.get_path_name() in seen:
            continue
        seen.add(node.get_path_name())
        queue.extend(E.get_inputs_for_material_expression(mat,node))
        if isinstance(node,u.MaterialExpressionTextureSample) and node.texture:
            previous=node.texture.get_name()
            role=previous.rsplit('_',1)[-1]
            if role in textures and 'SwiftCrescent' in previous:
                node.set_editor_property('texture',textures[role])
                changed.add(role)
    expected={'BaseColor','Normal','ORM'} | ({'RuneWing'} if marked else set())
    if not expected.issubset(changed):
        raise RuntimeError('Incomplete new surface '+name+' '+str(changed))
    if marked:
        L.set_metadata_tag(mat,'OriginalPBR',root+'/Materials/M_TacticalHatchet_Head_SwiftCrescent_Leaf')
    L.set_metadata_tag(mat,'ModelRevision','SwiftCrescentLeaf20261122')
    E.recompile_material(mat)
    save(mat)
    return mat

mat=surface(old,'M_TacticalHatchet_Head_SwiftCrescent_Leaf',False)
rune=surface(old_marks+'M_HatchetMark_SwiftCrescent','M_HatchetMark_SwiftCrescent_Leaf',True)
for kind in ('RuneWing','RuneKnot','RunePeaks'):
    instance=duplicate(old_marks+'MI_HatchetMark_SwiftCrescent_'+kind,'MI_HatchetMark_SwiftCrescent_Leaf_'+kind)
    E.set_material_instance_parent(instance,rune)
    E.set_material_instance_texture_parameter_value(instance,'RuneMask',textures[kind])
    E.update_material_instance(instance)
    save(instance)

ui=u.FbxImportUI()
ui.set_editor_properties(dict(automated_import_should_detect_type=False,import_mesh=True,import_as_skeletal=False,
                             import_textures=False,import_materials=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH))
ui.static_mesh_import_data.set_editor_properties(dict(combine_meshes=True,auto_generate_collision=False,
    generate_lightmap_u_vs=False,convert_scene=True,convert_scene_unit=True,
    normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS))
mesh=imported(art/'Export/SM_TacticalHatchet_Head_SwiftCrescent_Leaf.fbx',root,ui)
slot,=mesh.static_materials
slot.set_editor_property('material_slot_name',u.Name(mat.get_name()))
mesh.set_editor_property('static_materials',[slot])
mesh.set_material(0,mat)
nanite=mesh.get_editor_property('nanite_settings')
nanite.enabled=True
mesh.set_editor_property('nanite_settings',nanite)
if not u.TacticalHatchetImportLibrary.finalize_mesh(mesh):
    raise RuntimeError('Unable to save authored tangent basis')
L.set_metadata_tag(mesh,'ModelRevision','SwiftCrescentLeaf20261122')
save(mesh)
(batch/'authored-head.json').write_text(json.dumps(saved,indent=2),encoding='utf8')
