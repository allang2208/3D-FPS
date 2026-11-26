"""Author the continuous terrain layer, existing fine grass and final forest-village map."""
import json
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0,str(Path(__file__).resolve().parent))
import author_trail_cover_materials as art

ed=u.MaterialEditingLibrary
lib=u.EditorAssetLibrary
dest=art.ref+'/ContinuousMeadow'

def tagged(m,cls,tag):
    item=next((n for n in ed.get_material_expressions(m) if n.get_editor_property('desc')==tag),None)
    if not item:
        item=ed.create_material_expression(m,cls)
        item.set_editor_property('desc',tag)
    return item

def prepare_textures():
    lib.make_directory(dest)
    field=art.tex('T_ContinuousMeadowField',dest,'BC7',False)
    for key in ('address_x','address_y'):field.set_editor_property(key,u.TextureAddress.TA_CLAMP)
    field.set_editor_property('compression_no_alpha',False)
    color=art.tex('T_ContinuousMeadowBlades',dest,'DEFAULT',True)
    normal=art.tex('T_ContinuousMeadowNormal',dest,'NORMALMAP',False)
    for tex in (field,color,normal):art.save(tex)
    return field,color,normal

def apply_surface(m,shade,field,color,normal):
    nodes=ed.get_material_expressions(m)
    owners=[n for n in nodes if isinstance(n,u.MaterialExpressionMakeMaterialAttributes)
            and art.inputs(m,n).get('BaseColor')==shade]
    if len(owners)!=1:raise RuntimeError('Missing unique meadow output on '+m.get_name())
    root=owners[0]
    sources=art.inputs(m,shade)
    base=art.inputs(m,root)['Normal']
    if base!=shade:
        outpin=str(ed.get_input_node_output_name_for_material_expression(root,base) or '')
    else:
        base=sources['BaseN']
        outpin=str(ed.get_input_node_output_name_for_material_expression(shade,base) or '')
    names=list(shade.get_editor_property('inputs'))
    for name in ('Bank','Detail','BaseN','BladeN','Wet'):
        if not any(str(n.get_editor_property('input_name'))==name for n in names):
            pin=u.CustomInput();pin.set_editor_property('input_name',name);names.append(pin)
    shade.set_editor_property('inputs',names)
    outputs=list(shade.get_editor_property('additional_outputs'))
    if not any(str(p.get_editor_property('output_name'))=='MeadowNormal' for p in outputs):
        out=u.CustomOutput();out.set_editor_property('output_name','MeadowNormal')
        out.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        outputs.append(out);shade.set_editor_property('additional_outputs',outputs)
    # Reuse the source field's metre-grid projection. Each terrain reads identical pixel centres.
    atlas=tagged(m,u.MaterialExpressionTextureSample,'Continuous meadow field')
    original=sources['F']
    if original!=atlas:art.wire(art.inputs(m,original)['UVs'],'',atlas,'UVs')
    atlas.set_editor_property('texture',field)
    atlas.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    art.wire(atlas,'RGB',shade,'F');art.wire(atlas,'A',shade,'Bank')
    for pin,tex,kind in [('Detail',color,'COLOR'),('BladeN',normal,'NORMAL')]:
        obj=tagged(m,u.MaterialExpressionTextureObject,'Continuous meadow '+pin)
        obj.set_editor_property('texture',tex)
        obj.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind))
        art.wire(obj,'',shade,pin)
    rain=tagged(m,u.MaterialExpressionCollectionParameter,'Continuous meadow weather')
    rain.set_editor_property('collection',art.asset('/Game/Weather/Materials/MPC_FPS_Weather'))
    rain.set_editor_property('parameter_name','WeatherWetness')
    art.wire(rain,'',shade,'Wet');art.wire(base,outpin,shade,'BaseN')
    shade.set_editor_property('code',Path(__file__).with_name('continuous_meadow.ush').read_text(encoding='utf-8-sig'))
    shade.set_editor_property('desc','R26 continuous ground cover')
    art.wire(shade,'MeadowNormal',root,'Normal')
    import author_roadside_leaves as litter
    if lib.does_asset_exist(litter.folder+'/T_ShoulderLeafField'):litter.configure(m,shade,root)

def update_surfaces():
    textures=prepare_textures()
    for path in (art.ref+'/M_ForestReferenceMesh',art.dest+'/M_ForestVillageLandscape'):
        mat=art.asset(path)
        shade=next(n for n in ed.get_material_expressions(mat) if n.get_editor_property('desc') in
                   ('R24 hillside meadow','R21 continuous meadow','R26 continuous ground cover'))
        apply_surface(mat,shade,*textures);art.compile_mat(mat)

def update_map():
    import author_trail_cover_level as level
    world=level.save.load_map(level.village)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name('L_ForestPathVillage'):
        raise RuntimeError('Could not select forest village persistent level')
    count,cells=level.place_meadows(world)
    if not count or not level.save.save_map(world,level.village):raise RuntimeError('Could not save fine grass')
    (art.batch/'authored.json').write_text(json.dumps(dict(instances=count,cells=cells,mesh=level.fine_mesh,material=level.fine_material,road_look=3),indent=2))

def author():
    update_surfaces()
    update_map()

if __name__=='__main__':author()
