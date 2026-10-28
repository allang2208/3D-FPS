"""Finish imported chain coordinate bindings and save all 26 standard icon keys."""
import json,itertools,copy
from pathlib import Path
import unreal as u
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriRefinement20261027')
data=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
manifest=json.loads((P/'icon-manifest.json').read_text(encoding='utf-8'))
E=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt={'complete':False,'saved_assets':[],'dynamics_bindings':[],'runtime_tested':False}
for e in data['variants']:
    if 'dynamics' not in e:continue
    # FBX coordinate conversion belongs to the asset import contract. Match the
    # imported local mesh basis before placing guide pivots and collision shapes.
    mesh=u.load_asset(e['mesh']);box=mesh.get_bounding_box()
    actual=[[box.min.x,box.min.y,box.min.z],[box.max.x,box.max.y,box.max.z]]
    authored=e['author_bounds_cm'];candidates=[]
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1,1),repeat=3):
            transformed=[[min(authored[0][perm[i]]*signs[i],authored[1][perm[i]]*signs[i]) for i in range(3)],
                         [max(authored[0][perm[i]]*signs[i],authored[1][perm[i]]*signs[i]) for i in range(3)]]
            error=sum(abs(actual[j][i]-transformed[j][i]) for j in range(2) for i in range(3))
            candidates.append((error,perm,signs))
    error,perm,signs=min(candidates)
    if error>.05 or perm[2]!=2 or signs[2]!=1:raise RuntimeError('Unresolved hanging FBX frame: '+str((e['id'],error,perm,signs)))
    def convert(p):return [p[perm[i]]*signs[i] for i in range(3)]
    spec=copy.deepcopy(e['dynamics']);spec['guides_cm']=[convert(p) for p in spec['guides_cm']]
    spec['collision_capsules_cm']=[convert(c[:3])+convert(c[3:6])+[c[6]] for c in spec['collision_capsules_cm']]
    e['runtime_dynamics']=spec
    m=u.load_asset(e['material']);nodes=E.get_material_expressions(m)
    constants=[n for n in nodes if isinstance(n,u.MaterialExpressionConstant3Vector)]
    for i,(old,new) in enumerate(zip(e['dynamics']['guides_cm'][:7],spec['guides_cm'][:7])):
        n=min(constants,key=lambda n:sum(abs(v-w) for v,w in zip((n.constant.r,n.constant.g,n.constant.b),old)))
        constants.remove(n);n.set_editor_property('constant',u.LinearColor(*new,0))
        p=next(n for n in nodes if isinstance(n,u.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='TasselP'+str(i))
        p.set_editor_property('default_value',u.LinearColor(*new,0))
    E.recompile_material(m)
    if not u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost()],False):raise RuntimeError('Saving chain binding failed')
    receipt['dynamics_bindings'].append({'mesh':e['mesh'],'author_to_ue_permutation':perm,'signs':signs,'guides_cm':spec['guides_cm']})
(P/'surfaces.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
masters={m['id']:m for m in manifest['masters']}
for job in manifest['bindings']:
    task=u.AssetImportTask();task.filename=masters[job['master']]['output']
    task.destination_path,task.destination_name=job['texture'].split('.')[0].rsplit('/',1)
    task.factory=u.TextureFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    A.import_asset_tasks([task]);tex=u.load_asset(job['texture'])
    if not tex or not task.imported_object_paths:raise RuntimeError('Icon import failed: '+job['key'])
    tex.set_editor_properties({'lod_group':u.TextureGroup.TEXTUREGROUP_UI,'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON,
        'srgb':True,'never_stream':True,'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS,'max_texture_size':1024})
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Icon save failed')
    receipt['saved_assets'].append(tex.get_path_name())
    (P/'Receipts/import-icons.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
receipt['complete']=True
(P/'Receipts/import-icons.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('KUKRI_REFINEMENT_ICONS_SAVED '+str(len(receipt['saved_assets'])))
