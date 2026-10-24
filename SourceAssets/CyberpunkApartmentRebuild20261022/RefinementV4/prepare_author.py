from pathlib import Path
root=Path(__file__).resolve().parent;old=root.parent/'RefinementV3'
text=(old/'refinement_design.py').read_text('utf8').replace('/RefinementV3','/RefinementV4')
(root/'refinement_design.py').write_text(text,encoding='utf8')
text=(old/'author.py').read_text('utf8')
text=text.replace("from refinement_design import *","sys.path.append(str(Path(__file__).resolve().parent.parent/'RefinementV3'))\nfrom refinement_design import *")
text=text.replace("apply_v3(globals(),refinement)","apply_v3(globals(),refinement)\nfrom cabinet_upgrade import apply_v4\napply_v4(globals(),refinement)")
text=text.replace("ROOT.parent/'RefinementV2/assembly.json'","ROOT.parent/'RefinementV3/assembly.json'")
text=text.replace("reused_revision='RefinementV2'","reused_revision='RefinementV3'")
(root/'author.py').write_text(text,encoding='utf8')
print('V4_AUTHOR_CREATED')
