from pathlib import Path
p=Path(__file__).with_name('build_drop_reload.py');s=p.read_text()
s=s.replace('(8,10,-18)','(8,10,12)').replace('(10,7,-35)','(10,7,22)')
a=s.index(' trusted=[]');b=s.index(' raw=[]',a)
s=s[:a]+" trusted=[{n:gun[k]@src['P']['WPN_root'].inverted()@m for n,m in src['P'].items()} for k,src in enumerate(reference)]\n"+s[b:]
s=s.replace(' for phase in [0,1]:',' for phase in [1]:')
a=s.index("   row={'frame':t}");b=s.index('   # Reuse the accepted R5 limb',a)
s=s[:a]+"   row={'frame':t}\n"+s[b:]
s=s.replace("   if t>=lock:\n    for b in r.pose.bones:\n     if b.name.endswith('_r')", "   if True:\n    for b in r.pose.bones:\n     if b.name.endswith('_r')")
a=s.index('  if phase==0:');b=s.index(" a.name='BeforeThrow_'",a)
s=s[:a]+s[b:]
p.write_text(s)
