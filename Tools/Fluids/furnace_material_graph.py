"""Material graph helpers without a Niagara editor toolset dependency."""
import unreal as u
L=u.MaterialEditingLibrary

def node(m,cls):return L.create_material_expression(m,cls)

def wire(source,target,pin):
    obj,out=source if isinstance(source,tuple) else (source,'')
    if not L.connect_material_expressions(obj,out,target,pin):raise RuntimeError('Cannot connect '+pin)

def prop(m,source,name):
    if not L.connect_material_property(source,'',getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError(name)

def scalar(m,name,value):
    n=node(m,u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value)
    return n

def custom(m,code,inputs,width=1):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code)
    n.set_editor_property('description','Furnace casting')
    n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for name in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins)
    for name,value in inputs.items():wire(value,n,name)
    return n
