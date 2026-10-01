"""Dispatch to the current saved finish; retain the original recipe for older workspaces."""
import json as _finish_json
import runpy as _finish_runpy
from pathlib import Path as _FinishPath

_finish_project = _FinishPath(__file__).resolve().parents[2]
_finish_manifest = _finish_project / 'SourceAssets/PKMLowpoly20260922/current_surface_bindings.json'
if _finish_manifest.exists():
    _finish_state = _finish_json.loads(_finish_manifest.read_text(encoding='utf-8'))
    _finish_runpy.run_path(str(_finish_project / _finish_state['rebind_script']), run_name='__main__')
else:
    """Upgrade current PKM-private dry/wet surface nodes, preserving mesh references."""
    import unreal as u, json, shutil, sys
    from pathlib import Path
    O=Path(__file__).parent
    sys.path.insert(0,str(O))
    import finish_recipe as recipe
    P=recipe.P; E=u.EditorAssetLibrary; L=u.MaterialEditingLibrary
    commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    if not commandlet:
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():
            raise RuntimeError('PKM finish: active PIE; no material writes performed')
    paths=[P+'/Accessories14/SK_PKM_Manny_Modular',P+'/OpticMount23/SM_PKM_optic_rail']
    paths+=list(E.list_assets(P+'/Bipod26',recursive=False,include_folder=False))
    paths+=list(E.list_assets(P+'/Accessories14/Meshes',recursive=False,include_folder=False))
    meshes=[]; dry={}
    for path in paths:
        mesh=u.load_asset(path)
        if not isinstance(mesh,(u.SkeletalMesh,u.StaticMesh)):continue
        meshes.append(mesh)
        slots=mesh.materials if isinstance(mesh,u.SkeletalMesh) else mesh.static_materials
        for s in slots:
            mat=s.material_interface
            if mat and mat.get_path_name().startswith(P+'/'):dry[mat.get_path_name()]=mat
    # Keep the established independent box pair even after legacy material rebuilds.
    box=u.load_asset(P+'/AmmoBox30/Materials/M_PKM_AmmoBoxPaint_Dry')
    if not box:raise RuntimeError('PKM olive paint source is required')
    dry[box.get_path_name()]=box
    table=u.load_asset(P+'/Finish20/DA_PKM_WetMaterials')
    mapping=dict(table.get_editor_property('wet_materials'))
    wet_by_path={str(k):v for k,v in mapping.items() if v}
    boxwet=u.load_asset(P+'/AmmoBox30/Materials/M_PKM_AmmoBoxPaint_Wet')
    if not boxwet:raise RuntimeError('PKM olive wet paint source is required')
    wet_by_path[box.get_path_name()]=boxwet
    plan={}; pairs=[]
    for path,mat in dry.items():
        base=mat.get_base_material()
        settings=recipe.profile(path,str(E.get_metadata_tag(base,'PKM20_Category')))
        if settings is None:continue
        wet=wet_by_path.get(path)
        if not wet:raise RuntimeError('Missing current PKM wet partner '+path)
        pairs.append({'dry':path,'wet':wet.get_path_name(),'profile':settings})
        for version in [mat,wet]:
            master=version.get_base_material()
            if not master.get_path_name().startswith(P+'/'):
                raise RuntimeError('Refusing to change shared parent '+master.get_path_name())
            plan[master.get_path_name()]=(master,settings)
    # Exact target conflict detection is part of preserving existing authoring work.
    packages={a.get_path_name().split('.')[0] for a,_ in plan.values()}|{recipe.TEXTURE}
    main=meshes[0];slots=main.materials
    box_indices=[i for i,s in enumerate(slots) if str(s.material_slot_name).endswith(('__OldBox','__NewBox'))]
    if len(box_indices)!=2:raise RuntimeError('Expected existing PKM old/new box sections')
    restore_boxes=any(slots[i].material_interface!=box for i in box_indices)
    restore_mapping=not any(str(k)==box.get_path_name() and v==boxwet for k,v in mapping.items())
    if restore_boxes:packages.add(main.get_path_name().split('.')[0])
    if restore_mapping:packages.add(table.get_path_name().split('.')[0])
    if not commandlet:
        conflict=packages & {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        if conflict:raise RuntimeError('PKM target packages have unsaved edits: '+str(sorted(conflict)))
    content=Path(u.Paths.project_dir()).resolve()/'Content'
    for package in packages:
        relative=package.removeprefix('/Game/')+'.uasset';source=content/relative;dest=O/'Before'/relative
        if source.exists() and not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    report={'complete':False,'game_tested':False,'rendered':False,'mesh_reimported':False,
            'pairs':pairs,'saved':[],'texture':recipe.TEXTURE,'binding_paths_preserved':True}
    receipt=O/'install_receipt.json'
    def record():receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
    def save(a):
        if not E.save_loaded_asset(a,False):raise RuntimeError('PKM finish save failed '+a.get_path_name())
        report['saved'].append(a.get_path_name());record()
    record()
    tex=recipe.texture()
    for path,(mat,settings) in plan.items():
        recipe.apply_material(mat,settings,tex)
        errors=[str(v) for v in L.recompile_material(mat)]
        if errors:
            report['compile_error']={'asset':path,'errors':errors};record()
            raise RuntimeError('PKM material compilation failed '+path+' '+str(errors))
        save(mat)
    if restore_mapping:
        mapping[box.get_path_name()]=boxwet
        table.set_editor_property('wet_materials',mapping);save(table)
    if restore_boxes:
        for i in box_indices:
            slot=slots[i];slot.material_interface=box;slots[i]=slot
        main.set_editor_property('materials',slots);save(main)
    report['complete']=True
    report['materials_saved']=len(plan)
    report['box_bindings']=[{'slot':str(main.materials[i].material_slot_name),'material':main.materials[i].material_interface.get_path_name()} for i in box_indices]
    record()
    print('PKM_SATIN_SAVED',json.dumps({'material_pairs':len(pairs),'materials_saved':len(plan),'box_bindings':report['box_bindings'],'game_tested':False}),flush=True)
