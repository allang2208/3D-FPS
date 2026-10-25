"""Pinned leather suspension; same 30-float current/previous field as backpack inertia."""
import unreal as u
L=u.MaterialEditingLibrary
def add_motion(mat):
    def node(kind,**props):
        n=L.create_material_expression(mat,kind)
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(a,b,pin,output=''):
        if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Quiver motion pin '+pin)
    position=node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    mask=node(u.MaterialExpressionVertexColor)
    def field(offset):
        names=['Pivot','RowX','RowY','RowZ','Shift']
        nodes=[node(u.MaterialExpressionVectorParameter,parameter_name='Quiver'+str(offset)+name,default_value=u.LinearColor(0,0,0,0),use_custom_primitive_data=True,primitive_data_index=offset+i*3) for i,name in enumerate(names)]
        custom=node(u.MaterialExpressionCustom,description='Weighted quiver suspension',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,code='float3 q=Position-Pivot; return (float3(dot(RowX,q),dot(RowY,q),dot(RowZ,q))+Shift)*saturate(Mask);')
        inputs=[]
        for name in ['Position',*names,'Mask']:
            v=u.CustomInput();v.set_editor_property('input_name',name);inputs.append(v)
        custom.set_editor_property('inputs',inputs);wire(position,custom,'Position');wire(mask,custom,'Mask','R')
        for name,n in zip(names,nodes):wire(n,custom,name,'RGB')
        return custom
    switch=node(u.MaterialExpressionPreviousFrameSwitch);wire(field(0),switch,'Current Frame');wire(field(15),switch,'Previous Frame')
    attrs=next(e for e in L.get_material_expressions(mat) if isinstance(e,u.MaterialExpressionMakeMaterialAttributes))
    wire(switch,attrs,'WorldPositionOffset');mat.set_editor_property('max_world_position_offset_displacement',3.)

def apply_mask(dm,data):
    # The native writer splits positions for UV/normal seams. Duplicates retain
    # the same exact authored point mask in every LOD.
    lookup={tuple(round(c,4) for c in p):v for p,v in zip(data['positions'],data['motion_mask'])}
    _,points,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
    colors=[u.LinearColor(lookup[tuple(round(c,4) for c in (p.x,p.y,p.z))],0,0,1) for p in u.GeometryScript_List.convert_vector_list_to_array(points)]
    u.GeometryScript_VertexColors.set_mesh_per_vertex_colors(dm,u.GeometryScript_List.convert_array_to_color_list(colors))
