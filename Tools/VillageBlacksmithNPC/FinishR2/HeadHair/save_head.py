"""Use the original head-authoring functions with versioned R2 material imports in an empty host."""
import ast,json
from pathlib import Path
import unreal as u
PROJECT=Path(__file__).resolve().parents[4]
ROOT=PROJECT/'SourceAssets/VillageBlacksmithNPC20261118'
OUT=ROOT/'FinishR2/HeadHair'
DEST='/Game/Characters/VillageBlacksmithNPC20261118'
PARTS=DEST+'/HeadFinishR2'
legacy=PROJECT/'Tools/VillageBlacksmithNPC/HeadHair/save_meshes.py'
# Reuse the shipping mesh/LOD builder and its material settings, but give this revision distinct assets.
tree=ast.parse(legacy.read_text(encoding='utf-8-sig'))
functions=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.Import,ast.ImportFrom))]
exec(compile(ast.Module(body=functions,type_ignores=[]),str(legacy),'exec'),globals())
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
owned=[]
t=OUT/'Textures'
face=material('M_Smith_MeshyFace_R2',texture(t/'T_Smith_Face_BC.png','color'),texture(t/'T_Smith_Face_N.png','normal'),texture(t/'T_Smith_Face_R.png','rough'))
bc=L.get_material_property_input_node(face,u.MaterialProperty.MP_BASE_COLOR)
for pin,hair_value,skin_value in [(u.MaterialProperty.MP_SPECULAR,.24,.32),(u.MaterialProperty.MP_OPACITY,1.,.70)]:
    blend=L.create_material_expression(face,u.MaterialExpressionLinearInterpolate)
    blend.set_editor_property('const_a',hair_value);blend.set_editor_property('const_b',skin_value)
    L.connect_material_expressions(bc,'A',blend,'Alpha')
    if not L.connect_material_property(blend,'',pin):raise ValueError('Cannot apply crown material response.')
L.recompile_material(face);save(face)
neck=u.load_asset(DEST+'/HeadParts/M_Smith_NativeNeck')
if not neck:raise ValueError('Cannot bind the saved nape-finished material.')
r4=json.loads((PROJECT/'SourceAssets/JasonStrong20261117/R4_PoseRefined/variant_saved.json').read_text())
source=u.load_asset(r4['asset'])
ref,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise ValueError('R4 bindings unavailable.')
head=write_skeletal('face.json.gz','SK_Smith_Head',{'SmithMeshyFace':face,'SmithNativeNeck':neck},ref,source)
(OUT/'saved.json').write_text(json.dumps({'packages':owned,'head':head.get_path_name(),'skeleton':head.skeleton.get_path_name(),'lods':u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(head)},indent=2))
