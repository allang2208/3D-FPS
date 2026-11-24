"""Retain the forged finish underneath the cyan charge using the existing base-colour sample."""
import unreal as u

def refine(material):
    lib=u.MaterialEditingLibrary
    old="return float3(.035,.91,1.0)*mask*(1.7+.65*saturate(Charge));"
    marker="float wear=smoothstep"
    work=[lib.get_material_property_input_node(material,u.MaterialProperty.MP_EMISSIVE_COLOR)]
    seen=set()
    while work:
        node=work.pop()
        if not node or node.get_name() in seen: continue
        seen.add(node.get_name())
        if isinstance(node,u.MaterialExpressionCustom):
            code=node.get_editor_property("code")
            if marker in code: return False
            if old in code:
                base=lib.get_material_property_input_node(material,u.MaterialProperty.MP_BASE_COLOR)
                if not base: raise RuntimeError("Missing forged base colour: "+material.get_path_name())
                inputs=list(node.get_editor_property("inputs"))
                steel=u.CustomInput()
                steel.set_editor_property("input_name","Steel")
                node.set_editor_property("inputs",inputs+[steel])
                if not lib.connect_material_expressions(base,"",node,"Steel"): raise RuntimeError("Could not bind steel colour")
                node.set_editor_property("code",code.replace(old,"""float wear=smoothstep(.055,.25,dot(Steel,float3(.2126,.7152,.0722)));
return float3(.035,.91,1.)*mask*lerp(.065,.95,wear)*lerp(.8,1.15,saturate(Charge));"""))
                if lib.recompile_material(material): raise RuntimeError("Raven charge shader compile failed")
                return True
        work.extend(lib.get_inputs_for_material_expression(material,node))
    raise RuntimeError("Missing Raven charge node: "+material.get_path_name())
