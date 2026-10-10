from pathlib import Path
root=Path(__file__).resolve().parent
text=(root.parent/'CrystalCraftV33/install_ue.py').read_text(encoding='utf-8')
text=text.replace('V33','V37').replace('CrystalCraftV37','ElementHeadsV37').replace("'revision':33","'revision':37")
text=text.replace('def localized_emission(g,kind,mask,inner=False):','def localized_emission(g,kind,mask,inner=False,phase=None):')
text=text.replace("'Jade':(.09,.53,.20),'Storm':(.29,.13,1.)", "'Jade':(.09,.53,.20),'Storm':(.38,.22,1.)")
text=text.replace("g.wire(time,sine,'Input')", "g.wire(g.add(time,g.mul(phase,g.scalar(2.9))) if phase is not None else time,sine,'Input')")
text=text.replace("idle={'Ice':.16,'Magma':4.0,'Jade':.26,'Storm':5.0 if inner else .45}[kind]", "idle={'Ice':.12,'Magma':3.2,'Jade':.20,'Storm':4.2 if inner else .25}[kind]")
text=text.replace("g.output(g.scalar(.78 if kind=='Mount' else 0.),u.MaterialProperty.MP_METALLIC)", "g.output(g.scalar(.82 if kind=='Mount' else 0.),u.MaterialProperty.MP_METALLIC)")
text=text.replace("g.output(packed,u.MaterialProperty.MP_OPACITY,'G')", """edge=g.node(u.MaterialExpressionFresnel,exponent=3.0,base_reflect_fraction=0.)
        cover=g.add(g.channel(packed,'G'),g.mul(edge,g.scalar(.14 if kind=='Ice' else .18)))
        g.output(cover,u.MaterialProperty.MP_OPACITY)
        # Angle-dependent absorption stays restrained. No refraction sheets or fog.
        body=g.mul(base,g.add(g.scalar(1.),g.mul(edge,g.scalar(-.24))),'RGB')
        g.output(body,u.MaterialProperty.MP_BASE_COLOR)""")
text=text.replace("g.color((.45,.78,.40))","g.color((.32,.65,.38))").replace("g.scalar(.58),u.MaterialProperty.MP_OPACITY","g.scalar(.70),u.MaterialProperty.MP_OPACITY")
text=text.replace("g.color((.013,.007,.03))", "g.color((.010,.006,.024))").replace("g.color((.18,.09,.42))","g.color((.23,.15,.46))").replace("g.color((.12,.31,.36))","g.color((.075,.20,.26))")
text=text.replace("g.output(g.scalar(.34),u.MaterialProperty.MP_ROUGHNESS)", "g.output(g.scalar(.20 if kind=='Storm' else .25),u.MaterialProperty.MP_ROUGHNESS)")
text=text.replace("localized_emission(g,kind,mask,inner=True)", "localized_emission(g,kind,mask,inner=True,phase=g.channel(vertex,'G') if kind=='Storm' else None)")
if 'apply_installed_surface' not in text:
    text=text.replace('    def finish(self):\n', '''    def finish(self):
        polish_recipe=ROOT.parent/'ElementPolishV42/ue_material.py'
        if polish_recipe.exists():
            import runpy
            runpy.run_path(str(polish_recipe))['apply_installed_surface'](self.mat)
''')
(root/'install_ue.py').write_text(text,encoding='utf-8')
print('V37_INSTALLER_WRITTEN')
