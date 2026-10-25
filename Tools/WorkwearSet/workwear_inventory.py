"""Shared production icon studio, writing only this revision's source folder."""
import types
from workwear_common import *
def studio(output,key):
    path=P/'Tools/FieldHat/render_icon.py';code=path.read_text(encoding='utf-8')
    code=code.replace('world.use_nodes = True','world.use_nodes = True\n    world.node_tree.nodes.clear()\n    bg=world.node_tree.nodes.new("ShaderNodeBackground")\n    bg.name="Background"\n    output=world.node_tree.nodes.new("ShaderNodeOutputWorld")\n    world.node_tree.links.new(bg.outputs[0],output.inputs[0])')
    start=code.index('    destinations = [family /');end=code.index('    for dest in destinations:',start)
    code=code[:start]+'    destinations = []\n'+code[end:]
    code=code.replace('width = round(320 * item["grid_w"] / item["grid_h"])','width = 160 * item["grid_w"]').replace('height = 320','height = 160 * item["grid_h"]')
    m=types.ModuleType('workwear_inventory');exec(compile(code,str(path),'exec'),m.__dict__);m.OUT=output;m.FAMILIES[key]='WorkwearSet20261024';return m
