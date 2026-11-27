# AudioSession20261127 共享宿主定向接入清单

以下 4 份文件在当前本机工作区已由并行重构从 `FPSGAMECharacter.cpp` / `PlayerSkillPreparation.cpp` 拆分，而 `origin/main`（基线 `22797e331`）尚未合入该拆分。为避免向公开 `main` 夹带未验收并行拆分或引入重复符号冲突，按 `WORKFLOW.md` 第 8 节将本批在这 4 份宿主中的精确挂点记录于此；本机工作区均已完成落地并编入 `UnrealEditor-FPSGAME.dll`。

## 1. `Source/FPSGAME/FPSGAMECharacterActionPose.cpp`（L401–L412）
**用途**：SVCh 左拉栓装备（`EquipLeftBolt-20261126`）让 `EquipAnimation` 与换弹动作一样选择当前握把家族的原生 `UWeaponGripProfile`（并回退至 `EM4SprintGrip::Base`），无需改动共享 `A_SVD_equip`。
```cpp
if(SVCHWeaponAssets::Matches(AKMViewmodel)
    && (ActiveActionAnimation==ReloadAnimation || ActiveActionAnimation==ReloadEmptyAnimation || ActiveActionAnimation==EquipAnimation))
{
    auto* ReloadProfile=WeaponGripProfileFor(ResolveRifleGripProfile());
    if(!ReloadProfile || !ReloadProfile->Find(ActiveActionAnimation))
        ReloadProfile=WeaponGripProfileFor(EM4SprintGrip::Base);
    if(ReloadProfile && ReloadProfile->Find(ActiveActionAnimation))
    {
        GunplayAnimation->ActionClip=ActiveActionAnimation;
        GunplayAnimation->ActionGripProfile=ReloadProfile;
    }
}
```

## 2. `Source/FPSGAME/FPSGAMECharacterAssetsAudio.cpp`（L484–L502）
**用途**：`LoadAKMSound` 对 SVCh 解析专属 `S_SVCH_EquipRaise`（装备抬枪）与 5 条换弹/拉栓机械音（缺失时回退 SVD），供本机播放与 `UFPSPlayerBodyComponent::DescribeGun` 联机远端发布复用。
```cpp
if(SVCHWeaponAssets::Matches(AKMViewmodel))
{
    if(FCString::Strcmp(AssetName,TEXT("S_AKM_Fire"))==0)
        if(auto* S=LoadObject<USoundBase>(nullptr,*SVCHWeaponAssets::FireSoundPath(1)))return S;
    if(FCString::Strcmp(AssetName,TEXT("S_AKM_Equip"))==0)
        if(auto* S=LoadObject<USoundBase>(nullptr,*SVCHWeaponAssets::MechanicalSoundPath(TEXT("EquipRaise"))))return S;
    if(FCString::Strcmp(AssetName,TEXT("S_AKM_MagOut"))==0 ||
       FCString::Strcmp(AssetName,TEXT("S_AKM_MagInsert"))==0 ||
       FCString::Strcmp(AssetName,TEXT("S_AKM_MagSeat"))==0 ||
       FCString::Strcmp(AssetName,TEXT("S_AKM_ChargePull"))==0 ||
       FCString::Strcmp(AssetName,TEXT("S_AKM_ChargeRelease"))==0)
    {
        FString Cue(AssetName);
        Cue.RemoveFromStart(TEXT("S_AKM_"));
        if(auto* S=LoadObject<USoundBase>(nullptr,*SVCHWeaponAssets::MechanicalSoundPath(*Cue)))return S;
        return LoadObject<USoundBase>(nullptr,*SVDWeaponAssets::MechanicalSoundPath(*Cue));
    }
    return LoadObject<USoundBase>(nullptr,*FString::Printf(TEXT("/Game/Weapons/AKM/Audio/%s.%s"),AssetName,AssetName));
}
```

## 3. `Source/FPSGAME/FPSGAMECharacterWeaponState.cpp`（L575–L580）
**用途**：SVCh 装备开始时先播 `EquipSound`（`S_SVCH_EquipRaise`），随后按 `SVCHWeaponAssets::EquipPull` / `EquipRelease` 源时钟触发左拉栓两段机械音。
```cpp
else if (SVCHWeaponAssets::Matches(AKMViewmodel))
{
    PlayMechanicalSound(EquipSound, AKMSource::ActionVolume);
    MechanicalCueTimes={SVCHWeaponAssets::EquipPull,SVCHWeaponAssets::EquipRelease};
    MechanicalCueSounds={ChargePullSound,ChargeReleaseSound};
}
```

## 4. `Source/FPSGAME/Skills/PlayerSkillAssets.cpp`（L50）
**用途**：将穿心箭发射音效 `/Game/Skills/HeartPiercingArrow/Audio20261026/S_HeartPiercingArrow_Release` 纳入 `PlayerSkillAssets::Gather` 异步预热，减少远端观察者首次听到穿心箭发射时的异步加载等待。
```cpp
if(Skill==TEXT("heartPiercingArrow"))AddSkillAsset(Out,TEXT("/Game/Skills/HeartPiercingArrow/Audio20261026/S_HeartPiercingArrow_Release.S_HeartPiercingArrow_Release"));
```
