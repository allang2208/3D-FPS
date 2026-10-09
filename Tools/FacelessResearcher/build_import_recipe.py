"""Prepare independent researcher material/mesh import and native clip reuse."""
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME')
s=(BASE/'Tools/FacelessSecurity/import_assets.py').read_text(encoding='utf-8')
s=s.split('clips={}')[0]
s=s.replace('FacelessSecurity20261008/V01','FacelessResearcher20261009/V01')
s=s.replace('FacelessSecurity','FacelessResearcher').replace('Security_','Researcher_').replace('T_FS1_','T_FRS1_').replace('M_FS1_','M_FRS1_')
s=s.replace("'Uniform'","'Coat'").replace("'Skin','Coat','Trousers','Trim','Hardware','Insignia','Leather'","'Skin','Coat','Trousers','Trim','Hardware','Leather'")
s=s.replace('User Meshy athletic male GLB; independent local security uniform; native humanoid rig','User reduced Meshy female GLB; independent fitted lab coat and trousers; original Nurse skeleton')
s=s.replace("data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS", "data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS\ndata.set_editor_property('import_morph_targets',True)")
s=s.replace("MEL.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)","MEL.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);mat.set_editor_property('used_with_morph_targets',True)")
guard="\nif '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():\n    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is active; researcher import not started')\n"
s=s.replace("LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary","LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary"+guard)
tail=(BASE/'Tools/FacelessResearcher/import_tail.py').read_text(encoding='utf-8')
(BASE/'Tools/FacelessResearcher/import_assets.py').write_text(s+'\n'+tail,encoding='utf-8')
common=s[:s.index('skeleton=copy_asset(')]
cut=s.index("u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')")
context="""
skeleton=u.load_asset(DEST+'/SKEL_FacelessResearcher')
physics=u.load_asset(DEST+'/PA_FacelessResearcher')
materials={'Researcher_'+f:u.load_asset(DEST+'/Materials/M_FRS1_'+f) for f in ['Skin','Coat','Trousers','Trim','Hardware','Leather']}
"""
(BASE/'Tools/FacelessResearcher/import_materials.py').write_text(s[:cut]+"\nprint('RESEARCHER_MATERIALS_SAVED',flush=True)\n",encoding='utf-8')
loop="[('outfit','SK_FacelessResearcher_V01'),('clothing','SK_FacelessResearcher_Clothing_V01'),('body','SK_FacelessResearcher_Body_V01')]"
for role,name in [('outfit','SK_FacelessResearcher_V01'),('clothing','SK_FacelessResearcher_Clothing_V01'),('body','SK_FacelessResearcher_Body_V01')]:
    stage=s[cut:].replace(loop,repr([(role,name)]))
    (BASE/('Tools/FacelessResearcher/import_mesh_'+role+'.py')).write_text(common+context+stage+"\nprint('RESEARCHER_MESH_SAVED '+"+repr(role)+",flush=True)\n",encoding='utf-8')
load_meshes="\nmeshes={r:u.load_asset(DEST+'/'+n) for r,n in "+loop+"}\n"
(BASE/'Tools/FacelessResearcher/import_blueprint.py').write_text(common+context+load_meshes+tail,encoding='utf-8')
print('Researcher import recipe saved')
