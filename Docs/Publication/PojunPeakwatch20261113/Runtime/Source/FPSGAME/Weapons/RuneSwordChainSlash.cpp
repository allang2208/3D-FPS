#include "RuneSwordComponent.h"
#include "PojunGrip.h"
#include "../Production/ProductionToolComponent.h"
#include "FPSMeleeLightningComponent.h"
#include "MeleeSmallTargetQuery.h"
#include "../Skills/ChainSlashAssets.h"
#include "../Skills/ChainSlashMotion.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/LightningHasteSpeed.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace
{
float ChainSourceTime(float PlaybackTime)
{
    return ChainSlashMotion::SourceTime(PlaybackTime);
}

float ChainPlaybackTime(float SourceTime)
{
    return ChainSlashMotion::PlaybackTime(SourceTime);
}
}

UAnimSequence* URuneSwordComponent::ChainSlashAnimation(bool Pojun) const
{
    static const TSoftObjectPtr<UAnimSequence> PojunClip{FSoftObjectPath(ChainSlash::Pojun)};
    if(Pojun)return PojunClip.Get();
    const bool Long=EquippedAnimationFolder.EndsWith(TEXT("/LongGripAnimations"));
    static const TSoftObjectPtr<UAnimSequence> StandardClip{FSoftObjectPath(ChainSlash::Standard)};
    static const TSoftObjectPtr<UAnimSequence> LongClip{FSoftObjectPath(ChainSlash::LongGrip)};
    return (Long?LongClip:StandardClip).Get();
}

FString URuneSwordComponent::ChainSlashStatusText(bool bPaid) const
{
    const auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    const auto* Item=PojunGrip::ChainSlashWeapon(Model);
    if(!Item)return TEXT("需双手剑或破军长柄");
    if(bChainSlashPending)return TEXT("准备中");
    if(bChainSlash)return TEXT("连斩中");
    const auto* Pawn=Character.Get();
    if(!Pawn||!CanUse()||UBoundCongregateCaptureComponent::IsCaptured(Pawn))return TEXT("暂不可用");
    if(IsBusy()||bGuardHeld||Pawn->IsCastBlockingLeftHandAction())return TEXT("动作占用");
    const bool Pojun=PojunGrip::Installed(*Item);
    if(Pojun)
    {
        const auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>();
        if(Pawn->IsDodging()||Pawn->IsSliding()||(PS&&PS->IsQuickCombatExecuting(Pawn)))return TEXT("动作占用");
        const auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();
        if(!Tool||Tool->IsBusy()||Tool->HasAuthorityAttackInFlight()||Tool->IsLeapAimPreviewActive())return TEXT("动作占用");
        if(Pawn->IsLocallyControlled())
        {
            const auto* Arms=Tool->ArmsMesh();
            const auto* Mesh=Arms?Arms->GetSkeletalMeshAsset():nullptr;
            const auto* Pose=ChainSlashAnimation(true);
            if(!Tool->HasReadyPresentation()||Tool->EquippedId!=Item->InstanceId||!Mesh||!Pose||
                Mesh->GetSkeleton()!=Pose->GetSkeleton())return TEXT("动作准备中");
        }
    }
    else if(InstanceId!=Item->InstanceId)return TEXT("需双手剑");
    if(!Model||Model->MasteryProgress(TEXT("chainSlash")).Level<1)return TEXT("未学习");
    if(!bPaid)
    {
        if(Model->ChainSlashCooldown()>0.f)return TEXT("冷却中");
        if(!Model->CanSpendStamina(Model->ChainSlashStats().StaminaCost))return TEXT("体力不足");
    }
    const auto* Clip=ChainSlashAnimation(Pojun);
    if(Pojun)return Clip?FString():FString(TEXT("动作准备中"));
    const auto* Mesh=Viewmodel?Viewmodel->GetSkeletalMeshAsset():nullptr;
    return Clip&&Mesh&&Mesh->GetSkeleton()==Clip->GetSkeleton()?FString():FString(TEXT("动作准备中"));
}

float URuneSwordComponent::ChainSlashActionRate() const
{
    return FMath::Max(.05f,LightningHaste::ActionSpeed(Character.Get())*ChainGripRate);
}

bool URuneSwordComponent::StartChainSlash(bool bPaid)
{
    if(!ChainSlashStatusText(bPaid).IsEmpty())return false;
    auto* Pawn=Character.Get();
    auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Held=PojunGrip::ChainSlashWeapon(Model);
    if(!Held||Held->InstanceId!=ChainWeaponId||(bPaid&&PojunGrip::Installed(*Held)!=ChainTool.IsValid()))return false;
    // The stamina transaction can rebuild the profile inventory during this cast.
    const FColdSteelItem CastWeapon=*Held;
    const FColdSteelItem* Item=&CastWeapon;
    ChainTool=PojunGrip::Installed(*Item)?Pawn->FindComponentByClass<UProductionToolComponent>():nullptr;
    UAnimSequence* Clip=ChainSlashAnimation(ChainTool.IsValid());
    static const FName CutNames[]={TEXT("Cut1"),TEXT("Cut2"),TEXT("Cut3"),TEXT("Cut4")};
    ChainSlashContacts.Reset();
    for(FName Name:CutNames)
    {
        const auto* Marker=Clip->AuthoredSyncMarkers.FindByPredicate([Name](const FAnimSyncMarker& M){return M.MarkerName==Name;});
        if(!Marker)return false;
        ChainSlashContacts.Add(Marker->Time);
    }
    const FChainSlashCast Cast=Model->ChainSlashStats();
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Model);
    const auto* Grip=PojunGrip::Modifiers(Item,Model);
    ChainGripRate=Grip?float(Grip->AttackSpeed):1.f;
    const float BeforeStamina=Model->Stamina();
    if(Pawn->HasAuthority()&&!Model->CommitChainSlashCast(Cast))return false;
    if(bInspecting)CancelAction();
    bChainSlash=true;
    ChainSlashCut=0;
    ChainImpactMask=0;
    ChainLastImpact=ChainRibbonCut=INDEX_NONE;
    ChainImpactAt=-1.;
    StopRift();
    SwingSkills=ColdSteelSkills::Snapshot(Pawn,Item);
    const auto Hammer=ChainTool.IsValid()?ColdSteelTool::Evaluate(*Item,Model):FProductionToolStats{};
    const double DamageBase=ChainTool.IsValid()?Hammer.Damage.Total():Stats.Damage;
    ChainSlashDamage=float(DamageBase*Cast.DamageMultiplier*Stats.Modifiers.MartialDamage);
    SwingReach=ChainTool.IsValid()?Hammer.CombatReachCM:Stats.SlashReach;
    SwingSkills.AttackForm=EMonsterAttackForm::Blade;
    // Meta 0 keeps damage-derived poise. ChainSlashDamage already includes the
    // level's 40%-120% coefficient; applying it to ToughnessDamageMultiplier
    // again would square the coefficient. Preserve the weapon's poise bonuses.
    SwingSkills.AttackMeta=0;
    SwingSkills.WeakpointPercent=0.f;
    ChainSlashKills=0;ChainSlashKilledTargets.Reset();
    bChainSlashTrainingPending=Pawn->HasAuthority();ChainSlashRewardModel=Model;
    if(Pawn->HasAuthority())
    {
        ChainGaleKey=GaleWing::Key(GaleWing::EAttack::Chain,ChainSlashSerial);
        RecordGalePayment(ChainGaleKey,Item->InstanceId,BeforeStamina-Model->Stamina());
        SwingSkills.GalePaymentKey=ChainGaleKey;
    }
    bPommelAttack=bQueuedAttack=bQueuedQuickCombat=false;
    HitActors.Reset();
    ScheduleWalkInspect(true);
    if(auto* Tool=ChainTool.Get())
    {
        CurrentClip=TEXT("ChainSlash");CurrentAnimation=Clip;Elapsed=0.f;SweepHitPause=0.f;
        PreviousAimFrame=Pawn->GetMeleeAimTransform();
        Tool->CancelInspect();
        if(Pawn->IsLocallyControlled())
        {
            Tool->Motions.Add(TEXT("PojunChain"),Clip);
            Tool->SamplePojunChain(0.f,Clip->GetPlayLength(),ChainSlashContacts);
        }
    }
    else
    {
        Animations.Add(TEXT("ChainSlash"),Clip);
        SetClip(TEXT("ChainSlash"),false);
    }
    return true;
}

bool URuneSwordComponent::BeginChainSlash()
{
    if(!ChainSlashStatusText().IsEmpty())return false;
    const auto* Item=PojunGrip::ChainSlashWeapon(ColdSteelAuthority::ForPawn(Character.Get()));
    if(!Item)return false;
    ChainWeaponId=Item->InstanceId;
    ChainTool=PojunGrip::Installed(*Item)?GetOwner()->FindComponentByClass<UProductionToolComponent>():nullptr;
    if(++ChainSlashSerial==0)++ChainSlashSerial;
    if(!GetOwner()->HasAuthority())
    {
        bChainSlashPending=true;
        ServerChainSlash(ChainWeaponId,ChainSlashSerial,true,ChainTool.IsValid());
        return true;
    }
    return StartChainSlash();
}

void URuneSwordComponent::ServerChainSlash_Implementation(const FString& Weapon,uint32 Serial,bool bStart,bool bPojun)
{
    if(!bStart)
    {
        if(bChainSlash&&Serial==ChainSlashSerial&&Weapon==ChainWeaponId)CancelAction();
        return;
    }
    if(!Serial||int32(Serial-ChainSlashReceivedSerial)<=0)return;
    ChainSlashReceivedSerial=Serial;
    auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    bool bAccepted=false;
    const auto* Item=PojunGrip::ChainSlashWeapon(Model);
    if(!bChainSlash&&Item&&Weapon==Item->InstanceId&&PojunGrip::Installed(*Item)==bPojun)
    {
        ChainSlashSerial=Serial;
        ChainWeaponId=Weapon;
        bAccepted=StartChainSlash();
    }
    const auto State=Model?Model->Snapshot():FColdSteelProfile();
    const auto* GS=GetWorld()->GetGameState();
    ClientChainSlashResult(Serial,bAccepted,State.UppercutStaminaSpent,State.ChainSlashCooldown,
        State.ChainSlashCooldownDuration,State.MartialCooldownRevision,
        GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds());
}

void URuneSwordComponent::ClientChainSlashResult_Implementation(uint32 Serial,bool bAccepted,double TotalSpent,
    float Cooldown,float Duration,int64 Revision,double ServerAt)
{
    if(auto* Model=ColdSteelAuthority::ForPawn(Character.Get()))
        Model->ApplyChainSlashReceipt(TotalSpent,Cooldown,Duration,Revision,ServerAt);
    if(Serial!=ChainSlashSerial)return;
    const bool bRequested=bChainSlashPending;bChainSlashPending=false;
    // The accepted payment arrives before the local windup starts.
    if(bAccepted&&bRequested&&StartChainSlash(true))return;
    if(bAccepted)ServerChainSlash(ChainWeaponId,Serial,false,ChainTool.IsValid());
    ChainTool.Reset();
}

void URuneSwordComponent::FinishChainSlashTraining()
{
    if(!bChainSlashTrainingPending)return;
    bChainSlashTrainingPending=false;
    auto* Model=ChainSlashRewardModel.Get();const int32 Kills=ChainSlashKills;
    ChainSlashRewardModel.Reset();ChainSlashKilledTargets.Reset();ChainSlashKills=0;
    if(Model)Model->TrainChainSlash(Kills);
}

void URuneSwordComponent::HitChainSlashRange(const FTransform& Aim)
{
    auto* Pawn=Character.Get();
    const uint32 CastSerial=ChainSlashSerial;
    const int32 Cut=ChainSlashCut;
    auto Hits=RuneSwordCombat::QueryFrontSlash(GetWorld(),Pawn,Aim,SwingReach,HitActors);
    Hits.Append(MeleeSmallTargets::QueryLowSector(GetWorld(),Pawn,Aim,SwingReach,HitActors));
    if(Hits.IsEmpty())return;
    ColdSteelAuthority::FScope Authority(ColdSteelAuthority::ForPawn(Pawn));
    for(const FHitResult& Hit:Hits)
    {
        AActor* Target=Hit.GetActor();
        if(!bChainSlash||ChainSlashSerial!=CastSerial)return;
        if(!UFPSMeleeLightningComponent::IsEnemy(Target,Pawn)||HitActors.Contains(Target))continue;
        HitActors.Add(Target);
        const bool bTrainingTarget=ColdSteelSkills::IsMasteryTrainingTarget(Pawn,Target);
        const TWeakObjectPtr<AActor> TargetKey=Target;
        FWeaponDamageResult Result;
        const float Applied=ColdSteelSkills::ApplyHit(Pawn,Hit,ChainSlashDamage,Aim.GetUnitAxis(EAxis::X),SwingSkills,&Result);
        if(Applied>0.f)
        {
            const bool bFirst=bChainSlash&&ChainSlashSerial==CastSerial&&!(ChainImpactMask&(1u<<Cut));
            if(bFirst)
            {
                ApplyChainImpact(Cut);
                if(!Pawn->IsLocallyControlled())ClientChainImpact(CastSerial,Cut);
            }
            MulticastChainContact(IsValid(Target)?Target:nullptr,Hit.ImpactPoint,Hit.ImpactNormal,bFirst,Cut==3);
            if(bTrainingTarget&&Result.bKilled&&!ChainSlashKilledTargets.Contains(TargetKey))
            {ChainSlashKilledTargets.Add(TargetKey);++ChainSlashKills;}
            if(IsValid(Target))Pawn->NotifyConfirmedWeaponHit(Target,Applied,&Result);
        }
    }
}

void URuneSwordComponent::TickChainSlash(float Delta)
{
    auto* Pawn=Character.Get();
    const auto* HeldWeapon=PojunGrip::ChainSlashWeapon(ColdSteelAuthority::ForPawn(Pawn));
    if(!Pawn||!HeldWeapon||HeldWeapon->InstanceId!=ChainWeaponId||PojunGrip::Installed(*HeldWeapon)!=ChainTool.IsValid()||
        !CurrentAnimation||!CanUse(true)||Pawn->IsCastBlockingLeftHandAction()||UBoundCongregateCaptureComponent::IsCaptured(Pawn))
    {
        CancelAction();
        return;
    }
    const float End=CurrentAnimation->GetPlayLength();
    const float ActionRate=ChainSlashActionRate();
    const FTransform Aim=Pawn->GetMeleeAimTransform();
    constexpr float HalfWindow=.09f;
    float Remaining=Delta;
    while(Remaining>0.f&&Elapsed<End)
    {
        const float Held=FMath::Min(Remaining,SweepHitPause);
        SweepHitPause-=Held;
        Remaining-=Held;
        if(Remaining<=0.f)break;
        const bool bHasCut=ChainSlashContacts.IsValidIndex(ChainSlashCut);
        const float Mark=bHasCut?ChainSlashContacts[ChainSlashCut]:End;
        const float Open=Mark-HalfWindow,Close=Mark+HalfWindow;
        const float Boundary=FMath::Min(End,!bHasCut?End:(Elapsed<Open?Open:(Elapsed<Mark?Mark:Close)));
        const float Before=Elapsed;
        const float PlaybackBefore=ChainPlaybackTime(Before);
        const float PlaybackBoundary=ChainPlaybackTime(Boundary);
        const float PlaybackEnd=FMath::Min(PlaybackBefore+Remaining*ActionRate,PlaybackBoundary);
        Elapsed=FMath::Min(ChainSourceTime(PlaybackEnd),Boundary);
        // Land on the exact source marker when this real-time slice reaches it.
        if(PlaybackEnd>=PlaybackBoundary)Elapsed=Boundary;
        if(Elapsed<=Before)break;
        // Haste advances the shared pose/contact/sound clock; impact hold stays in real seconds.
        Remaining=FMath::Max(0.f,Remaining-(PlaybackEnd-PlaybackBefore)/ActionRate);
        if(bHasCut&&Before<Mark&&Elapsed>=Mark&&Pawn->IsLocallyControlled())
        {
            if(auto* Tool=ChainTool.Get())Tool->PlayPojunSwing(.72f);
            else if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.72f);
        }
        if(bHasCut&&Pawn->HasAuthority()&&Elapsed>Open&&Before<Close)
        {
            FTransform ContactAim;
            ContactAim.Blend(PreviousAimFrame,Aim,FMath::Clamp(1.f-Remaining/Delta,0.f,1.f));
            HitChainSlashRange(ContactAim);
            if(!bChainSlash)return;
        }
        if(bHasCut&&Elapsed>=Close){++ChainSlashCut;HitActors.Reset();}
    }
    if(auto* Tool=ChainTool.Get())
    {
        if(Pawn->IsLocallyControlled())Tool->SamplePojunChain(Elapsed,End,ChainSlashContacts);
    }
    else SamplePose(Elapsed);
    if(!ChainTool.IsValid()&&Pawn->IsLocallyControlled())PresentChainRibbon();
    PreviousAimFrame=Aim;
    if(Elapsed>=End)
    {
        StopRift();
        bChainSlash=false;
        FinishChainSlashTraining();
        HitActors.Reset();
        if(ChainTool.IsValid()){ChainTool.Reset();CurrentAnimation=nullptr;CurrentClip=NAME_None;}
        else SetClip(TEXT("Idle"),true);
    }
}
