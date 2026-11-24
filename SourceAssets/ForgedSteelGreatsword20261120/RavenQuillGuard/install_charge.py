"""Make charge-capable versions of the accepted steel surfaces for the Raven guard only."""
import json
import runpy
from pathlib import Path
import unreal as u

here=Path(__file__).resolve().parent
project=here.parents[2]
if Path(u.Paths.project_dir()).resolve()!=project or '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Run in the background FPSGAME project commandlet.')
outdir=here/'Art/SprintCharge'
outdir.mkdir(exist_ok=True)
folder='/Game/Weapons/ForgedSteelGreatsword20261120/RavenQuillGuard/SprintCharge'
old=json.loads((here/'Art/NestedV4/import_receipt.json').read_text(encoding='utf8'))
seat=json.loads((here.parent/'CommonMods/blade_materials.json').read_text(encoding='utf8'))
wing=next(iter(old['temporal']))
sources={'M_RavenQuill_ForgedMetal':(wing,old['temporal'][wing]),
         'M_ForgedSteelGreatsword_Surface_V1':(seat['base'],seat['whirlwind'])}
g=runpy.run_path(str(project/'SourceAssets/KukriRefinement20261027/hanging_material.py'))
node,wire,out,custom=[g[k] for k in ('node','link','out','custom')]
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
apply_relief=runpy.run_path(str(here/'charge_relief.py'))['refine']
materials={}; temporal={}; assets=[]
for slot,pair in sources.items():
    paths=[]
    for source in pair:
        name=source.rsplit('.',1)[1]
        dest=folder+'/'+name
        mat=u.load_asset(dest) if E.does_asset_exist(dest) else E.duplicate_asset(source,dest)
        if not mat:raise RuntimeError('Failed to duplicate '+source)
        if not E.get_metadata_tag(mat,'RavenSprintGlow'):
            slab=L.get_material_property_input_node(mat,u.MaterialProperty.MP_FRONT_MATERIAL)
            old_emission=L.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)
            position=node(mat,u.MaterialExpressionWorldPosition)
            local=node(mat,u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
            wire(position,'',local,'')
            amount=node(mat,u.MaterialExpressionScalarParameter,parameter_name='RavenCharge',default_value=0.,use_custom_primitive_data=True,primitive_data_index=0)
            code="""float h=saturate((P.z+5.0)/8.70);
float distanceFromCollar=.84*h+.16*saturate(abs(P.x)/14.8);
float edge=lerp(-.06,1.06,saturate(Charge));
float mask=1-smoothstep(edge-.045,edge+.045,distanceFromCollar);
return float3(.035,.91,1.0)*mask*(1.7+.65*saturate(Charge));"""
            emission=custom(mat,code,[('P',local,''),('Charge',amount,'')])
            if old_emission:
                add=node(mat,u.MaterialExpressionAdd)
                wire(old_emission,'',add,'A');wire(emission,'',add,'B')
                emission=add
            wire(emission,'',slab,'Emissive Color')
            out(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
            if L.recompile_material(mat):raise RuntimeError('Recompile failed '+dest)
            E.set_metadata_tag(mat,'RavenSprintGlow','1')
        apply_relief(mat)
        if not E.save_loaded_asset(mat,False):raise RuntimeError('Could not save '+dest)
        paths.append(mat.get_path_name());assets.append(paths[-1])
    materials[slot]=paths[0];temporal[paths[0]]=paths[1]
bind=runpy.run_path(str(here.parent/'CommonMods/guard_surface_defaults.py'))['bind_saved_guards']
bind([path for path in old['assets'] if path.rsplit('/',1)[-1].startswith('SM_')],materials)
(outdir/'import_receipt.json').write_text(json.dumps({'assets':assets,'materials':materials,'temporal':temporal},indent=2)+'\n',encoding='utf8')
print('RAVEN_CHARGE_MATERIALS_SAVED',len(assets))
