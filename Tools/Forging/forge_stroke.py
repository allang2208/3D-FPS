"""Shared runtime/source strike timing: twice-speed downstroke, unchanged recovery."""


def apply_stroke(data):
    # Windup stays at 160 ms. The 160–340 ms downstroke is compressed to 160–250 ms.
    # Keep the full 480 ms contact/recovery phase and the runtime's separate target gap.
    data['contact_seconds']=.25
    data['stroke_seconds']=.73
    data['stroke']=[{'t':t,'angle':a,'offset':o} for t,a,o in [
        (0,-30,[-4,-4,10]),(.16,-48,[-4,-4,15]),(.20,-28,[-3,-4,10]),
        (.25,0,[0,0,0]),(.29,0,[0,0,0]),
        (.36,-18,[1,-1,6]),(.40,-16,[.8,-.8,5.5]),
        (.53,-30,[-3,-4,7]),(.73,-30,[-4,-4,10])]]
    data['stroke_markers_seconds']={'Windup':.16,'CONTACT score + sound + sparks':.25,
                                    'Rebound':.36,'Ready':.73}
    data['motion_revision']='FastDownstroke2x_20260927'
    return data


if __name__=='__main__':
    import json
    import shutil
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    path=root/'Content/ColdSteelData/forge-grip.json'
    source=root/'SourceAssets/ForgeInteraction20260927'
    backup=source/'BeforeFastDownstroke';backup.mkdir(exist_ok=True)
    for original in (path,source/'ForgeTools_V7_Grasp.blend'):
        archived=backup/original.name
        if not archived.exists():
            shutil.copy2(original,archived)
    data=json.loads(path.read_text(encoding='utf-8'))
    apply_stroke(data)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FORGE_STRIKE_TIMING_SAVED',str(path),'contact=',data['contact_seconds'],'duration=',data['stroke_seconds'])
