"""Repair the existing two HUD materials in place; preserve art and gameplay."""
from pathlib import Path
import unreal as u
import ast,json,os
P=Path(__file__).parent;L=u.MaterialEditingLibrary
paths=[
 '/Game/Weapons/WoodSteelLongbow20261026/MountainEchoAlpineV23/M_MountainEcho_AlpineHUD',
 '/Game/Weapons/WoodSteelLongbow20261026/CadenceV1/M_Cadence_HUD']
if '-nullrhi' in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('This repair requires the actual shader platform; NullRHI cannot diagnose material compilation.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    sub=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if sub and sub.is_in_play_in_editor():raise RuntimeError('Preserving Play session; stop Play before saving these materials.')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(path in dirty for path in paths):raise RuntimeError('Preserving pre-existing unsaved HUD edits')
r={'pid':os.getpid(),'renderer':'D3D12 / SM6','materials':[],'gameplay_tested':False,'runtime_state_observed':False}
for path in paths:
    print('RESONANCE_REPAIR_BEGIN '+path,flush=True)
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing target material '+path)
    nodes=L.get_material_expressions(mat)
    row={'path':path,'before_nodes':[{'name':x.get_name(),'class':x.get_class().get_name()} for x in nodes],
         'before':[],'after':[]}
    for node in nodes:
        if isinstance(node,u.MaterialExpressionComponentMask):
            row['before'].append({'node':node.get_name(),
             'inputs':[v.get_name() if v else None for v in L.get_inputs_for_material_expression(mat,node)]})
    print('RESONANCE_EXISTING_GRAPH '+json.dumps(row),flush=True)
    # Rebuild only the two known graphs from their approved author source. Reuse
    # the saved texture; do not reimport the image or touch texture settings.
    folder=path.split('/')[-2]
    texture_name='T_MountainEcho_Alpine' if folder=='MountainEchoAlpineV23' else 'T_Cadence_HUD'
    texture=u.load_asset(path.rsplit('/',1)[0]+'/'+texture_name)
    if not isinstance(texture,u.Texture2D):raise RuntimeError('Missing approved HUD texture')
    author=P.parent/folder/'import_hud.py'
    statements=ast.parse(author.read_text(encoding='utf-8-sig'),filename=str(author)).body
    def assigns(statement,key):
        return isinstance(statement,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in statement.targets)
    start=next(i for i,s in enumerate(statements) if assigns(s,'name'))
    end=next(i for i,s in enumerate(statements) if assigns(s,'errors'))
    scope={'u':u,'LIB':L,'TOOLS':u.AssetToolsHelpers.get_asset_tools(),
           'DEST':path.rsplit('/',1)[0],'texture':texture}
    exec(compile(ast.Module(body=statements[start:end],type_ignores=[]),str(author),'exec'),scope)
    if scope['mat']!=mat:raise RuntimeError('Author changed the material identity')
    nodes=L.get_material_expressions(mat)
    customs=[x for x in nodes if isinstance(x,u.MaterialExpressionCustom)]
    masks=[x for x in nodes if isinstance(x,u.MaterialExpressionComponentMask)]
    if len(customs)!=1 or len(masks)!=2:raise RuntimeError('Unexpected authored HUD graph; preserve it: '+path)
    row['after_nodes']=[{'name':x.get_name(),'class':x.get_class().get_name()} for x in nodes]
    for node in masks:
        if not L.connect_material_expressions(customs[0],'',node,''):
            raise RuntimeError('ComponentMask first-input connection failed')
        inputs=L.get_inputs_for_material_expression(mat,node)
        if not inputs or inputs[0]!=customs[0]:raise RuntimeError('HUD mask connection did not persist in the graph')
        row['after'].append({'node':node.get_name(),'inputs':[v.get_name() if v else None for v in inputs]})
    print('RESONANCE_CONNECTIONS_FIXED '+path,flush=True)
    errors=list(L.recompile_material(mat))
    row['compile_errors']=errors
    if errors:raise RuntimeError('HUD compiler errors: '+str(errors))
    # This engine API finishes this material's shader jobs, unlike NullRHI import.
    stats=L.get_statistics(mat)
    row['shader_jobs_finished']=True
    row['texture_samplers']=stats.get_editor_property('num_samplers')
    row['pixel_texture_samples']=stats.get_editor_property('num_pixel_texture_samples')
    if not u.EditorLoadingAndSavingUtils.save_packages([mat.get_outermost()],False):raise RuntimeError('Could not save '+path)
    row['saved']=True;r['materials'].append(row)
    (P/'repair-receipt.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print('RESONANCE_REPAIR_SAVED '+path,flush=True)
r['complete']=True
(P/'repair-receipt.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print('RESONANCE_REPAIR_COMPLETE',flush=True)
