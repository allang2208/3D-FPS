"""Place fracture edges at the wall toe, keep thin floor dressing out of the dust projection."""
import unreal as u
from pathlib import Path
import json
def run(world,row):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    base='/Game/SceneTests/FreightCameraMatch20261113/Materials/'
    def prop(name,loc,rot,scale):
        a=actors[name];a.modify()
        a.set_actor_location_and_rotation(u.Vector(*loc),u.Rotator(roll=rot[0],pitch=rot[1],yaw=rot[2]),False,False)
        a.set_actor_scale3d(u.Vector(*scale))
    prop('SurfaceStudy_PackingConcreteRelief',(2908.,485.66,48.),(0.,5.,0.),(1.58,1.12,1.25))
    prop('Cart_WorkshopWallFootSpall',(8317.3,-341.,19.),(0.,-16.,90.),(-.92,.9,.59))
    # Positive light/dust at the actual cart wheel, set down onto the finished platform.
    for name,where in [('WarehouseEntrance_Dust_PalletHalo',(2918.,341.,-.03)),('WarehouseEntrance_Dust_PackingWallFoot',(2948.,458.,-.03)),('FreightStation_WorkshopCartDust',(8432.,-326.,-.03))]:
        a=actors[name];a.modify();a.set_actor_location(u.Vector(*where),False,False)
        c=a.get_component_by_class(u.DecalComponent);c.modify()
        size=c.get_editor_property('decal_size');c.set_editor_property('decal_size',u.Vector(.105,size.y,size.z))
    # Preserve the pre-existing top faces on route markings and paper. These sit less than 2 mm above the concrete.
    for k,a in actors.items():
        if 'Cardboard' in k or 'Carton' in k:
            if (a.get_actor_location()-actors['REF_01_PackingSurface'].get_actor_location()).length()<750:
                c=a.get_component_by_class(u.StaticMeshComponent)
                if c:a.modify();c.modify();c.set_editor_property('receives_decals',False)
    # Lift extremely dark pockets within the scan itself. Use the registered scanned colors and normals.
    mat=u.load_asset(base+'M_SpalledConcrete')
    lib=u.MaterialEditingLibrary
    if not u.EditorAssetLibrary.get_metadata_tag(mat,'ChipGrade'):
        tex=next(n for n in lib.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='ColorCoverage')
        orm=next(n for n in lib.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='ScanORM')
        mat.modify()
        def filtered(src,out,code,name,kind):
            n=lib.create_material_expression(mat,u.MaterialExpressionCustom)
            pin=u.CustomInput();pin.set_editor_property('input_name','V');n.set_editor_property('inputs',[pin]);n.set_editor_property('code',code);n.set_editor_property('output_type',kind)
            lib.connect_material_expressions(src,out,n,'V');lib.connect_material_property(n,'',name)
        filtered(tex,'RGB','return .045+V*.72;',u.MaterialProperty.MP_BASE_COLOR,u.CustomMaterialOutputType.CMOT_FLOAT3)
        filtered(orm,'R','return lerp(.65,1.,V);',u.MaterialProperty.MP_AMBIENT_OCCLUSION,u.CustomMaterialOutputType.CMOT_FLOAT1)
        errors=lib.recompile_material(mat)
        if errors:raise RuntimeError(str(errors))
        u.EditorAssetLibrary.set_metadata_tag(mat,'ChipGrade','1')
        if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Cannot save relief')
