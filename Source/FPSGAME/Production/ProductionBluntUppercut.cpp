#include "ProductionToolComponent.h"
#include "WarhammerUppercutArc.h"
#include "WarhammerUppercutMotion.h"
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
bool CanUppercut(AFPSGAMECharacter* Pawn,const UColdSteelStatusModel* Profile)
{
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    const auto* PS=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    const auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
    return Pawn&&PC&&Item&&ColdSteelInventory::IsTwoHandedBlunt(*Item)&&
        (!Sword||!Sword->IsGuarding())&&(!PS||!PS->IsQuickCombatExecuting(Pawn))&&
        !Pawn->IsTraversing()&&!Pawn->IsDodging()&&!Pawn->IsSliding()&&!Pawn->IsCastBlockingLeftHandAction()&&
        !UBoundCongregateCaptureComponent::IsCaptured(Pawn)&&(!Health||!Health->IsDead())&&
        !AFPSGAMEPlayerController::BlocksOngoingActions(PC)&&(!Build||!Build->IsBuilding());
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
    if(!CanUppercut(Pawn,Profile)||bBluntUppercut||bBluntWhirlwind||bBluntServerCharging||
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

void UProductionToolComponent::StartBluntUppercut(UColdSteelStatusModel* Profile)
{
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;if(!Item)return;
    ColdSteelAuthority::FScope Scope(Profile);
    bBluntUppercut=true;bBluntUppercutReleased=bBluntUppercutLungeStarted=bBluntUppercutLungeBlocked=false;
    BluntUppercutTime=BluntUppercutPause=0.f;BluntUppercutImpactAge=1.f;
    BluntUppercutHits=BluntUppercutKills=0;BluntUppercutHitActors.Reset();
    BluntUppercutDirection=FVector::ZeroVector;BluntUppercutInstance=Item->InstanceId;
    const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
    const auto Effect=Profile->MasteryEffect(TEXT("swordUppercut"));
    BluntUppercutDamage=Stats.Damage*ColdSteelMelee::UppercutMultiplier(Profile,Stats.Modifiers);
    BluntUppercutReach=Stats.ThrustReach*Effect.UppercutReachMultiplier;
    BluntUppercutRange=RuneSwordCombatTuning::RangeMultiplier*Stats.Modifiers.Range*
        Profile->MasteryDefinition(TEXT("swordUppercut")).UppercutRangeMultiplier;
    ApplyToolStats(Item,Profile);
    BluntUppercutShot=ColdSteelSkills::Snapshot(Character.Get(),Item);
    BluntUppercutShot.bMelee=true;BluntUppercutShot.WeakpointPercent=0.f;
    BluntUppercutShot.AttackMeta=SwordUppercut::AttackMeta;
    BluntUppercutShot.DamagePanel=Stats.DamageParts.Scaled(Stats.Damage>0.?BluntUppercutDamage/Stats.Damage:0.);
    BluntUppercutShot.ToughnessDamageMultiplier=float(ToolStats.ToughnessDamage*Stats.Modifiers.HeavyToughness);
    BluntUppercutShot.CriticalChance=FMath::Clamp(BluntUppercutShot.CriticalChance+float(ToolStats.CriticalChanceAdd),0.f,100.f);
    bQueuedBluntAttack=false;bBluntHeavy=bBluntSprintAttack=false;NextBluntStage=0;
    BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;SetTickGroup(TG_PostPhysics);
    BluntServerReadyAt=GetWorld()->GetTimeSeconds()+RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)+HitPause;
    Character->StopMovementForMeleeSkill();
}

float UProductionToolComponent::BluntUppercutPoseTime() const
{return WarhammerUppercutMotion::PoseTime(BluntUppercutTime);}

void UProductionToolComponent::TickBluntUppercut(float Delta)
{
    auto* Pawn=Character.Get();if(!Pawn)return;
    auto* Profile=Pawn->HasAuthority()?ColdSteelAuthority::ForPawn(Pawn):GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!CanUppercut(Pawn,Profile)||!Item||Item->InstanceId!=BluntUppercutInstance)
    {FinishBluntUppercut();return;}
    ColdSteelAuthority::FScope Scope(Profile);
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
            if(Pawn->HasAuthority())
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
            if(auto* Sound=Cast<USoundBase>(WarhammerAudioPaths::Uppercut.ResolveObject()))
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
        if(Pawn->HasAuthority()&&bBluntUppercutReleased&&BluntUppercutHitActors.IsEmpty())
            SweepBluntUppercut(From,To,Before,Pawn->GetMeleeAimTransform());
        if(BluntUppercutPause>0.f)break;
    }
    if(bBluntUppercut&&BluntUppercutTime>=End-UE_SMALL_NUMBER)FinishBluntUppercut();
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
    FRuneSwordTraceSettings Settings;Settings.bCleavePawns=false;Settings.Radius=RuneSwordCombat::BladeRadius*BluntUppercutRange;
    const auto Hits=RuneSwordCombat::Query(GetWorld(),Pawn,Sample(A,Before),Sample(B,After),BluntUppercutReach,BluntUppercutHitActors,Settings);
    for(const auto& Hit:Hits)
    {
        auto* Target=Hit.GetActor();if(!IsValid(Target))continue;
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();if(Combat&&Combat->IsDead())continue;
        FWeaponDamageResult Result;
        const float Applied=ColdSteelSkills::ApplyHit(Pawn,Hit,BluntUppercutDamage,After.GetUnitAxis(EAxis::X),BluntUppercutShot,&Result);
        if(Applied<=0.f&&!(Combat&&Combat->IsDead()))continue;
        BluntUppercutHitActors.Add(Target);
        if(Combat&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))
        {BluntUppercutHits=1;BluntUppercutKills=Combat->IsDead()?1:0;}
        Pawn->NotifyConfirmedWeaponHit(Target,Applied,&Result);
        if(!bBluntUppercut)return;
        BluntUppercutPause=HitPause;BluntUppercutImpactAge=0.f;
        if(!Pawn->IsLocallyControlled())ClientBluntUppercutImpact(BluntAttackId);
        break;
    }
}

void UProductionToolComponent::FinishBluntUppercut()
{
    if(!bBluntUppercut)return;
    const bool Train=bBluntUppercutReleased;
    bBluntUppercut=false;bBluntUppercutReleased=false;BluntUppercutPause=0.f;
    if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->ClearWhirlwindEntry();
    if(Train&&Character.IsValid()&&Character->HasAuthority())
        if(auto* Profile=ColdSteelAuthority::ForPawn(Character.Get()))
        {ColdSteelAuthority::FScope Scope(Profile);Profile->TrainSwordUppercut(BluntUppercutHits,BluntUppercutKills);}
    BluntUppercutHitActors.Reset();BluntServerReadyAt=GetWorld()->GetTimeSeconds();VisualTime=0.f;NextBluntStage=0;
}
