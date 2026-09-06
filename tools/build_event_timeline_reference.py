"""Render harness using original DOM/CSS/JS functions, with Godot's forecast fixture.

Read-only source repository; output only task reference artifacts.
"""
from pathlib import Path
import shutil

SOURCE = Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev')
OUTPUT = Path(__file__).resolve().parents[1] / 'docs/preview/event-timeline'
OUTPUT.mkdir(parents=True, exist_ok=True)
for file in ['game-style.css', 'ui/panel-theme-backpack.css']:
    target = OUTPUT / file
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / file, target)
for file in (SOURCE / 'assets/ui/event-icons').glob('*.png'):
    target = OUTPUT / 'assets/ui/event-icons' / file.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(file, target)
source = (SOURCE / 'src/ui/game-ui-manager.js').read_text(encoding='utf-8')
helpers = source[source.index('const TIMELINE_PROGRESS_COLORS'):source.index('// 统计只跟随')]
refresh = source[source.index('    refreshGameTime() {'):source.index('    setupWeaponSwitchButtons() {')]
dom_source = (SOURCE / 'src/ui/panels/hud-panels-misc.js').read_text(encoding='utf-8')
dom = dom_source.split('invasionHud.innerHTML = `', 1)[1].split('`;', 1)[0]
html = '''<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="game-style.css"><link rel="stylesheet" href="ui/panel-theme-backpack.css">
<style>body{background:#657078!important;margin:0}#worldInvasionHud{display:block!important}*{animation:none!important}</style>
<div id="worldInvasionHud" class="world-invasion-hud is-compact">''' + dom + '''</div><script>
const getElementIfExists = id => document.getElementById(id);
const EnvironmentLightingSystem={getGameTime:()=>({day:1,hour:12,minute:0,period:'白昼',icon:'☀'}),getSun:()=>({phase:.25})};
window.WorldInvasionSystem={getHudModel:()=>({text:'暂无入侵情报',active:false})};
''' + helpers + '''
const manager={_timelineFilterType:'all',refreshBasicResources(){},
''' + refresh + '''};
window.ready=fetch('fixture.json').then(r=>r.json()).then(events=>{
const mapping={type_label:'typeLabel',time_label:'timeLabel',icon_path:'iconPath',world_name:'worldName',intensity_name:'intensityName',duration_label:'durationLabel',warning_level:'warningLevel',warning_label:'warningLabel',starts_at_label:'startsAtLabel',ends_at_label:'endsAtLabel'};
window.events=events.map(e=>{const out={...e};for(const [a,b] of Object.entries(mapping))out[b]=e[a];if(out.iconPath)out.iconPath=out.iconPath.replace('res://','');return out;});
window.WorldEventTimelineSystem={getHudModel:()=>({events:window.events,nowPosition:.04,durationDays:5})};
manager.refreshGameTime();
document.querySelector('#worldTimelineModeToggle').onclick=()=>document.querySelector('#worldInvasionHud').classList.toggle('is-compact');
document.querySelector('#worldTimelinePopoverClose').onclick=closeTimelinePopover;
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeTimelinePopover();});
});</script>'''
(OUTPUT / 'source.html').write_text(html, encoding='utf-8')
print(OUTPUT / 'source.html')
