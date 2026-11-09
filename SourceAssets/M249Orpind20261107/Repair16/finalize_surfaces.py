"""Finish the saved variants with the shared WS dielectric reflectance."""
import unreal as u,json,hashlib
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2]
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report=json.loads((r/'install_receipt.json').read_text())
for source,row in report['materials'].items():
    mi=u.load_asset(row['asset']);m=mi.get_base_material()
    nodes=L.get_material_expressions(m)
    spec=next((n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='M249_Specular'),None)
    if not spec:spec=L.create_material_expression(m,u.MaterialExpressionScalarParameter);spec.set_editor_property('parameter_name','M249_Specular')
    spec.set_editor_property('default_value',.5)
    if not L.connect_material_property(spec,'',u.MaterialProperty.MP_SPECULAR):raise RuntimeError('Specular connection')
    for n in nodes:
        if isinstance(n,u.MaterialExpressionTextureObjectParameter) and str(n.get_editor_property('parameter_name'))=='M249_Grain':n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    errors=list(L.recompile_material(m) or [])
    if errors:raise RuntimeError('Material compilation '+str(errors[:3]))
    for a in (m,mi):
        if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
        path=a.get_path_name().split('.')[0];file=p/'Content'/(path.removeprefix('/Game/')+'.uasset')
        report['saved'][path]=hashlib.sha256(file.read_bytes()).hexdigest()
    row['dielectric_specular']=.5
    (r/'install_receipt.json').write_text(json.dumps(report,indent=2))
report['surface_revision']=2
(r/'install_receipt.json').write_text(json.dumps(report,indent=2))
print('M249_SURFACES_FINALIZED',len(report['materials']),flush=True)
