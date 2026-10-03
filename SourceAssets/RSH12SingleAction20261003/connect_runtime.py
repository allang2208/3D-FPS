"""Publish the RSH-only single-action routing and mechanical source clock."""
from pathlib import Path
import json
O=Path(__file__).parent;P=O.parents[1];edits=[]
def edit(rel,changes):
    path=P/rel;raw=path.read_bytes();text=raw.decode('utf-8-sig').replace('\r\n','\n')
    for before,after in changes:
        before=before.replace('\r\n','\n');after=after.replace('\r\n','\n')
        if before not in text:raise RuntimeError('Source anchor missing '+rel+' '+before[:65])
        if text.count(before)!=1:raise RuntimeError('Ambiguous source anchor '+rel)
        text=text.replace(before,after,1)
    out=O/'BeforeSource'/rel;out.parent.mkdir(parents=True,exist_ok=True)
    if not out.exists():out.write_bytes(raw)
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent source edit '+rel)
    path.write_text(text,encoding='utf8',newline='')
    edits.append(rel)
edit('Source/FPSGAME/Weapons/RSH12WeaponAssets.h',[(
    '// Native 715 source clips plus the RSH-12 base profile provide all motion.\r\n    inline FString AnimationPath(const TCHAR* Clip) { return DanWesson715WeaponAssets::AnimationPath(Clip); }',
    '''inline constexpr float CockLatch = .60f;
    inline constexpr float FireCycle = 1.f;
    inline constexpr const TCHAR* ProfilePath = TEXT("/Game/Weapons/RSH12/SingleAction20261003/Profiles/DA_RSH12_base");
    inline FString DualProfilePath(int32 Side)
    {
        return FString::Printf(TEXT("/Game/Weapons/RSH12/SingleAction20261003/Profiles/DA_RSH12_%s_base"),Side?TEXT("l"):TEXT("r"));
    }
    inline FString DualFirePath(int32 Side)
    {
        const TCHAR* Hand=Side?TEXT("l"):TEXT("r");
        return FString::Printf(TEXT("/Game/Weapons/RSH12/SingleAction20261003/%s/A_RSH12_%s_fire"),Hand,Hand);
    }
    // Fire/cock has its own source duration; the rest of the 715 family stays shared.
    inline FString AnimationPath(const TCHAR* Clip)
    {
        if(FCString::Strcmp(Clip,TEXT("fire"))==0 || FCString::Strcmp(Clip,TEXT("aim_fire"))==0)
            return FString::Printf(TEXT("/Game/Weapons/RSH12/SingleAction20261003/single/A_RSH12_%s"),Clip);
        return DanWesson715WeaponAssets::AnimationPath(Clip);
    }''')])
edit('Source/FPSGAME/Weapons/SVDGripProfiles.cpp',[
    ('#include "SVDWeaponAssets.h"','#include "SVDWeaponAssets.h"\n#include "RSH12WeaponAssets.h"'),
    (':TEXT("/Game/Weapons/AnimationProfiles20261001/")+ActiveInventoryWeaponDefinition+TEXT("/DA_")+Family.ToString();',
     ':IsRSH12Weapon()&&Family==TEXT("base")?FString(RSH12WeaponAssets::ProfilePath)\n        :TEXT("/Game/Weapons/AnimationProfiles20261001/")+ActiveInventoryWeaponDefinition+TEXT("/DA_")+Family.ToString();')])
edit('Source/FPSGAME/FPSGAMECharacter.cpp',[
    ('*DanWesson715WeaponAssets::AnimationPath(*Clip));','*(IsRSH12Weapon()?RSH12WeaponAssets::AnimationPath(*Clip):DanWesson715WeaponAssets::AnimationPath(*Clip)));'),
    ('PlayWeaponAnimation(Animation, false, ShotAnimationRate);',
     '''if(Animation && IsRSH12Weapon())
        ShotAnimationRate=Animation->GetPlayLength()/FMath::Max(.01f,float(ShotInterval));
    PlayWeaponAnimation(Animation, false, ShotAnimationRate);
    if(IsRSH12Weapon())
    {
        // The whole source action is one single-action cycle, including the thumb return.
        NextAllowedShotTime=Now+FMath::Max(ShotInterval,double(ActionDuration));
        NextMechanicalCue=0;
    }'''),
    ('if (!bInventoryWeaponReady || IsWeaponBusy() || (!ResumeCycle',
     'if (!bInventoryWeaponReady || (IsWeaponBusy() && !IsRevolverFireActionPlaying()) || (!ResumeCycle'),
    ('return IsDoorPushActive() || IsTraversing() || (RuneSword && RuneSword->IsBusy()) ||',
     'return (IsRSH12Weapon() && IsRevolverFireActionPlaying()) || (DualPistols && DualPistols->IsSingleActionCocking())\n        || IsDoorPushActive() || IsTraversing() || (RuneSword && RuneSword->IsBusy()) ||'),
    ('float SourceTime = ActionStartPosition + ActionElapsed * ActionPlayRate;',
     '''float SourceTime = ActionStartPosition + ActionElapsed * ActionPlayRate;
        if(IsRSH12Weapon() && bFireAction && SourceTime>=RSH12WeaponAssets::CockLatch && NextMechanicalCue==0)
        {
            PlaySound2D(DryClickSound,.65f);
            NextMechanicalCue=1;
        }'''),
    ('ActiveActionAnimation = nullptr;\r\n            GunplayAnimation->ActionAlpha = 0.0f;',
     '''ActiveActionAnimation = nullptr;
            GunplayAnimation->ActionAlpha = 0.0f;
            if(IsRSH12Weapon() && bFireAction && WeaponState==EAKMWeaponState::Idle)
            {SetAimingState(bAimHeld);ResumeWeaponPose();}''')])
edit('Source/FPSGAME/FPSGAMECharacterActionPriority.cpp',[
    ('if(IsDoorPushActive() || IsSwitchingWeapon() || bResolvingActionInterrupt || !IsLocallyControlled())return false;',
     'if(IsDoorPushActive() || IsSwitchingWeapon() || (IsRSH12Weapon() && IsRevolverFireActionPlaying()) || bResolvingActionInterrupt || !IsLocallyControlled())return false;')])
edit('Source/FPSGAME/Weapons/PistolDualWieldComponent.h',[
    ('bool IsEquipping() const;','bool IsEquipping() const;\n    bool IsSingleActionCocking() const;')])
edit('Source/FPSGAME/Weapons/PistolDualWieldComponent.cpp',[
    ('const FString Path=FString::Printf(TEXT("/Game/Weapons/AnimationProfiles20261001/%s/Dual_%s/DA_%s"),*Item.Definition,Index?TEXT("l"):TEXT("r"),Family);',
     'const FString Path=Item.Definition==RSH12WeaponAssets::Definition && FString(Family)==TEXT("base")\n            ?RSH12WeaponAssets::DualProfilePath(Index):FString::Printf(TEXT("/Game/Weapons/AnimationProfiles20261001/%s/Dual_%s/DA_%s"),*Item.Definition,Index?TEXT("l"):TEXT("r"),Family);'),
    ('if(PitViper){H.Clips.Add(Kind,LoadObject<UAnimSequence>(nullptr,*PitViper2011WeaponAssets::DualAnimationPath(Index,Kind)));return;}',
     'if(Item.Definition==RSH12WeaponAssets::Definition && Kind==TEXT("fire")){H.Clips.Add(Kind,LoadObject<UAnimSequence>(nullptr,*RSH12WeaponAssets::DualFirePath(Index)));return;}\n        if(PitViper){H.Clips.Add(Kind,LoadObject<UAnimSequence>(nullptr,*PitViper2011WeaponAssets::DualAnimationPath(Index,Kind)));return;}'),
    ('void UPistolDualWieldComponent::StopAction(int32 Index)',
     '''bool UPistolDualWieldComponent::IsSingleActionCocking() const
{
    if(!bActive)return false;
    for(int32 Side=FirstHand();Side<Hands.Num();++Side)
    {
        const auto& H=Hands[Side];
        if(H.Item.Definition==RSH12WeaponAssets::Definition && H.Action && H.Action==H.Clips.FindRef(TEXT("fire"))
            && GetWorld()->GetTimeSeconds()<H.ActionStarted+H.Action->GetPlayLength()/FMath::Max(.01f,H.ActionRate))return true;
    }
    return false;
}
void UPistolDualWieldComponent::StopAction(int32 Index)'''),
    ('if(!Player->CanStartQuickCombatPriority())return TEXT("切换武器或输入不可用");',
     'if(IsSingleActionCocking())return TEXT("RSH-12正在拨回击锤");\n    if(!Player->CanStartQuickCombatPriority())return TEXT("切换武器或输入不可用");'),
    ('if(H.Reloading)AdvanceReload(Side,Previous);',
     '''if(H.Item.Definition==RSH12WeaponAssets::Definition && H.Action==H.Clips.FindRef(TEXT("fire"))
                && H.ActionTime>=RSH12WeaponAssets::CockLatch && !H.PlayedCues.Contains(TEXT("RSH12CockLatch")))
            {
                if(auto* Sound=H.Sounds.FindRef(TEXT("DryClick")).Get())UGameplayStatics::PlaySound2D(this,Sound,.65f);
                H.PlayedCues.Add(TEXT("RSH12CockLatch"));
            }
            if(H.Reloading)AdvanceReload(Side,Previous);''')])
edit('Source/FPSGAME/Weapons/PistolDualWieldCombat.cpp',[
    ('#include "G18WeaponAssets.h"','#include "G18WeaponAssets.h"\n#include "RSH12WeaponAssets.h"'),
    ('H.Pending=false;\r\n    if(WeaponReloadStages::NeedsCycle',
     'if(H.Item.Definition==RSH12WeaponAssets::Definition && H.Action && H.Action==H.Clips.FindRef(TEXT("fire")))return;\n    H.Pending=false;\n    if(WeaponReloadStages::NeedsCycle'),
    ('StartAction(Index,!H.Revolver && H.Rounds==0?TEXT("fire_last"):TEXT("fire"));',
     '''const float FireRate=H.Item.Definition==RSH12WeaponAssets::Definition && H.Clips.FindRef(TEXT("fire"))
        ?H.Clips.FindRef(TEXT("fire"))->GetPlayLength()/float(ShotInterval):1.f;
    StartAction(Index,!H.Revolver && H.Rounds==0?TEXT("fire_last"):TEXT("fire"),FireRate);
    if(H.Item.Definition==RSH12WeaponAssets::Definition && H.Action)
        H.NextShot=Now+FMath::Max(ShotInterval,double(H.Action->GetPlayLength()/FireRate));'''),
    ('if(H.Reloading||(Index==1&&Player->IsCastBlockingLeftHandAction()))return false;',
     'if(H.Reloading || (H.Item.Definition==RSH12WeaponAssets::Definition && H.Action && H.Action==H.Clips.FindRef(TEXT("fire"))) || (Index==1&&Player->IsCastBlockingLeftHandAction()))return false;')])
edit('Source/FPSGAME/UI/ColdSteelIconResources.cpp',[
    ('Add(TEXT("/Game/Weapons/AnimationProfiles20261001/ue_rsh12/DA_base"),true);','Add(RSH12WeaponAssets::ProfilePath,true);')])
(O/'runtime_edits.json').write_text(json.dumps(dict(files=edits,scope='RSH12 only; no reflected instance fields added',tested=False),indent=2),encoding='utf8')
print('RSH12_SINGLE_ACTION_RUNTIME_CONNECTED',len(edits))
