"""Scoped, one-time PKM integration edits; preserve unrelated file contents."""
import json,pathlib,shutil,datetime
R=pathlib.Path('D:/FPS3D/FPSGAME');O=pathlib.Path(__file__).parent
backup=O/('BeforeIntegration_'+datetime.datetime.now().strftime('%H%M%S'));backup.mkdir()
def edit(file,pairs):
 p=R/file;raw=p.read_bytes();text=raw.decode('utf-8-sig');newline='\r\n' if b'\r\n' in raw else '\n';text=text.replace('\r\n','\n')
 for old,new in pairs:
  if old not in text:raise RuntimeError('Edit anchor missing: '+file+' '+old[:70])
  text=text.replace(old,new,1)
 target=backup/file;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
 p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.replace('\n',newline).encode())
char='Source/FPSGAME/FPSGAMECharacter.cpp'
edit(char,[
 ('#include "Weapons/A762WeaponAssets.h"','#include "Weapons/A762WeaponAssets.h"\n#include "Weapons/PKMLowpolyWeaponAssets.h"'),
 ('    bUsingReplacement = ViewmodelMesh != nullptr;','''    if (ActiveInventoryWeaponDefinition == PKMLowpolyWeaponAssets::Definition)
    {
        ViewmodelMesh=LoadObject<USkeletalMesh>(nullptr,PKMLowpolyWeaponAssets::MeshPath);
        bUsingM4Infima=ViewmodelMesh!=nullptr;
        HipViewmodelLocation=M4HipViewmodelLocation+FVector(6.f,0.f,0.f);
        ADSRearEyeDistance=20.f;
        QuickCombatAnimation=LoadObject<UAnimSequence>(nullptr,*PKMLowpolyWeaponAssets::AnimationPath(TEXT("quick_melee")));
    }
    bUsingReplacement = ViewmodelMesh != nullptr;'''),
 ('AKMViewmodel->SetBoundsScale(bUseDanWesson715 ?', 'AKMViewmodel->SetBoundsScale(ActiveInventoryWeaponDefinition==PKMLowpolyWeaponAssets::Definition ? 2.f : bUseDanWesson715 ?'),
 ('        InitializeFoldingSights();','        InitializeFoldingSights();\n        PKMLowpolyWeaponAssets::SetSections(AKMViewmodel,false,false,0.f,100);'),
 ('InspectAnimation = bUseDanWesson715 || bUseM16 ?', 'InspectAnimation = bUseDanWesson715 || bUseM16 || PKMLowpolyWeaponAssets::Matches(AKMViewmodel) ?'),
 ('if (bUsingM4Infima && !bUseQBZ191 && !bUseM16 && !IsPistolWeapon())','if (bUsingM4Infima && !bUseQBZ191 && !bUseM16 && !IsPistolWeapon() && !PKMLowpolyWeaponAssets::Matches(AKMViewmodel))'),
 ('    if (!IsPistolWeapon())\n    {\n        InitializeForegripAnimations();','    if (!IsPistolWeapon() && !PKMLowpolyWeaponAssets::Matches(AKMViewmodel))\n    {\n        InitializeForegripAnimations();'),
 ('Sprint->Configure(IsPistolWeapon() ? ERifleSprintWeapon::None','Sprint->Configure(IsPistolWeapon() ? ERifleSprintWeapon::None\n            : PKMLowpolyWeaponAssets::Matches(AKMViewmodel) ? ERifleSprintWeapon::PKM'),
 ('if (bUsingM4Infima && !IsPistolWeapon())\n    {\n        const TCHAR* AudioWeapon','if (bUsingM4Infima && !IsPistolWeapon() && !PKMLowpolyWeaponAssets::Matches(AKMViewmodel))\n    {\n        const TCHAR* AudioWeapon'),
 ('        if (bUseASH12)\n        {\n            // Reference remake:', '''        if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel))
        {
            MechanicalCueTimes={.65f,1.65f,2.6f,4.35f,5.1f,5.72f};
            MechanicalCueSounds={ChargeReleaseSound,MagOutSound,MagOutSound,MagInsertSound,MagSeatSound,ChargeReleaseSound};
            if (bPendingEmptyReload)
            {
                MechanicalCueTimes.Append({6.03f,6.45f});
                MechanicalCueSounds.Append({ChargePullSound,ChargeReleaseSound});
            }
        }
        else if (bUseASH12)
        {
            // Reference remake:'''),
 ('UAnimSequence* AFPSGAMECharacter::RifleQuickCombatClip(EM4SprintGrip Grip)\n{','UAnimSequence* AFPSGAMECharacter::RifleQuickCombatClip(EM4SprintGrip Grip)\n{\n    if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel)) return QuickCombatAnimation;'),
 ('UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)\n{','''UAnimSequence* AFPSGAMECharacter::LoadAKMAnimation(const TCHAR* AssetName)
{
    if (ActiveInventoryWeaponDefinition==PKMLowpolyWeaponAssets::Definition)
    {
        FString Clip(AssetName);Clip.RemoveFromStart(TEXT("A_AKM_"));
        if (Clip.StartsWith(TEXT("equip"))) Clip=TEXT("equip");
        return LoadObject<UAnimSequence>(nullptr,*PKMLowpolyWeaponAssets::AnimationPath(*Clip));
    }'''),
 ('USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)\n{','''USoundBase* AFPSGAMECharacter::LoadAKMSound(const TCHAR* AssetName)
{
    if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel))
        return LoadObject<USoundBase>(nullptr,*FString::Printf(TEXT("/Game/Weapons/AKM/Audio/%s.%s"),AssetName,AssetName));'''),
 ('    if (!GunplayAnimation) return;','''    if (!GunplayAnimation) return;
    PKMLowpolyWeaponAssets::SetSections(AKMViewmodel,IsReloading(),bPendingEmptyReload,
        IsReloading()?ReloadSourceTime(WeaponStateElapsed):0.f,bGunsmithInspection?100:MagazineAmmo);'''),
 ('GunplayAnimation->ActionAlpha = FMath::Min(In, Out);','''GunplayAnimation->ActionAlpha = FMath::Min(In, Out);
        // Both prop sets have different parked poses. Fade only into the reload;
        // its authored grip return hands off to idle without blending props through the gun.
        if (PKMLowpolyWeaponAssets::Matches(AKMViewmodel) && IsReloading()) GunplayAnimation->ActionAlpha=In;'''),
])
edit('Source/FPSGAME/Weapons/M4TacticalSprintComponent.h',[('None, M4, AKM, QBZ191, ASH12, M16','None, M4, AKM, QBZ191, ASH12, M16, PKM')])
edit('Source/FPSGAME/Weapons/M4TacticalSprintComponent.cpp',[
 ('#include "A762WeaponAssets.h"','#include "A762WeaponAssets.h"\n#include "PKMLowpolyWeaponAssets.h"'),
 ('    if (bA762)\n    {','''    if (Weapon==ERifleSprintWeapon::PKM)
    {
        for (int32 Grip=0;Grip<6;++Grip)
            for (const TCHAR* Clip:{TEXT("sprint_enter"),TEXT("sprint_loop"),TEXT("sprint_exit")})
                Clips.Add(LoadObject<UAnimSequence>(nullptr,*PKMLowpolyWeaponAssets::AnimationPath(Clip)));
        return;
    }
    if (bA762)
    {''')])
for file,var,op in [('Source/FPSGAME/FPSGAMECharacterProfile.cpp','I->','||'),('Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp','I.','||'),('Source/FPSGAME/UI/ColdSteelPickupWeapon.cpp','Item.','&&'),('Source/FPSGAME/UI/ColdSteelPickupStudio.cpp','Item.','&&')]:
 cmp='==' if op=='||' else '!=';old=var+'Definition'+cmp+'TEXT("ue_a762")';edit(file,[(old,old+op+var+'Definition'+cmp+'TEXT("ue_pkm_lowpoly")')])
edit('Source/FPSGAME/UI/ColdSteelWarehouseModel.cpp',[
 ('{TEXT("ue_a762"),','{TEXT("ue_pkm_lowpoly"), TEXT("ue_a762"),'),
 ('Gun.Magazine=IsMeleeWeapon(Gun)?0:', 'Gun.Magazine=IsMeleeWeapon(Gun)?0:FString(Definition)==TEXT("ue_pkm_lowpoly")?100:'),
 ('        if(FString(Definition)==TEXT("ue_ash12"))','''        if(FString(Definition)==TEXT("ue_pkm_lowpoly"))
        {
            if(!AddAmmoToState(State,TEXT("ammo_pkm_762x54r"),300))return false;
        }
        if(FString(Definition)==TEXT("ue_ash12"))''')])
edit('Source/FPSGAME/Weapons/WeaponStatEvaluation.cpp',[
 ('{TEXT("ammo_762"),TEXT("7.62x39mm")}', '{TEXT("ammo_762"),TEXT("7.62x39mm")},{TEXT("ammo_pkm_762x54r"),TEXT("7.62x54R mm")}')])
edit('Source/FPSGAME/Characters/FPSBodyAssetPreloader.cpp',[('TEXT("/Game/Weapons/A762/"),','TEXT("/Game/Weapons/A762/"),\n        TEXT("/Game/Weapons/PKMLowpoly20260922/"),')])
edit('Config/DefaultGame.ini',[('+DirectoriesToAlwaysCook=(Path="/Game/Weapons/A762")','+DirectoriesToAlwaysCook=(Path="/Game/Weapons/A762")\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/PKMLowpoly20260922")')])
def data(name,fn):
 p=R/'Content/ColdSteelData'/name;shutil.copy2(p,backup/name);d=json.loads(p.read_text(encoding='utf-8-sig'));fn(d);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def items(d):
 d['ue_pkm_lowpoly']={'category':'weapon','desc':'PKM 弹链供弹机枪，使用 7.62×54R 弹药与 100 发弹箱。','equipSlot':'weapon','icon':'','icon_fallback':'PKM','id':'ue_pkm_lowpoly','isTwoHanded':True,'name':'PKM','rarity':'common','stack_max':1,'stats':[{'name':'物理攻击','value':'7'},{'name':'弹匣容量','value':'100'}],'type':'武器','weaponType':'rifle','grid_w':5,'grid_h':2}
 d['ammo_pkm_762x54r']={'category':'material','desc':'7.62×54R 标准弹，自动计入弹药袋。','icon':'','icon_fallback':'▥','id':'ammo_pkm_762x54r','name':'7.62×54R LPS','rarity':'common','stack_max':999,'type':'弹药'}
def guns(d):
 d['weapons'].append({'id':'ue_pkm_lowpoly','model':'PKMLowpoly','name':'PKM','allowed':[],'base':{'spread_mult':2.5,'ammo_item_id':'ammo_pkm_762x54r','ads_smooth':6.6571828301,'mag_size':100,'recoil':110,'camera_shake':110,'fire_interval':.10,'reload_time':6.5,'empty_reload_time':7.5,'damage':7,'bullet_speed':350,'effective_range':150,'stability_mult':1},'options':{}})
def ammo(d):
 d['types'].append({'id':'ammo_pkm_762x54r','group':'ammo_pkm_762x54r','group_name':'7.62×54R mm','name':'LPS','tier_name':'绿阶','tier_color':'#4CAA70','description':'PKM 标准弹种。','icon':'','order':70,'enabled':True,'allow_infinite_reserve':True,'damage_multiplier':1.0,'physical_armor_penetration':0.0})
data('items.json',items);data('gunsmith.json',guns);data('ammo_types.json',ammo)
print('PKM source and catalog integration written; snapshot:',backup)
