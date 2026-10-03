"""Apply the matching sampler types to the private authored texture inputs."""
import importlib.util,json
from pathlib import Path
import unreal as u
O=Path(__file__).parent
spec=importlib.util.spec_from_file_location('pv_surface_contract',O/'surface_contract.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
if Path(u.Paths.project_dir()).resolve()!=C.P.resolve():raise RuntimeError('Wrong production project')
targets=set(C.MATERIAL_REMAP.values())
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets&dirty:raise RuntimeError('Preserve unsaved 2011 private surface materials')
saved=[]
for path in targets:
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing saved private surface '+path)
    for node in u.MaterialEditingLibrary.get_material_expressions(mat):
        if not isinstance(node,u.MaterialExpressionTextureSample) or not node.texture:continue
        source=node.texture.get_path_name().split('.')[0]
        if not source.startswith(C.D+'/Textures/'):continue
        kind=source.rsplit('_',1)[1]
        node.sampler_type={'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,
            'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,
            'Roughness':u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE,
            'ORM':u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR}[kind]
    u.MaterialEditingLibrary.recompile_material(mat)
    if not u.EditorLoadingAndSavingUtils.save_packages([mat.get_outermost()],False):raise RuntimeError('Private surface material save failed '+path)
    saved.append(mat.get_path_name())
rpath=O/'import_receipt.json';r=json.loads(rpath.read_text(encoding='utf8'))
r['sampler_types_applied']=saved
rpath.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
print('PIT_VIPER_PRIVATE_TEXTURE_SAMPLERS_SAVED',len(saved),flush=True)
