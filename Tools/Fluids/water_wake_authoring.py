"""Add four bounded wake records to an existing shared water field node."""
import unreal as u

def wake_inputs(material,field):
    from author_river_pilot import vector,wire
    lib=u.MaterialEditingLibrary
    inputs=list(field.get_editor_property('inputs'))
    names={str(v.get_editor_property('input_name')) for v in inputs}
    bindings={}
    for i in range(4):
        for prefix,parameter,default in [('Wake','WaterWake',(0,0,0,0)),('WakeMotion','WaterWakeMotion',(1,0,0,-10000))]:
            name=prefix+str(i)
            if name in names:continue
            pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
            parameter+=str(i)
            node=next((n for n in lib.get_material_expressions(material) if isinstance(n,u.MaterialExpressionVectorParameter)
                       and str(n.get_editor_property('parameter_name'))==parameter),None)
            bindings[name]=node or vector(material,parameter,default)
    field.set_editor_property('inputs',inputs)
    for name,node in bindings.items():wire((node,'RGBA'),field,name)
