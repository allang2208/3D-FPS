"""Apply only the Super90 receiver material's retained normal detail strength."""
import unreal as u

def apply_receiver_surface(material):
    L=u.MaterialEditingLibrary
    nodes=list(L.get_material_expressions(material))
    sample=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureSample) and n.texture and n.texture.get_name()=='T_S90_TTI_Benelli_M4_Normal_brand_friendly')
    for n in nodes:
        if n.get_editor_property('desc')=='Super90 surface normal repair':L.delete_material_expression(material,n)
    def make(cls):
        n=L.create_material_expression(material,cls);n.set_editor_property('desc','Super90 surface normal repair');return n
    strength=make(u.MaterialExpressionScalarParameter);strength.set_editor_property('parameter_name','SourceNormalStrength');strength.set_editor_property('default_value',.5)
    flat=make(u.MaterialExpressionConstant3Vector);flat.set_editor_property('constant',u.LinearColor(0,0,1,1))
    blend=make(u.MaterialExpressionLinearInterpolate)
    L.connect_material_expressions(flat,'',blend,'A');L.connect_material_expressions(sample,'RGB',blend,'B');L.connect_material_expressions(strength,'',blend,'Alpha')
    norm=make(u.MaterialExpressionNormalize);L.connect_material_expressions(blend,'',norm,'VectorInput')
    L.connect_material_property(norm,'',u.MaterialProperty.MP_NORMAL)
    u.EditorAssetLibrary.set_metadata_tag(material,'Super90SurfaceRepair','20261007: preserve UV0/albedo/PBR maps; half-strength source normal over repaired curve normals')
    L.recompile_material(material)
