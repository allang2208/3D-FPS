import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
const source='E:/无尽轮回/长期备份/2026-7-13-1/game-dev';
const out='D:/FPS3D/FPSGAME/Saved/CoreFormulaAudit';fs.mkdirSync(out,{recursive:true});
const read=p=>fs.readFileSync(source+'/'+p,'utf8');
const formulas=JSON.parse(read('data/combat-formulas.json'));
const context=vm.createContext({COMBAT_FORMULAS:formulas,CONFIG:{PLAYER_SPEED:130.528125,STAMINA_MAX:100,DODGE_DURATION:250,DODGE_SPEED:600},applyTributeEffects:()=>{}});
const code=read('src/entities/player/base.js').replace(/^import .*;\r?$/gm,'').replace(/^export .*;?\r?$/gm,'');
vm.runInContext(code+'\nglobalThis.base=baseMixin;',context);
const defense=await import('data:text/javascript;base64,'+Buffer.from(read('src/combat/defense-formula.js')).toString('base64'));
const fields=['atk','def','matk','mdef','crit','critRes','aspd','speed','maxHp','maxMp','mpRegen'];
const players=[];
for(let n=0;n<60;n++){
 const attrs=n===0?[10,10,10,10,10,10]:Array.from({length:6},(_,i)=>(n*17+i*31)%137);
 const [str,dex,int,con,wis,luck]=attrs,level=1+n%30;
 const p=Object.assign({},context.base,{data:{str,dex,int,con,wis,luck,level,maxHp:0,maxMp:0},
 _getEquipmentBonuses:()=>Object.fromEntries(['str','dex','int','con','wis','luck','atk','matk','crit','maxHp','maxMp','maxStamina','defense'].map(k=>[k,0])),
 _getEquipmentMatkBonus:()=>0,_applyDungeonBuffBonus:()=>{},getExpForLevel:()=>0});
 p.calculateCombatStats();p.updateMaxStats();
 players.push({attrs,level,expected:fields.map(k=>p.data[k])});
}
const cases=[];
const equipment=read('src/ui/equip-data-manager.js');
const weaponMap={ue_m4a1:'M416_ITEM',ue_akm:'AKM_ITEM',ue_qbz191:'QBZ191_ITEM',ue_m1911:'M1911A1_ITEM',ue_dan_wesson715:'REVOLVER357_ITEM',ue_rune_sword:'RUNE_SWORD_ITEM'};
const weapons={},weaponCases=[];
const attackContext=vm.createContext({});
vm.runInContext(read('src/config/attack-formula.js').replace(/^import .*;\r?$/gm,'').replace(/export\s*\{[\s\S]*?\};?/g,'').replace(/export /g,''),attackContext);
for(const [id,name] of Object.entries(weaponMap)){
 const start=equipment.indexOf(name+': {');
 if(start<0)throw Error('Missing '+name);
 const line=equipment.slice(start).split(/\r?\n/).find(l=>l.includes('attackFormula:'));
 const raw=line.slice(line.indexOf('attackFormula:')+14).trim().replace(/,\s*$/,'');
 const formula=vm.runInNewContext('('+raw+')');weapons[id]={source:name,...formula};
 for(const p of players)for(const level of [0,1,5,15]){
  const d=Object.fromEntries(['str','dex','int','con','wis','luck'].map((k,i)=>[k,p.attrs[i]]));
  weaponCases.push({id,level,base:formula.base,flat:formula.enhanceFlat,terms:formula.attrs.map(t=>[d[t.key],t.base,t.perEnhance]),expected:attackContext.calculateAttackFormula(formula,d,level)});
 }
}
fs.writeFileSync('D:/FPS3D/FPSGAME/Content/ColdSteelData/combat-weapon-formulas.json',JSON.stringify(weapons,null,2));
for(const damage of [.5,1,9,10,59,100,333.5,10000])for(const def of [0,1,15,35,60,65,540,10000])
for(const magic of [false,true])for(const penetration of [0,.15,.5,1])for(const shred of [0,.25,.95])for(const corrosion of [1,.7]){
 const target={data:{def,mdef:def},getMagicResistanceShredRatio:()=>shred,getCorrosionDefenseMul:()=>corrosion};
 const shooter={data:{atk:damage,matk:damage},getCurrentWeapon:()=>({_craftEffects:{armorPenetrationPercent:penetration,magicPenetrationPercent:penetration}})};
 cases.push({damage,def,magic,penetration,shred,corrosion,expected:defense.applyDefenseToDamage(damage,shooter,target,magic?'magic':'physical')});
}
const provenance=Object.fromEntries(['data/combat-formulas.json','src/entities/player/base.js','src/combat/defense-formula.js','src/config/enemy-base-stats.js','src/config/attack-formula.js','src/ui/equip-data-manager.js'].map(p=>[p,crypto.createHash('sha256').update(read(p)).digest('hex')]));
fs.writeFileSync(out+'/reference.json',JSON.stringify({source,provenance,fields,players,cases,weaponCases},null,2));
console.log(`Generated ${players.length} original-player cases and ${cases.length} original-defense cases`);
