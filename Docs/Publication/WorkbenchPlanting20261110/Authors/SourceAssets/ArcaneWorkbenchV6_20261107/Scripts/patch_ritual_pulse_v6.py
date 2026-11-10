"""Idempotent emissive-only pulse layer for the two actual V6 rune materials.
Run as a background Python commandlet; no mesh imports, previews or tests.
The full material author also calls patch_rune_material so rebuilding preserves it.
"""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ArcaneWorkbenchV6_20261107')
DEST='/Game/Building/ArcaneWorkbenchV6_20261107/Materials/'
TARGETS=('M_EW_Rune_inlay_energized_recessed_copper',
         'M_EW_PROJECT_carved_stone_work_surface')
L=u.MaterialEditingLibrary
TAG='ArcaneRitualPulseV1'

def patch_rune_material(mat):
    if mat.get_name() not in TARGETS:
        return False
    nodes=list(L.get_material_expressions(mat))
    # The final node is the stable ownership marker. Never wrap the layer twice.
    if any(str(n.get_editor_property('desc')) == TAG+'_Output' for n in nodes):
        return False
    original=L.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)
    if original is None:
        raise RuntimeError('Missing authored emissive mask: '+mat.get_path_name())
    def node(cls,label):
        n=L.create_material_expression(mat,cls)
        n.set_editor_property('desc',TAG+'_'+label)
        return n
    def link(source,pin,target,input_name):
        if not L.connect_material_expressions(source,pin,target,input_name):
            raise RuntimeError('Could not connect ritual pulse '+input_name)
    pulse=node(u.MaterialExpressionScalarParameter,'Amount')
    pulse.set_editor_property('parameter_name','ArcanePulse')
    pulse.set_editor_property('default_value',0.0)
    tint=node(u.MaterialExpressionVectorParameter,'Color')
    tint.set_editor_property('parameter_name','ArcanePulseColor')
    tint.set_editor_property('default_value',u.LinearColor(1,.52,.025,1))
    mask=node(u.MaterialExpressionDesaturation,'ExistingMask')
    # MaterialEditingLibrary resolves an empty input name to GetInput(0).
    # Desaturation's first input is the authored RGB emission, not Fraction.
    # Use that API contract instead of its shortened/unnamed graph-pin label.
    link(original,'',mask,'')
    color=node(u.MaterialExpressionMultiply,'MaskedColor')
    link(mask,'',color,'A');link(tint,'',color,'B')
    strength=node(u.MaterialExpressionMultiply,'Peak')
    strength.set_editor_property('const_b',10.0)
    link(color,'',strength,'A')
    result=node(u.MaterialExpressionLinearInterpolate,'Output')
    link(original,'',result,'A');link(strength,'',result,'B');link(pulse,'',result,'Alpha')
    if not L.connect_material_property(result,'',u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Could not connect ritual emissive output')
    return True

def install():
    if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():
        raise RuntimeError('Wrong project')
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('PIE running')
    paths=[DEST+name for name in TARGETS]
    dirty=u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    if any(p.get_path_name() in paths for p in dirty):
        raise RuntimeError('Target rune materials have unsaved edits')
    receipt={'stage':'ritual_pulse_saved','materials':[],'tests_run':False,'renders_run':False}
    for path in paths:
        mat=u.load_asset(path)
        if mat is None:raise RuntimeError('Missing V6 rune material: '+path)
        changed=patch_rune_material(mat)
        if changed:
            L.layout_material_expressions(mat)
            L.recompile_material(mat)
            if not u.EditorAssetLibrary.save_loaded_asset(mat,False):
                raise RuntimeError('Could not save '+path)
        receipt['materials'].append({'asset':mat.get_path_name(),'changed':changed,
            'default_pulse':0,'preserves_authored_emission_mask':True})
    output=ROOT/'Receipts/ritual-pulse-v1.json'
    output.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt))

if __name__=='__main__':
    install()
