#include "ProductionToolComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Weapons/RuneSwordWhirlwindFeel.h"
#include "../Weapons/RuneSwordHitQuery.h"
#include "../Weapons/RuneSwordMeshComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace
{
bool CanWhirlwind(AFPSGAMECharacter* Pawn,UColdSteelStatusModel* Profile)
{
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    const auto* PS=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
    const auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
    return Pawn&&Item&&ColdSteelInventory::IsTwoHandedBlunt(*Item)&&PC&&
        (!Sword||!Sword->IsGuarding())&&(!PS||!PS->IsQuickCombatExecuting(Pawn))&&
        !Pawn->IsTraversing()&&!Pawn->IsDodging()&&!Pawn->IsSliding()&&!Pawn->IsCastBlockingLeftHandAction()&&
        !UBoundCongregateCaptureComponent::IsCaptured(Pawn)&&(!Health||!Health->IsDead())&&
        !AFPSGAMEPlayerController::BlocksOngoingActions(PC)&&(!Build||!Build->IsBuilding());
}
const FSoftObjectPath Whoosh(TEXT("/Game/Weapons/SteelWarhammer20261014/NormalSwingAudioV1/S_Warhammer_NormalSwing.S_Warhammer_NormalSwing"));
}

bool UProductionToolComponent::BeginWhirlwind()
{
    auto* Pawn=Character.Get();
    auto* Profile=Pawn&&Pawn->HasAuthority()?ColdSteelAuthority::ForPawn(Pawn):
        GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!CanWhirlwind(Pawn,Profile)||IsBusy()||!IsEquipped()||!CanUse()||!HasReadyPresentation()||
        !Motions.FindRef(TEXT("Whirlwind"))||Profile->MasteryProgress(TEXT("whirlwind")).Level<1||
        Profile->WhirlwindCooldown()>0.f||!Profile->CanSpendStamina(Profile->WhirlwindStats().StaminaCost))return false;
    ColdSteelAuthority::FScope Scope(Profile);
    if(Pawn->HasAuthority()&&!Profile->CommitWhirlwindCast(Profile->WhirlwindStats()))return false;
    ++BluntAttackId;BluntServerAttackId=BluntAttackId;
    StartBluntWhirlwind(Profile);
    if(!Pawn->HasAuthority())ServerBeginBluntWhirlwind(BluntAttackId);
    return true;
}

void UProductionToolComponent::ServerBeginBluntWhirlwind_Implementation(uint32 AttackId)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    if(!CanWhirlwind(Pawn,Profile)||bBluntUppercut||bBluntWhirlwind||bBluntServerCharging||GetWorld()->GetTimeSeconds()<BluntServerReadyAt)
    {ClientBluntWhirlwindResult(AttackId,false);return;}
    ColdSteelAuthority::FScope Scope(Profile);
    const float StaminaBefore=Profile->Stamina();
    if(!Profile->CommitWhirlwindCast(Profile->WhirlwindStats())){ClientBluntWhirlwindResult(AttackId,false);return;}
    SendBluntMartialReceipt(Profile,AttackId,FMath::Max(0.f,StaminaBefore-Profile->Stamina()));
    Character=Pawn;BluntAttackId=BluntServerAttackId=AttackId;
    StartBluntWhirlwind(Profile);ClientBluntWhirlwindResult(AttackId,true);
}

void UProductionToolComponent::ClientBluntWhirlwindResult_Implementation(uint32 AttackId,bool Accepted)
{
    if(AttackId==BluntAttackId&&!Accepted)FinishBluntWhirlwind();
}

void UProductionToolComponent::ClientBluntWhirlwindImpact_Implementation(uint32 AttackId,float Pause,float Strength)
{
    if(!bBluntWhirlwind||AttackId!=BluntAttackId)return;
    BluntWhirlwindPause=FMath::Max(BluntWhirlwindPause,Pause);
    BluntWhirlwindImpactAge=0.f;BluntWhirlwindImpactStrength=Strength;
}

void UProductionToolComponent::StartBluntWhirlwind(UColdSteelStatusModel* Profile)
{
    const auto* Item=Profile->ActiveProductionTool();
    bBluntWhirlwind=true;bBluntWhirlwindTrained=false;
    BluntWhirlwindTime=BluntWhirlwindPause=BluntWhirlwindPauseSpent=0.f;
    BluntWhirlwindImpactAge=1.f;BluntWhirlwindImpactStrength=1.f;
    BluntWhirlwindHitCount=BluntWhirlwindKillCount=0;BluntWhirlwindHitActors.Reset();
    BluntWhirlwindInstance=Item->InstanceId;BluntWhirlwindYaw=Character->GetControlRotation().Yaw;
    BluntWhirlwindCast=Profile->WhirlwindStats();BluntWhirlwindTuning=Profile->MasteryDefinition(TEXT("whirlwind")).Whirlwind;
    ApplyToolStats(Item,Profile);
    SetTickGroup(TG_PostPhysics);
    BluntWhirlwindShot=ColdSteelSkills::Snapshot(Character.Get(),Item);BluntWhirlwindShot.bMelee=true;
    BluntWhirlwindShot.AttackMeta|=0x20;BluntWhirlwindShot.WeakpointPercent=0.f;
    const double Total=ToolStats.Damage.Total();
    BluntWhirlwindShot.DamagePanel=ToolStats.Damage.Scaled(Total>0.?BluntWhirlwindCast.Damage/Total:0.);
    BluntWhirlwindShot.ToughnessDamageMultiplier=float(ToolStats.ToughnessDamage);
    BluntWhirlwindShot.CriticalChance=FMath::Clamp(BluntWhirlwindShot.CriticalChance+float(ToolStats.CriticalChanceAdd),0.f,100.f);
    bQueuedBluntAttack=false;bBluntHeavy=bBluntSprintAttack=false;NextBluntStage=0;
    BluntSprintSeconds=0.f;BluntSprintReadyAt=-100.;
    const auto& T=BluntWhirlwindTuning;
    BluntServerReadyAt=GetWorld()->GetTimeSeconds()+T.ReadySeconds+T.SpinSeconds+T.RecoverSeconds+T.HitStopBudget;
    Character->StopMovementForMeleeSkill();
    if(Character->IsLocallyControlled())BeginBluntWhirlwindFocus();
}

float UProductionToolComponent::BluntWhirlwindPoseTime() const
{
    const auto& T=BluntWhirlwindTuning;
    const float Time=BluntWhirlwindTime;
    if(Time<T.ReadySeconds)return .5f*Time/FMath::Max(.001f,T.ReadySeconds);
    if(Time<T.ReadySeconds+T.SpinSeconds)return .5f+.8f*(Time-T.ReadySeconds)/FMath::Max(.001f,T.SpinSeconds);
    return 1.3f+.52f*FMath::Clamp((Time-T.ReadySeconds-T.SpinSeconds)/FMath::Max(.001f,T.RecoverSeconds),0.f,1.f);
}

void UProductionToolComponent::TickBluntWhirlwind(float Delta)
{
    auto* Pawn=Character.Get();if(!Pawn)return;
    auto* Profile=Pawn->HasAuthority()?ColdSteelAuthority::ForPawn(Pawn):GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!CanWhirlwind(Pawn,Profile)||!Item||Item->InstanceId!=BluntWhirlwindInstance)
    {FinishBluntWhirlwind();return;}
    const auto& T=BluntWhirlwindTuning;
    const float Pause=FMath::Min(Delta,BluntWhirlwindPause);BluntWhirlwindPause-=Pause;Delta-=Pause;
    if(Delta<=0.f)
    {
        if(Pawn->IsLocallyControlled()&&Viewmodel)Viewmodel->ClearMotionVector();
        return;
    }
    BluntWhirlwindImpactAge+=Delta;
    const float End=T.ReadySeconds+T.SpinSeconds+T.RecoverSeconds;
    float Remaining=FMath::Min(Delta,End-BluntWhirlwindTime);
    while(Remaining>UE_SMALL_NUMBER&&bBluntWhirlwind)
    {
        const float Step=FMath::Min(Remaining,1.f/120.f),Before=BluntWhirlwindTime;
        BluntWhirlwindTime+=Step;Remaining-=Step;
        const float A=WhirlwindFeel::Phase(Before,T),B=WhirlwindFeel::Phase(BluntWhirlwindTime,T);
        FRotator Aim=Pawn->GetControlRotation();Aim.Yaw=BluntWhirlwindYaw+T.TurnDegrees*B;
        Pawn->GetController()->SetControlRotation(Aim);
        if(Pawn->IsLocallyControlled())
            if(auto* Sound=Cast<USoundBase>(Whoosh.ResolveObject()))
                if((A<.035f&&B>=.035f)||(A<.535f&&B>=.535f))UGameplayStatics::PlaySound2D(this,Sound,.7f,B<.5f?.9f:1.05f);
        if(Pawn->HasAuthority()&&B>A)SweepBluntWhirlwind(T.TurnDegrees*A,T.TurnDegrees*B);
        if(BluntWhirlwindPause>0.f)break;
    }
    if(!bBluntWhirlwind)return;
    Pawn->FaceRotation(Pawn->GetControlRotation(),0.f);
    if(BluntWhirlwindTime>=T.ReadySeconds+T.SpinSeconds)TrainBluntWhirlwind();
    if(BluntWhirlwindTime>=End-UE_SMALL_NUMBER)FinishBluntWhirlwind();
}

void UProductionToolComponent::SweepBluntWhirlwind(float From,float To)
{
    auto* Pawn=Character.Get();auto* Profile=ColdSteelAuthority::ForPawn(Pawn);ColdSteelAuthority::FScope Scope(Profile);
    const FVector Origin=Pawn->GetMeleeAimTransform().GetLocation()-FVector(0,0,45.f);
    auto Sample=[&](float Degrees)
    {
        FRuneSwordBladeSample S;S.Origin=Origin;S.Forward=FRotator(0,BluntWhirlwindYaw+90.f+Degrees,0).Vector();
        S.Base=Origin+S.Forward*15.f;S.Tip=Origin+S.Forward*BluntWhirlwindCast.RadiusCM;return S;
    };
    FRuneSwordTraceSettings Settings;Settings.Radius=32.f;Settings.bCleavePawns=true;Settings.bAreaDamage=true;
    const auto Hits=RuneSwordCombat::Query(GetWorld(),Pawn,Sample(From),Sample(To),BluntWhirlwindCast.RadiusCM,BluntWhirlwindHitActors,Settings);
    int32 Confirmed=0;
    for(const auto& Hit:Hits)
    {
        auto* Target=Hit.GetActor();auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!IsValid(Target)||BluntWhirlwindHitActors.Contains(Target)||(Combat&&Combat->IsDead()))continue;
        BluntWhirlwindHitActors.Add(Target);
        const FVector Direction=(Target->GetActorLocation()-Pawn->GetActorLocation()).GetSafeNormal2D();
        FWeaponDamageResult Result;
        const float Applied=ColdSteelSkills::ApplyHit(Pawn,Hit,BluntWhirlwindCast.Damage,Direction,BluntWhirlwindShot,&Result);
        const bool Killed=Combat&&Combat->IsDead();if(Applied<=0.f&&!Killed)continue;
        ++Confirmed;
        if(Combat&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))
        {++BluntWhirlwindHitCount;if(Killed)++BluntWhirlwindKillCount;}
        if(Combat&&!Killed)Combat->ReceiveStun(Pawn,BluntWhirlwindCast.StunSeconds,BluntWhirlwindCast.KnockbackCM);
        Pawn->NotifyConfirmedWeaponHit(Target,Applied,&Result);
    }
    if(Confirmed)
    {
        const float Pause=FMath::Max(0.f,FMath::Min(BluntWhirlwindTuning.HitStopSeconds,BluntWhirlwindTuning.HitStopBudget-BluntWhirlwindPauseSpent));
        BluntWhirlwindPause=Pause;BluntWhirlwindPauseSpent+=Pause;
        BluntWhirlwindImpactAge=0.f;BluntWhirlwindImpactStrength=1.f+.12f*FMath::Min(Confirmed-1,3);
        if(!Pawn->IsLocallyControlled())ClientBluntWhirlwindImpact(BluntAttackId,Pause,BluntWhirlwindImpactStrength);
    }
}

void UProductionToolComponent::TrainBluntWhirlwind()
{
    if(bBluntWhirlwindTrained)return;bBluntWhirlwindTrained=true;
    if(auto* Pawn=Character.Get();Pawn&&Pawn->HasAuthority())
        if(auto* Profile=ColdSteelAuthority::ForPawn(Pawn))
        {ColdSteelAuthority::FScope Scope(Profile);Profile->TrainWhirlwind(BluntWhirlwindHitCount,BluntWhirlwindKillCount);}
}

void UProductionToolComponent::FinishBluntWhirlwind()
{
    if(!bBluntWhirlwind)return;
    bBluntWhirlwind=false;BluntWhirlwindPause=0.f;
    EndBluntWhirlwindFocus();
    if(auto* Arms=Cast<URuneSwordMeshComponent>(Viewmodel))Arms->ClearWhirlwindEntry();
    TrainBluntWhirlwind();BluntWhirlwindHitActors.Reset();BluntServerReadyAt=GetWorld()->GetTimeSeconds();
    VisualTime=0.f;NextBluntStage=0;
}
