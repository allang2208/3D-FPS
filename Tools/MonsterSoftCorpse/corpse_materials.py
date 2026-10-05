"""Preserve each surface graph and parameters while rebuilding deformed normals."""
import hashlib
import unreal as u

L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
DEST = '/Game/Monsters/SoftCorpseV1/Materials'
MARKER = 'ContinuousCorpseV1 DeformedSurfaceNormal'


def wire(source, target, pin):
    if not L.connect_material_expressions(source, '', target, pin):
        raise RuntimeError('Could not connect normal input ' + pin)


def make(source, saved):
    if not source:
        return None
    suffix = hashlib.sha1(source.get_path_name().encode()).hexdigest()[:8]
    path = DEST+'/'+source.get_name()+'_'+suffix+'_Corpse'
    material = u.load_asset(path) or E.duplicate_asset(source.get_path_name(), path)
    if isinstance(material, u.MaterialInstanceConstant):
        parent = make(source.get_editor_property('parent'), saved)
        L.set_material_instance_parent(material, parent)
    else:
        expressions = L.get_material_expressions(material)
        if not any(isinstance(node, u.MaterialExpressionCustom) and
                   str(node.get_editor_property('description')) == MARKER for node in expressions):
            original = L.get_material_property_input_node(material, u.MaterialProperty.MP_NORMAL)
            if not original:
                original = L.create_material_expression(material, u.MaterialExpressionConstant3Vector)
                original.set_editor_property('constant', u.LinearColor(0, 0, 1, 0))
            material.set_editor_property('tangent_space_normal', False)
            custom = L.create_material_expression(material, u.MaterialExpressionCustom)
            custom.set_editor_property('description', MARKER)
            custom.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
            pins = []
            for name in ('P', 'UV', 'N', 'View', 'Fallback'):
                pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
            custom.set_editor_property('inputs', pins)
            custom.set_editor_property('code',
                'float3 dx=ddx(P),dy=ddy(P);float2 ux=ddx(UV),uy=ddy(UV);'
                'float3 g=cross(dy,dx);float g2=dot(g,g);'
                'float3 gn=g2>1e-16?g*rsqrt(max(g2,1e-16)):normalize(Fallback);'
                'gn*=dot(gn,View)>=0?1:-1;'
                'float det=ux.x*uy.y-ux.y*uy.x;if(abs(det)<1e-10)return gn;'
                'float sd=det>=0?1:-1;float3 t=(dx*uy.y-dy*ux.y)*sd;t-=gn*dot(t,gn);'
                'float t2=dot(t,t);if(t2<1e-16)return gn;t*=rsqrt(max(t2,1e-16));'
                'float3 b=(-dx*uy.x+dy*ux.x)*sd;b-=gn*dot(b,gn)+t*dot(b,t);'
                'float b2=dot(b,b);if(b2<1e-16)return gn;b*=rsqrt(max(b2,1e-16));'
                'float3 result=t*N.x+b*N.y+gn*max(N.z,0.001);'
                'return result*rsqrt(max(dot(result,result),1e-16));')
            position = L.create_material_expression(material, u.MaterialExpressionWorldPosition)
            position.set_editor_property('world_position_shader_offset', u.WorldPositionIncludedOffsets.WPT_CAMERA_RELATIVE)
            uv = L.create_material_expression(material, u.MaterialExpressionTextureCoordinate)
            view = L.create_material_expression(material, u.MaterialExpressionCameraVectorWS)
            fallback = L.create_material_expression(material, u.MaterialExpressionVertexNormalWS)
            for node, pin in ((position, 'P'), (uv, 'UV'), (original, 'N'), (view, 'View'), (fallback, 'Fallback')):
                wire(node, custom, pin)
            if not L.connect_material_property(custom, '', u.MaterialProperty.MP_NORMAL):
                raise RuntimeError('Could not connect corpse normal')
            for node in expressions:
                if isinstance(node, u.MaterialExpressionSubstrateShadingModels):
                    wire(custom, node, 'Normal')
            errors = L.recompile_material(material)
            if errors:
                raise RuntimeError(str(errors))
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('Could not save '+path)
    saved.add(material.get_path_name())
    return material
