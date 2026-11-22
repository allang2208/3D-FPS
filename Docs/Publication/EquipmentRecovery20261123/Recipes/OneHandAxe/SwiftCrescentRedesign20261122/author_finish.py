"""Editable Cycles/EEVEE look development for the Swift Crescent redesign."""
from pathlib import Path
import bpy

OUT = Path(__file__).resolve().parent


def steel(name, undertone, highlight, roughness, anisotropy, grain):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_fake_user = True
    mat.diffuse_color = (*undertone, 1)
    mat.asset_mark()
    tree = mat.node_tree
    bsdf = tree.nodes.get("Principled BSDF")
    bsdf.location = (600, 100)
    tree.nodes.get("Material Output").location = (900, 100)
    bsdf.inputs["Metallic"].default_value = 1
    bsdf.inputs["Anisotropic"].default_value = anisotropy

    def node(kind, label, x, y):
        n = tree.nodes.new(kind)
        n.label = label
        n.location = (x, y)
        return n

    def wire(a, out, b, inp):
        tree.links.new(a.outputs[out], b.inputs[inp])

    uv = node("ShaderNodeTexCoord", "UV follows the curve", -900, 200)
    scale = node("ShaderNodeVectorMath", "Directional grain", -670, 280)
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = grain
    wire(uv, "UV", scale, 0)
    fine = node("ShaderNodeTexNoise", "Fine directional surface", -430, 275)
    fine.inputs["Scale"].default_value = 1
    fine.inputs["Detail"].default_value = 1.5
    wire(scale, "Vector", fine, "Vector")
    broad = node("ShaderNodeTexNoise", "Slow variation in finish", -430, -70)
    broad.inputs["Scale"].default_value = 6
    broad.inputs["Detail"].default_value = 2
    wire(uv, "UV", broad, "Vector")
    colors = node("ShaderNodeValToRGB", "Steel tone", -75, -95)
    colors.color_ramp.elements[0].color = (*undertone, 1)
    colors.color_ramp.elements[1].color = (*highlight, 1)
    wire(broad, "Fac", colors, "Fac")
    wire(colors, "Color", bsdf, "Base Color")
    gloss = node("ShaderNodeMapRange", "Roughness range", -80, 290)
    gloss.inputs["To Min"].default_value, gloss.inputs["To Max"].default_value = roughness
    wire(fine, "Fac", gloss, "Value")
    wire(gloss, "Result", bsdf, "Roughness")
    tangent = node("ShaderNodeTangent", "Follow UV grain direction", 205, -160)
    tangent.direction_type = "UV_MAP"
    wire(tangent, "Tangent", bsdf, "Tangent")
    bump = node("ShaderNodeBump", "Subtle grain under raking light", 180, 80)
    bump.inputs["Strength"].default_value = .085
    bump.inputs["Distance"].default_value = .000018
    wire(fine, "Fac", bump, "Height")
    wire(bump, "Normal", bsdf, "Normal")
    return mat


def make_palette():
    return [
        steel("SwiftCrescent | satin blue steel", (.23,.267,.307), (.32,.357,.397), (.29,.43), .34, (28,470,1)),
        steel("SwiftCrescent | recessed graphite", (.105,.119,.131), (.17,.182,.198), (.44,.62), .10, (220,300,1)),
        steel("SwiftCrescent | pale brushed silver", (.52,.55,.58), (.69,.70,.72), (.22,.34), .54, (19,650,1)),
    ]


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    make_palette()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"SwiftCrescent_Finish.blend"), compress=True)
