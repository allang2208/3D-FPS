#include "ProductionToolComponent.h"
#include "../Weapons/PojunGrip.h"
#include "WarhammerUppercutArc.h"
#include "WarhammerUppercutMotion.h"
#include "ProductionBluntCombo.h"
#include "../Weapons/RuneSwordRisingDragon.h"
#include "WarhammerAudioPaths.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/SwordUppercutTuning.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/RuneSwordUppercutMotion.h"
#include "../Weapons/RuneSwordHitQuery.h"
#include "../Weapons/MeleeSmallTargetQuery.h"
#include "../Weapons/RuneSwordMeshComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Weapons/RuneSwordCombatTuning.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace
{
bool CanUppercut(AFPSGAMECharacter* Pawn,const UColdSteelStatusModel* Profile,bool bContinuing=false)
{
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    const auto* PS=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    const auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
    const auto* Tool=Pawn?Pawn->FindComponentByClass<UProductionToolComponent>():nullptr;
    return Pawn&&PC&&Item&&PojunGrip::UsesHammerMotion(*Item)&&
        (!Sword||(!Sword->IsGuarding()&&!Sword->IsPojunChainOccupied()))&&(!Tool||!Tool->IsThunderHammerAway())&&(!PS||!PS->IsQuickCombatExecuting(Pawn))&&
        !Pawn->IsTraversing()&&!Pawn->IsDodging()&&!Pawn->IsSliding()&&!Pawn->IsCastBlockingLeftHandAction()&&
        !UBoundCongregateCaptureComponent::IsCaptured(Pawn)&&(!Health||!Health->IsDead())&&
        !(bContinuing?AFPSGAMEPlayerController::BlocksActionContinuation(PC):AFPSGAMEPlayerController::BlocksOngoingActions(PC))&&(!Build||!Build->IsBuilding());
}
constexpr float HitPause=.05f;
}

FString UProductionToolComponent::UppercutStatusText() const
{
    if(!IsEquipped()||Kind!=TEXT("warhammer"))return TEXT("需双手近战");
    if(bBluntUppercut)return TEXT("上挑中");
    const auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!CanUppercut(Character.Get(),Profile)||!CanUse())return TEXT("暂不可用");
    if(Profile->SwordUppercutCooldown()>0.f)return TEXT("冷却中");
    if(!Profile->CanSpendStamina(Profile->SwordUppercutStaminaCost()))return TEXT("体力不足");
    if(IsBusy())return TEXT("动作中");
    const UAnimSequence* Clip=Motions.FindRef(TEXT("Uppercut"));
    if(!HasReadyPresentation()||!Clip||Clip->GetSkeleton()!=Viewmodel->GetSkeletalMeshAsset()->GetSkeleton())return TEXT("动作准备中");
    return FString();
}

bool UProductionToolComponent::BeginUppercut()
{
    if(!UppercutStatusText().IsEmpty())return false;
    auto* Pawn=Character.Get();
    auto* Profile=Pawn->HasAuthority()?ColdSteelAuthority::ForPawn(Pawn):GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    ++BluntAttackId;BluntServerAttackId=BluntAttackId;
    StartBluntUppercut(Profile);
    if(!Pawn->HasAuthority())ServerBeginBluntUppercut(BluntAttackId);
    return bBluntUppercut;
}

void UProductionToolComponent::ServerBeginBluntUppercut_Implementation(uint32 AttackId)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    if(!CanUppercut(Pawn,Profile)||IsLeapStrikeActive()||bBluntUppercut||bBluntWhirlwind||bBluntServerCharging||
        GetWorld()->GetTimeSeconds()<BluntServerReadyAt||Profile->SwordUppercutCooldown()>0.f||
        !Profile->CanSpendStamina(Profile->SwordUppercutStaminaCost()))
    {ClientBluntUppercutResult(AttackId,false);return;}
    Character=Pawn;BluntAttackId=BluntServerAttackId=AttackId;
    StartBluntUppercut(Profile);ClientBluntUppercutResult(AttackId,true);
}

void UProductionToolComponent::ClientBluntUppercutResult_Implementation(uint32 AttackId,bool Accepted)
{if(AttackId==BluntAttackId&&!Accepted)FinishBluntUppercut();}

void UProductionToolComponent::ClientBluntUppercutImpact_Implementation(uint32 AttackId)
{
    if(!bBluntUppercut||AttackId!=BluntAttackId)return;
    BluntUppercutPause=HitPause;BluntUppercutImpactAge=0.f;
}

void UProductionToolComponent::StartPojunAttack(PojunGrip::EAttack Attack,UColdSteelStatusModel* Profile)
{
    const auto* Item=Profile->ActiveProductionTool();
    if(!Item)return;
    PojunAttack=Attack;PojunAttackItemData=Item->Data;
    Elapsed=-1.f;bQueuedBluntAttack=bBluntChain=bBluntFloorTarget=false;
    BluntStartClip=0.f;BluntServerGroundSlamUntil=BluntServerSprintContactAt=0.;
    if(Attack==PojunGrip::EAttack::Zhufeng)
    {
        StartBluntWhirlwind(Profile);
        return;
    }
    StartBluntUppercut(Profile);
}

void UProductionToolComponent::StartBluntUppercut(UColdSteelStatusModel* Profile)
{
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;if(!Item)return;
    ColdSteelAuthority::FScope Scope(Profile);
    bBluntUppercut=true;bBluntUppercutReleased=bBluntUppercutLungeStarted=bBluntUppercutLungeBlocked=false;
    BluntUppercutTime=BluntUppercutPause=0.f;BluntUppercutImpactAge=1.f;
    BluntUppercutHits=BluntUppercutKills=0;BluntUppercutHitActors.Reset();
    BluntUppercutDirection=FVector::ZeroVector;BluntUppercutInstance=Item->InstanceId;
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
    ApplyToolStats(Item,Profile);
    PojunSlashTime=-1.f;
    if(PojunAttack==PojunGrip::EAttack::Ordinary)
    {
        const auto Effect=Profile->MasteryEffect(TEXT("swordUppercut"));
        BluntUppercutDamage=Stats.Damage*ColdSteelMelee::UppercutMultiplier(Profile,Stats.Modifiers);
        BluntUppercutReach=Stats.ThrustReach*Effect.UppercutReachMultiplier;
        BluntUppercutRange=RuneSwordCombatTuning::RangeMultiplier*Stats.Modifiers.Range*
            Profile->MasteryDefinition(TEXT("swordUppercut")).UppercutRangeMultiplier;
        BluntUppercutShot=ColdSteelSkills::Snapshot(Character.Get(),Item);
        BluntUppercutShot.bMelee=true;BluntUppercutShot.WeakpointPercent=0.f;
        BluntUppercutShot.AttackMeta=SwordUppercut::AttackMeta;
        BluntUppercutShot.DamagePanel=Stats.DamageParts.Scaled(Stats.Damage>0.?BluntUppercutDamage/Stats.Damage:0.);
        BluntUppercutShot.ToughnessDamageMultiplier=float(ToolStats.ToughnessDamage*Stats.Modifiers.HeavyToughness);
        BluntUppercutShot.CriticalChance=FMath::Clamp(BluntUppercutShot.CriticalChance+float(ToolStats.CriticalChanceAdd),0.f,100.f);
    }
    else
    {
        const bool Rising=PojunAttack==PojunGrip::EAttack::Tengyun;
        PojunSlashTime=Rising?-1.f:PojunChixiao::Start;
        const auto& Mods=Stats.Modifiers;
        AxeStrike.AttackMeta=Rising?3:0x10;
        AxeStrike.bRisingDragonFinisher=Rising;
        AxeStrike.DamagePanel=ToolStats.Damage.Scaled(Rising?Mods.ComboMultiplier(3):BluntHeavyMultiplier);
        AxeStrike.ToughnessDamageMultiplier=float(ToolStats.ToughnessDamage*(Rising?Mods.ComboThirdToughness:Mods.HeavyToughness));
        BluntUppercutShot=AxeStrike;
        BluntUppercutDamage=BluntUppercutShot.DamagePanel.Total();
        BluntUppercutReach=AxeCombatReach;BluntUppercutRange=RuneSwordCombatTuning::RangeMultiplier*Mods.Range;
    }
    bQueuedBluntAttack=false;bBluntHeavy=bBluntSprintAttack=false;NextBluntStage=0;
    BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;SetTickGroup(TG_PostPhysics);
    BluntServerReadyAt=GetWorld()->GetTimeSeconds()+(RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)+HitPause)/HasteActionRate;
    if(PojunAttack!=PojunGrip::EAttack::Ordinary)
    {
        const float Lead=PojunSlashTime>=0.f?PojunChixiao::Handoff-PojunChixiao::Start:-RuneSwordRisingDragon::WindupEnd;
        BluntServerReadyAt=GetWorld()->GetTimeSeconds()+
            (Lead+RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)+HitPause)/PojunCutRate();
    }
    Character->StopMovementForMeleeSkill();
}

bool UProductionToolComponent::PojunAttackStillEquipped(const FColdSteelItem& Item)
{
    if(PojunAttack==PojunGrip::EAttack::Ordinary||Item.Data==PojunAttackItemData)return true;
    if(PojunGrip::Attack(Item,PojunAttack==PojunGrip::EAttack::Chixiao,PojunAttack==PojunGrip::EAttack::Zhufeng,2)!=PojunAttack)return false;
    PojunAttackItemData=Item.Data;
    return true;
}

float UProductionToolComponent::PojunCutRate() const
{
    return PojunAttack==PojunGrip::EAttack::Chixiao?RateScale*BluntMasteryInterval:RateScale;
}

float UProductionToolComponent::BluntUppercutPoseTime() const
{return WarhammerUppercutMotion::PoseTime(BluntUppercutTime);}

void UProductionToolComponent::TickBluntUppercut(float Delta)
{
    auto* Pawn=Character.Get();if(!Pawn)return;
    auto* Profile=Pawn->HasAuthority()?ColdSteelAuthority::ForPawn(Pawn):GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!CanUppercut(Pawn,Profile,true)||!Item||Item->InstanceId!=BluntUppercutInstance)
    {FinishBluntUppercut();return;}
    ColdSteelAuthority::FScope Scope(Profile);
    if(!PojunAttackStillEquipped(*Item))
    {FinishBluntUppercut();return;}
    Delta*=PojunAttack==PojunGrip::EAttack::Ordinary?HasteActionRate:PojunCutRate();
    if(PojunSlashTime>=0.f)
    {
        const float Before=PojunSlashTime;
        const float Handoff=PojunChixiao::Handoff;
        PojunSlashTime=FMath::Min(Handoff,Before+Delta);
        Delta-=PojunSlashTime-Before;
        const float Whoosh=ProductionBluntCombo::WhooshClip(PojunChixiao::OpeningStage);
        if(Before<Whoosh&&PojunSlashTime>=Whoosh&&Pawn->IsLocallyControlled())
            PlayPojunSwing(.95f,.9f);
        if(Before<ProductionBluntCombo::ContactSeconds&&PojunSlashTime>=ProductionBluntCombo::ContactSeconds&&Pawn->HasAuthority())
            ResolveBluntContact(BluntHeavyStunSeconds);
        if(!bBluntUppercut||PojunSlashTime<Handoff)return;
        PojunSlashTime=-1.f;
        if(Pawn->HasAuthority())
            BluntUppercutShot.MasteryAttackSerial=ColdSteelSkills::Snapshot(Pawn,Profile->ActiveProductionTool()).MasteryAttackSerial;
    }
    if(PojunAttack==PojunGrip::EAttack::Tengyun&&BluntUppercutTime<RuneSwordUppercutMotion::ReleaseStart)
        Delta+=FMath::Min(Delta,(RuneSwordUppercutMotion::ReleaseStart-BluntUppercutTime)*.5f);
    const float Pause=FMath::Min(Delta,BluntUppercutPause);BluntUppercutPause-=Pause;Delta-=Pause;
    if(Delta<=0.f){if(Viewmodel)Viewmodel->ClearMotionVector();return;}
    BluntUppercutImpactAge+=Delta;
    const float End=RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End);
    float Remaining=FMath::Min(Delta,End-BluntUppercutTime);
    while(Remaining>UE_SMALL_NUMBER&&bBluntUppercut)
    {
        const float Step=FMath::Min(Remaining,1.f/120.f),From=BluntUppercutPoseTime();
        const float BeforeTime=BluntUppercutTime;
        BluntUppercutTime+=Step;Remaining-=Step;
        const float To=BluntUppercutPoseTime();
        if(!bBluntUppercutReleased&&To>=RuneSwordUppercutMotion::ReleaseStart)
        {
            if(Pawn->HasAuthority()&&PojunAttack==PojunGrip::EAttack::Ordinary)
            {
                const float StaminaBefore=Profile->Stamina();
                if(!Profile->CommitSwordUppercutRelease())
                {ClientBluntUppercutResult(BluntAttackId,false);FinishBluntUppercut();return;}
                SendBluntMartialReceipt(Profile,BluntAttackId,FMath::Max(0.f,StaminaBefore-Profile->Stamina()));
            }
            if(!bBluntUppercut)return;
            bBluntUppercutReleased=true;
        }
        if(BeforeTime<WarhammerUppercutMotion::StrikeStart&&BluntUppercutTime>=WarhammerUppercutMotion::StrikeStart&&
            Pawn->IsLocallyControlled())
        {
            if(bPojunGrip)PlayPojunSwing(.72f,1.1f);
            else if(auto* Sound=Cast<USoundBase>(WarhammerAudioPaths::Uppercut.ResolveObject()))
                UGameplayStatics::PlaySound2D(this,Sound,.72f,1.f);
        }
        const FTransform Before=Pawn->GetMeleeAimTransform();
        // Remote authority gets capsule displacement from the shared movement
        // protocol. Only the owner/listen-host authors the requested stride.
        if(Pawn->IsLocallyControlled()&&!bBluntUppercutLungeBlocked)
        {
            const float Distance=RuneSwordUppercutMotion::LungeDistance*
                (RuneSwordUppercutMotion::LungeAlpha(RuneSwordUppercutMotion::SkillSourceTime(BluntUppercutTime),true)-
                 RuneSwordUppercutMotion::LungeAlpha(RuneSwordUppercutMotion::SkillSourceTime(BeforeTime),true));
            if(Distance>0.f)
            {
                auto* Move=Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
                if(!Move||!Move->IsMovingOnGround())bBluntUppercutLungeBlocked=true;
                else
                {
                    if(!bBluntUppercutLungeStarted)
                    {
                        bBluntUppercutLungeStarted=true;BluntUppercutDirection=Before.GetUnitAxis(EAxis::X).GetSafeNormal2D();
                        Move->BeginMeleeLungeRequest(EFPSMeleeMove::Uppercut,BluntUppercutDirection);
                    }
                    if(Move->IsMeleeLungeRejected())bBluntUppercutLungeBlocked=true;
                    else
                    {
                        const FVector Moved=Move->ApplyMeleeLungeStep(BluntUppercutDirection,Distance);
                        const float Actual=FMath::Max(0.f,float(FVector::DotProduct(Moved,BluntUppercutDirection)));
                        Move->RecordMeleeLungeStep(Actual);if(Actual+.01f<Distance)bBluntUppercutLungeBlocked=true;
                    }
                }
            }
        }
        if(Pawn->HasAuthority()&&bBluntUppercutReleased&&(BluntUppercutHitActors.IsEmpty()||PojunAttack==PojunGrip::EAttack::Chixiao||PojunAttack==PojunGrip::EAttack::Tengyun))
            SweepBluntUppercut(From,To,Before,Pawn->GetMeleeAimTransform());
        if(BluntUppercutPause>0.f)break;
    }
    if(bBluntUppercut&&BluntUppercutTime>=End-UE_SMALL_NUMBER)
    {
        const bool NextCut=PojunAttack==PojunGrip::EAttack::Tengyun&&bQueuedBluntAttack&&Pawn->IsLocallyControlled();
        FinishBluntUppercut();
        if(NextCut)BeginUse();
    }
}

void UProductionToolComponent::SweepBluntUppercut(float From,float To,const FTransform& Before,const FTransform& After)
{
    // The idle-grip gather keeps the head beside the torso. Damage begins with
    // the visible strike/whoosh, not during the preceding foot push-off.
    const float A=FMath::Max(From,WarhammerUppercutMotion::LoadedSource),B=FMath::Min(To,RuneSwordUppercutMotion::Finish);
    if(B<=A)return;
    auto* Pawn=Character.Get();
    const auto Sample=[&](float Time,const FTransform& Aim)
    {
        FRuneSwordBladeSample Result;Result.Origin=Aim.GetLocation();Result.Forward=Aim.GetUnitAxis(EAxis::X);
        const FVector Local=WarhammerUppercutArc::Sample(Time);
        const FVector Axis=Local.GetSafeNormal();
        Result.Base=Aim.TransformPosition(Axis*15.f);
        Result.Tip=Aim.TransformPosition(Axis*BluntUppercutReach);
        return Result;
    };
    const bool Rising=PojunAttack==PojunGrip::EAttack::Tengyun;
    const bool Cleave=Rising||PojunAttack==PojunGrip::EAttack::Chixiao;
    FRuneSwordTraceSettings Settings;Settings.bCleavePawns=Cleave;Settings.bAreaDamage=Rising;Settings.Radius=RuneSwordCombat::BladeRadius*BluntUppercutRange;
    auto Hits=RuneSwordCombat::Query(GetWorld(),Pawn,Sample(A,Before),Sample(B,After),BluntUppercutReach,BluntUppercutHitActors,Settings);
    if(Rising)Hits.Append(MeleeSmallTargets::QueryLowSector(GetWorld(),Pawn,After,BluntUppercutReach,BluntUppercutHitActors));
    bool Confirmed=false;
    for(const auto& Hit:Hits)
    {
        auto* Target=Hit.GetActor();if(!IsValid(Target)||BluntUppercutHitActors.Contains(Target))continue;
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();if(Combat&&Combat->IsDead())continue;
        FWeaponDamageResult Result;
        const float Applied=ColdSteelSkills::ApplyHit(Pawn,Hit,BluntUppercutDamage,After.GetUnitAxis(EAxis::X),BluntUppercutShot,&Result);
        if(Applied<=0.f&&!(Combat&&Combat->IsDead()))continue;
        if(BluntUppercutShot.ItemDefinition==PojunGrip::Weapon)MulticastPojunCutImpact(Hit.ImpactPoint);
        BluntUppercutHitActors.Add(Target);
        if(Combat&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))
        {++BluntUppercutHits;if(Combat->IsDead())++BluntUppercutKills;}
        Pawn->NotifyConfirmedWeaponHit(Target,Applied,&Result);
        if(!bBluntUppercut)return;
        Confirmed=true;
        if(!Cleave)break;
    }
    if(Confirmed)
    {
        BluntUppercutPause=HitPause;BluntUppercutImpactAge=0.f;
        if(!Pawn->IsLocallyControlled())ClientBluntUppercutImpact(BluntAttackId);
    }
}

void UProductionToolComponent::FinishBluntUppercut()
{
    if(!bBluntUppercut)return;
    const bool Train=bBluntUppercutReleased&&PojunAttack==PojunGrip::EAttack::Ordinary;
    PojunAttack=PojunGrip::EAttack::Ordinary;PojunSlashTime=-1.f;PojunAttackItemData.Reset();bQueuedBluntAttack=false;
    bBluntUppercut=false;bBluntUppercutReleased=false;BluntUppercutPause=0.f;
    if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->ClearWhirlwindEntry();
    if(Train&&Character.IsValid()&&Character->HasAuthority())
        if(auto* Profile=ColdSteelAuthority::ForPawn(Character.Get()))
        {ColdSteelAuthority::FScope Scope(Profile);Profile->TrainSwordUppercut(BluntUppercutHits,BluntUppercutKills);}
    BluntUppercutHitActors.Reset();BluntServerReadyAt=GetWorld()->GetTimeSeconds();VisualTime=0.f;NextBluntStage=0;
}
