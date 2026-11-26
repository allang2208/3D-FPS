// Legacy Godot exporter. Writes only to Docs/Archives; the live UE table is hand-maintained.
// Do not point this at Content/ColdSteelData: rerunning it would re-add the 274 retired entries.
import fs from 'node:fs';
import vm from 'node:vm';
const source=process.argv[2]||'E:/无尽轮回/长期备份/2026-7-13-1/game-dev';
const target=process.argv[3]||'D:/FPS3D/FPSGAME/Docs/Archives';
const read=p=>fs.readFileSync(source+'/'+p,'utf8');
const ctx=vm.createContext({});
vm.runInContext(read('src/ui/equip-data-manager.js').replace(/\bexport /g,'')+'\nglobalThis.items=EquipDataManager;',ctx);
const fields=['attackFormula','matkFormula','armorSet','bonusStats','bonusPerEnhance','defense','setBonusDesc'];
const output={};
function visit(o,identity=''){
 if(!o||typeof o!=='object')return;
 if(o.name&&fields.some(k=>o[k])){
  const value=Object.fromEntries(fields.filter(k=>o[k]).map(k=>[k,o[k]]));
  for(const key of [o.weaponId,o.id,o.name,identity])if(key)output[key]=value;
 }
 for(const [key,value] of Object.entries(o))if(value&&typeof value==='object')visit(value,Array.isArray(o)?'':key);
}
visit(ctx.items);visit(JSON.parse(read('data/equipment.json')));
fs.writeFileSync(target+'/legacy-gamedev-combat-items-regenerated.json',JSON.stringify(output,null,2)+'\n');
console.log('Exported legacy combat metadata to '+target+'/legacy-gamedev-combat-items-regenerated.json (live table untouched)');
