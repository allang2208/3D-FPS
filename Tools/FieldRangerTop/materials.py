"""Shared, streamed 2K physical surfaces; no per-frame material work."""
import hashlib, json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020'
DEST='/Game/Characters/ModularOutfit20260924/FieldRangerTop20261020'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
def save(a):
    a.modify()
    if not E.save_loaded_asset(a,False):raise RuntimeError('Ranger asset not saved '+a.get_path_name())
def output(node,prop,pin=''):
    if not L.connect_material_property(node,pin,prop):raise RuntimeError('Ranger material output')
def material(name,family=None,color=None,rough=.7,metal=0):
    m=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    if not m:m=u.load_asset(DEST+'/Materials/'+name);L.delete_all_material_expressions(m)
    L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    L.set_material_usage(m,u.MaterialUsage.MATUSAGE_STATIC_MESH)
    if family:
        for channel in ('BaseColor','Normal','ORM'):
            tex=u.load_asset(DEST+'/Textures/T_'+family+'_'+channel)
            node=L.create_material_expression(m,u.MaterialExpressionTextureSampleParameter2D)
            node.set_editor_property('parameter_name',channel);node.set_editor_property('texture',tex)
            node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if channel=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            if channel=='BaseColor':output(node,u.MaterialProperty.MP_BASE_COLOR,'RGB')
            elif channel=='Normal':output(node,u.MaterialProperty.MP_NORMAL,'RGB')
            else:
                for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:output(node,prop,pin)
    else:
        node=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);node.set_editor_property('constant',u.LinearColor(*color,1));output(node,u.MaterialProperty.MP_BASE_COLOR)
        for val,prop in [(rough,u.MaterialProperty.MP_ROUGHNESS),(metal,u.MaterialProperty.MP_METALLIC)]:
            node=L.create_material_expression(m,u.MaterialExpressionConstant);node.set_editor_property('r',val);output(node,prop)
    node=L.create_material_expression(m,u.MaterialExpressionConstant);node.set_editor_property('r',.25 if family=='RangerTwill' else .35);output(node,u.MaterialProperty.MP_SPECULAR)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Ranger shader compile failed '+str(errors))
    save(m);return m
def create():
    receipt=R/'materials.json';sha=hashlib.sha256(Path(__file__).read_bytes()+(R/'surfaces.json').read_bytes()).hexdigest()
    if receipt.exists():
        existing=json.loads(receipt.read_text())
        if existing.get('revision')==sha:return [u.load_asset(p) for p in existing['materials']]
    for family in ('RangerTwill','RangerLeather'):
        for channel in ('BaseColor','Normal','ORM'):
            task=u.AssetImportTask();task.filename=str(R/'Textures'/(family+'_'+channel+'.png'))
            task.destination_path=DEST+'/Textures';task.destination_name='T_'+family+'_'+channel;task.automated=True;task.replace_existing=True;task.save=False
            A.import_asset_tasks([task]);tex=u.load_asset(DEST+'/Textures/'+task.destination_name)
            tex.set_editor_property('srgb',channel=='BaseColor')
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
            if channel=='Normal':tex.set_editor_property('flip_green_channel',True)
            tex.set_editor_property('never_stream',False);save(tex)
    mats=[material('M_RangerCloth','RangerTwill'),material('M_RangerLeather','RangerLeather'),
          material('M_RangerLining',color=(.027,.032,.022),rough=.88),
          material('M_RangerBrass',color=(.22,.145,.062),rough=.48,metal=.9),
          material('M_RangerThread',color=(.14,.095,.052),rough=.82)]
    receipt.write_text(json.dumps(dict(completed=True,revision=sha,materials=[m.get_path_name() for m in mats],runtime_tested=False),indent=2),encoding='utf-8')
    print('RANGER_MATERIALS_SAVED',flush=True);return mats
if __name__=='__main__':create()
