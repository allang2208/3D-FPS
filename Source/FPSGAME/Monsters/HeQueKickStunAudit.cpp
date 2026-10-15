#include "HeQueKickStunAudit.h"
#include "HeQueMonster.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "HandBrainFearComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Movement/PlayerGuardBreakComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../UI/StatusEffectsComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "BrainComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameStateBase.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Net/UnrealNetwork.h"
#include "UObject/UnrealType.h"

namespace HeQueKickAudit
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("HeQueKickStunAudit"));}
double Clock(const UWorld* World)
{const auto* GS=World->GetGameState();return GS?GS->GetServerWorldTimeSeconds():World->GetTimeSeconds();}
bool Stunned(const AFPSGAMECharacter* Target)
{const auto* Status=Target?Target->FindComponentByClass<UCombatStatusFormula>():nullptr;return Status&&Status->IsStunned();}
}

AHeQueKickStunProbe::AHeQueKickStunProbe()
{
    bReplicates=true;bAlwaysRelevant=true;SetNetUpdateFrequency(60.f);
    auto* Floor=CreateDefaultSubobject<UBoxComponent>(TEXT("AuditFloor"));RootComponent=Floor;
    Floor->InitBoxExtent(FVector(6000,6000,50));Floor->SetCollisionProfileName(TEXT("BlockAll"));
    auto* Wall=CreateDefaultSubobject<UBoxComponent>(TEXT("AuditObstacle"));Wall->SetupAttachment(Floor);
    Wall->SetRelativeLocation(FVector(700,1500,300));Wall->InitBoxExtent(FVector(25,600,300));
    Wall->SetCollisionProfileName(TEXT("BlockAll"));Wall->SetCanEverAffectNavigation(false);
}
void AHeQueKickStunProbe::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AHeQueKickStunProbe,CaseId);DOREPLIFETIME(AHeQueKickStunProbe,ExpectStun);
    DOREPLIFETIME(AHeQueKickStunProbe,Target);DOREPLIFETIME(AHeQueKickStunProbe,Start);
    DOREPLIFETIME(AHeQueKickStunProbe,FiredAt);DOREPLIFETIME(AHeQueKickStunProbe,CollisionAt);
}
void AHeQueKickStunController::BeginPlay()
{
    Super::BeginPlay();if(!HeQueKickAudit::Enabled()||!IsLocalController())return;
    FParse::Value(FCommandLine::Get(),TEXT("HeQueKickAuditRole="),AuditRole);ServerHello(AuditRole);
}
void AHeQueKickStunController::ServerHello_Implementation(const FString& InRole)
{if(HeQueKickAudit::Enabled()){AuditRole=InRole;UE_LOG(LogTemp,Display,TEXT("HEQUE_KICK_HELLO %s"),*AuditRole);}}
void AHeQueKickStunController::ServerReady_Implementation(int32 CaseId)
{if(HeQueKickAudit::Enabled())ReadyCase=CaseId;}
void AHeQueKickStunController::ServerResult_Implementation(const FHeQueKickStunReport& Report)
{
    if(!HeQueKickAudit::Enabled())return;Result=Report;
    UE_LOG(LogTemp,Display,TEXT("HEQUE_KICK_REPORT role=%s case=%d owner=%d pass=%d stun=%d lock=%d card=%d lock_correct=%d restored=%d jump=%d stun_s=%.4f lock_s=%.4f expiry_error=%.4f blocked_cm=%.3f blocked_yaw=%.3f resumed_cm=%.3f resumed_yaw=%.3f push_x=%.3f"),
        *AuditRole,Report.CaseId,Report.Owner,Report.Pass,Report.SawStun,Report.SawLock,Report.SawStatusCard,Report.LockCorrect,Report.InputRestored,Report.Jumped,
        Report.StunSeconds,Report.LockSeconds,Report.ExpiryError,Report.BlockedMove,Report.BlockedYaw,Report.ResumedMove,Report.ResumedYaw,Report.PushX);
    if(Report.CaseId>=4)UE_LOG(LogTemp,Display,TEXT("HEQUE_KICK_EDGE role=%s case=%d correct=%d observed=%d"),*AuditRole,Report.CaseId,Report.EdgeStateCorrect,Report.SawEdge);
}
void AHeQueKickStunController::PlayerTick(float Dt)
{
    // Feed normal input before PlayerTick consumes RotationInput. Actor Tick
    // happens afterwards and its axis input is immediately cleared by UE.
    SampleCase(Dt);Super::PlayerTick(Dt);
}
void AHeQueKickStunController::SampleCase(float Dt)
{
    if(!HeQueKickAudit::Enabled()||!IsLocalController())return;
    for(TActorIterator<AHeQueKickStunProbe> It(GetWorld());It;++It)
    {
        const auto* P=*It;if(P->CaseId<=0||!IsValid(P->Target))return;
        if(LocalCase!=P->CaseId)
        {
            LocalCase=P->CaseId;Sample={};Sample.CaseId=LocalCase;
            StunOn=StunOff=LockOn=LockOff=ResumeAt=-1.;CapturedBlock=CapturedPush=RequestedJump=false;
            MenuLock=MenuReleased=false;
        }
        if(SentCase==LocalCase)return;
        auto* Target=P->Target.Get();Sample.Owner=GetPawn()==Target;
        if(P->FiredAt<=0.)
        {
            if(ReadyCase!=LocalCase&&FVector::Dist(Target->GetActorLocation(),P->Start)<6.f
                &&(!Sample.Owner||(!IsMoveInputIgnored()&&!IsLookInputIgnored()&&Target->InputEnabled())))
            {ReadyCase=LocalCase;ServerReady(LocalCase);}
            return;
        }
        if(LocalCase>=4){SampleEdgeCase(P);return;}
        const double Now=HeQueKickAudit::Clock(GetWorld()),Age=Now-P->FiredAt;
        const bool Stun=HeQueKickAudit::Stunned(Target);
        const auto* Display=Target->FindComponentByClass<UStatusEffectsComponent>();
        const bool Card=Display&&Display->Snapshot().ContainsByPredicate([](const FStatusEffectView& View){return View.Type==TEXT("stun");});
        Sample.SawStatusCard|=Card;
        const auto* Guard=Target->FindComponentByClass<UPlayerGuardBreakComponent>();
        const bool Locked=Sample.Owner&&Guard&&Guard->IsActive();
        if(Stun){Sample.SawStun=true;if(StunOn<0.)StunOn=Now;}
        else if(StunOn>=0.&&StunOff<0.)StunOff=Now;
        if(Locked){Sample.SawLock=true;if(LockOn<0.)LockOn=Now;}
        else if(LockOn>=0.&&LockOff<0.)LockOff=Now;
        if(!CapturedPush&&Age>2.3)
        {CapturedPush=true;Sample.PushX=float(Target->GetActorLocation().X-P->Start.X);}
        if(Sample.Owner&&Locked)
        {
            Sample.LockCorrect&=IsMoveInputIgnored()&&IsLookInputIgnored()&&!Target->InputEnabled();
            // Exclude the correction immediately following the actual collision.
            if(P->CollisionAt>0.&&Now-P->CollisionAt>.3)
            {
                if(!CapturedBlock){CapturedBlock=true;BlockedAt=Target->GetActorLocation();BlockedFromYaw=GetControlRotation().Yaw;}
                Sample.BlockedMove=FMath::Max(Sample.BlockedMove,float(FVector::Dist2D(BlockedAt,Target->GetActorLocation())));
                Sample.BlockedYaw=FMath::Max(Sample.BlockedYaw,FMath::Abs(FMath::FindDeltaAngleDegrees(BlockedFromYaw,GetControlRotation().Yaw)));
                Target->AddMovementInput(FVector::RightVector);Target->AddControllerYawInput(5.f);
            }
        }
        const bool RecoverNow=P->ExpectStun?(P->CollisionAt>0.&&Now-P->CollisionAt>2.25):Age>2.5;
        if(Sample.Owner&&RecoverNow&&!Stun&&!Locked)
        {
            Sample.InputRestored=!IsMoveInputIgnored()&&!IsLookInputIgnored()&&Target->InputEnabled();
            if(ResumeAt<0.){ResumeAt=Now;ResumeFrom=Target->GetActorLocation();ResumeFromYaw=GetControlRotation().Yaw;}
            Target->AddMovementInput(FVector::RightVector);Target->AddControllerYawInput(5.f);
            Sample.ResumedMove=FMath::Max(Sample.ResumedMove,float(FVector::Dist2D(ResumeFrom,Target->GetActorLocation())));
            Sample.ResumedYaw=FMath::Max(Sample.ResumedYaw,FMath::Abs(FMath::FindDeltaAngleDegrees(ResumeFromYaw,GetControlRotation().Yaw)));
            if(!RequestedJump&&Now-ResumeAt>.4){RequestedJump=true;Target->Jump();}
            if(RequestedJump)Sample.Jumped|=Target->GetVelocity().Z>50.f||Target->GetActorLocation().Z-ResumeFrom.Z>30.f;
        }
        if(Age<6.5)return;
        Sample.StunSeconds=StunOn>=0.&&StunOff>=0.?float(StunOff-StunOn):-1.f;
        Sample.LockSeconds=LockOn>=0.&&LockOff>=0.?float(LockOff-LockOn):-1.f;
        Sample.ExpiryError=StunOff>=0.&&P->CollisionAt>0.?float(StunOff-P->CollisionAt-2.):-1.f;
        Sample.Pass=CapturedPush&&!Stun&&!Locked&&!Card;
        if(P->ExpectStun)
        {
            Sample.Pass&=Sample.SawStun&&Sample.SawStatusCard&&Sample.StunSeconds>1.7f&&Sample.StunSeconds<2.25f&&FMath::Abs(Sample.ExpiryError)<.25f
                &&Sample.PushX>200.f&&Sample.PushX<420.f;
            if(Sample.Owner)Sample.Pass&=Sample.SawLock&&Sample.LockCorrect&&CapturedBlock&&Sample.LockSeconds>1.7f&&Sample.LockSeconds<2.25f
                &&Sample.BlockedMove<3.f&&Sample.BlockedYaw<.1f;
        }
        else Sample.Pass&=!Sample.SawStun&&!Sample.SawLock&&!Sample.SawStatusCard&&FMath::Abs(Sample.PushX-1000.f)<3.f;
        if(Sample.Owner)Sample.Pass&=Sample.InputRestored&&Sample.ResumedMove>30.f&&Sample.ResumedYaw>5.f&&Sample.Jumped;
        SentCase=LocalCase;ServerResult(Sample);return;
    }
}

void AHeQueKickStunController::SampleEdgeCase(const AHeQueKickStunProbe* P)
{
    auto* Target=P->Target.Get();
    const double Now=HeQueKickAudit::Clock(GetWorld()),Age=Now-P->FiredAt;
    const double ContactAge=P->CollisionAt>0.?Now-P->CollisionAt:-1.;
    const bool Stun=HeQueKickAudit::Stunned(Target);
    const auto* Guard=Target->FindComponentByClass<UPlayerGuardBreakComponent>();
    const bool Locked=Sample.Owner&&Guard&&Guard->IsActive();
    const auto* Display=Target->FindComponentByClass<UStatusEffectsComponent>();
    const bool Card=Display&&Display->Snapshot().ContainsByPredicate([](const FStatusEffectView& V){return V.Type==TEXT("stun");});
    const bool Dead=Target->FindComponentByClass<UFPSCombatHealthComponent>()->IsDead();
    Sample.SawStun|=Stun;Sample.SawLock|=Locked;Sample.SawStatusCard|=Card;
    if(Locked)Sample.LockCorrect&=IsMoveInputIgnored()&&IsLookInputIgnored()&&!Target->InputEnabled();
    // Reproduce the same counted locks used by the game menu, without a UI/RHI.
    if(LocalCase==7&&Sample.Owner&&ContactAge>.3&&!MenuLock&&!MenuReleased)
    {SetIgnoreMoveInput(true);SetIgnoreLookInput(true);MenuLock=true;}
    if(LocalCase==7&&Sample.Owner&&ContactAge>2.25&&ContactAge<2.6)
    {Sample.SawEdge=true;Sample.EdgeStateCorrect&=!Stun&&!Locked&&IsMoveInputIgnored()&&IsLookInputIgnored();}
    if(MenuLock&&ContactAge>=2.6)
    {SetIgnoreMoveInput(false);SetIgnoreLookInput(false);MenuLock=false;MenuReleased=true;}
    if((LocalCase==4||LocalCase==5)&&P->ControlEndsAt>0.&&Now>P->ControlEndsAt+.25&&ContactAge<1.7)
    {
        const auto* Fear=Target->FindComponentByClass<UHandBrainFearComponent>();
        Sample.SawEdge=true;Sample.EdgeStateCorrect&=!Stun&&!Card&&(!Fear||Fear->Stacks==0)
            &&(!Sample.Owner||(!Locked&&!IsMoveInputIgnored()&&!IsLookInputIgnored()&&Target->InputEnabled()));
    }
    if(LocalCase==6&&ContactAge>.8&&ContactAge<1.2)
    {Sample.SawEdge=true;Sample.EdgeStateCorrect&=Stun&&(!Sample.Owner||Locked);}
    if(LocalCase==6&&ContactAge>2.3&&ContactAge<3.)
    {Sample.SawEdge=true;Sample.EdgeStateCorrect&=Stun&&(!Sample.Owner||Locked);}
    if((LocalCase==8||LocalCase==9)&&Dead)
    {Sample.SawEdge=true;if(Sample.Owner)Sample.EdgeStateCorrect&=!Target->InputEnabled()&&Target->GetCharacterMovement()->MovementMode==MOVE_None;}
    if(LocalCase==10&&ContactAge>2.3&&ContactAge<3.)
    {
        const auto* Fear=Target->FindComponentByClass<UHandBrainFearComponent>();Sample.SawEdge=true;
        Sample.EdgeStateCorrect&=!Stun&&Fear&&Fear->Stacks>0;
        if(Sample.Owner)Sample.EdgeStateCorrect&=!Locked&&IsMoveInputIgnored()&&!IsLookInputIgnored();
    }
    const double RecoverAfter=LocalCase==7?P->CollisionAt+2.8:LocalCase==10?P->CollisionAt+3.6:P->ControlEndsAt+.3;
    const bool CanRecover=P->ControlEndsAt>0.&&Now>RecoverAfter&&!Dead&&((LocalCase!=8&&LocalCase!=9)||P->Respawned);
    if(Sample.Owner&&CanRecover)
    {
        Sample.InputRestored=!Stun&&!Locked&&!IsMoveInputIgnored()&&!IsLookInputIgnored()&&Target->InputEnabled();
        Sample.EdgeStateCorrect&=Sample.InputRestored;
        if(ResumeAt<0.){ResumeAt=Now;ResumeFrom=Target->GetActorLocation();ResumeFromYaw=GetControlRotation().Yaw;}
        Target->AddMovementInput(FVector::RightVector);Target->AddControllerYawInput(5.f);
        Sample.ResumedMove=FMath::Max(Sample.ResumedMove,float(FVector::Dist2D(ResumeFrom,Target->GetActorLocation())));
        Sample.ResumedYaw=FMath::Max(Sample.ResumedYaw,FMath::Abs(FMath::FindDeltaAngleDegrees(ResumeFromYaw,GetControlRotation().Yaw)));
        if(!RequestedJump&&Now-ResumeAt>.4){RequestedJump=true;Target->Jump();}
        if(RequestedJump)Sample.Jumped|=Target->GetVelocity().Z>50.f||Target->GetActorLocation().Z-ResumeFrom.Z>30.f;
    }
    if(Age<8.5)return;
    Sample.Pass=Sample.SawStun&&Sample.SawStatusCard&&Sample.EdgeStateCorrect&&!Stun&&!Locked&&!Card;
    if(LocalCase!=7||Sample.Owner)Sample.Pass&=Sample.SawEdge;
    if(LocalCase==8||LocalCase==9)Sample.Pass&=P->Respawned;
    if(Sample.Owner)Sample.Pass&=Sample.SawLock&&Sample.LockCorrect&&Sample.InputRestored&&Sample.ResumedMove>30.f&&Sample.ResumedYaw>5.f&&Sample.Jumped;
    SentCase=LocalCase;ServerResult(Sample);
}

AHeQueKickStunGameMode::AHeQueKickStunGameMode()
{
    PrimaryActorTick.bCanEverTick=true;PlayerControllerClass=AHeQueKickStunController::StaticClass();
    DefaultPawnClass=AFPSGAMECharacter::StaticClass();GameStateClass=AGameStateBase::StaticClass();
}
void AHeQueKickStunGameMode::BeginPlay()
{
    Super::BeginPlay();if(!HeQueKickAudit::Enabled())return;
    BeganAt=GetWorld()->GetRealTimeSeconds();
    Probe=GetWorld()->SpawnActor<AHeQueKickStunProbe>(FVector(0,0,-50),FRotator::ZeroRotator);
    UE_LOG(LogTemp,Display,TEXT("HEQUE_KICK_HOST_READY"));
}
void AHeQueKickStunGameMode::BeginCase(int32 Id,AHeQueKickStunController* Host,AHeQueKickStunController* Guest)
{
    if(Boss)Boss->Destroy();
    const bool HostVictim=Id==1||Id==4||Id==9;
    auto* Victim=Cast<AFPSGAMECharacter>((HostVictim?Host:Guest)->GetPawn());
    auto* Other=Cast<AFPSGAMECharacter>((HostVictim?Guest:Host)->GetPawn());
    if(!Victim||!Other){Finish(false,TEXT("missing test players"));return;}
    const float Lane=Id==3?-1500.f:1500.f;
    Probe->CaseId=Id;Probe->ExpectStun=Id!=3;Probe->Target=Victim;Probe->FiredAt=Probe->CollisionAt=Probe->ControlEndsAt=0.;
    Probe->Respawned=false;EdgeStage=0;
    Probe->Start=FVector(310,Lane,Victim->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.15f);
    Other->SetActorLocation(FVector(-1500,-3500,100),false,nullptr,ETeleportType::TeleportPhysics);Other->ForceNetUpdate();
    Victim->StopJumping();Victim->GetCharacterMovement()->StopMovementImmediately();
    Victim->SetActorLocation(Probe->Start,false,nullptr,ETeleportType::TeleportPhysics);Victim->ForceNetUpdate();
    UClass* BossClass=LoadClass<AHeQueMonster>(nullptr,TEXT("/Game/Monsters/HeQue/BP_HeQue.BP_HeQue_C"));
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Boss=BossClass?GetWorld()->SpawnActor<AHeQueMonster>(BossClass,FVector(0,Lane,228),FRotator::ZeroRotator,Spawn):nullptr;
    if(!Boss){Finish(false,TEXT("boss spawn failed"));return;}
    // One actual kick per case. The authored motion and contacts are unchanged;
    // a small fixture-only damage value keeps repeated cases non-lethal.
    Boss->SweepDamage=5.f;
    if(auto* AI=Cast<AMonsterAIController>(Boss->GetController()))
    {AI->StopMovement();if(AI->GetBrainComponent())AI->GetBrainComponent()->StopLogic(TEXT("Manual kick audit"));AI->SetActorTickEnabled(false);}
    BeforeHealth=Victim->FindComponentByClass<UFPSCombatHealthComponent>()->Health;
    ObservedDamage=0.f;
    CaseAt=GetWorld()->GetRealTimeSeconds();AuthorityStunOn=AuthorityStunOff=-1.;Probe->ForceNetUpdate();
    UE_LOG(LogTemp,Display,TEXT("HEQUE_KICK_CASE case=%d target=%s wall=%d start=%s"),Id,HostVictim?TEXT("host"):TEXT("guest"),Probe->ExpectStun,*Probe->Start.ToCompactString());
}
void AHeQueKickStunGameMode::Finish(bool Pass,const FString& Reason)
{
    if(Done)return;Done=true;
    const FString Json=FString::Printf(TEXT("{\"passed\":%s,\"reason\":\"%s\",\"scope\":\"real HeQue kick; listen host and client; obstacle stun and owner input recovery\"}"),Pass?TEXT("true"):TEXT("false"),*Reason);
    FString Path;if(FParse::Value(FCommandLine::Get(),TEXT("HeQueKickAuditOutput="),Path))FFileHelper::SaveStringToFile(Json,*Path);
    UE_LOG(LogTemp,Display,TEXT("HEQUE_KICK_RESULT %s"),*Json);FPlatformMisc::RequestExit(false);
}
void AHeQueKickStunGameMode::Tick(float Dt)
{
    Super::Tick(Dt);if(!HeQueKickAudit::Enabled()||Done||!Probe)return;
    AHeQueKickStunController* Host=nullptr;AHeQueKickStunController* Guest=nullptr;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PC=Cast<AHeQueKickStunController>(It->Get()))
        {if(PC->AuditRole==TEXT("host"))Host=PC;else if(PC->AuditRole==TEXT("guest"))Guest=PC;}
    const double RealNow=GetWorld()->GetRealTimeSeconds();
    if(RealNow-BeganAt>240.){Finish(false,TEXT("peer timeout"));return;}
    if(!Host||!Guest||!Host->GetPawn()||!Guest->GetPawn())return;
    if(Probe->CaseId==0){BeginCase(FParse::Param(FCommandLine::Get(),TEXT("HeQueKickEdgesOnly"))?4:1,Host,Guest);return;}
    if(RealNow-CaseAt>35.){Finish(false,TEXT("case timeout"));return;}
    const double Now=HeQueKickAudit::Clock(GetWorld());
    // Respawn destroys the old pawn/components. Switch the probe before any
    // further health/status sampling of that actor.
    if((Probe->CaseId==8||Probe->CaseId==9)&&EdgeStage==2)
    {
        auto* NewPawn=Cast<AFPSGAMECharacter>((Probe->CaseId==9?Host:Guest)->GetPawn());
        if(NewPawn&&NewPawn!=Probe->Target)
        {Probe->Target=NewPawn;Probe->Respawned=true;Probe->ControlEndsAt=Now;EdgeStage=3;}
    }
    if(Probe->FiredAt<=0.)
    {
        if(Host->ReadyCase!=Probe->CaseId||Guest->ReadyCase!=Probe->CaseId||RealNow-CaseAt<1.)return;
        const bool Started=Boss->StartAttack(Probe->Target);
        if(!Started||!Boss->IsSweeping()){Finish(false,TEXT("actual kick did not start"));return;}
        Probe->FiredAt=Now;Probe->ForceNetUpdate();return;
    }
    if(!Probe->Respawned)ObservedDamage=FMath::Max(ObservedDamage,BeforeHealth-Probe->Target->FindComponentByClass<UFPSCombatHealthComponent>()->Health);
    const bool Stun=HeQueKickAudit::Stunned(Probe->Target);
    if(Stun&&AuthorityStunOn<0.)
    {
        AuthorityStunOn=Now;
        const auto* Guard=Probe->Target->FindComponentByClass<UPlayerGuardBreakComponent>();
        const auto* Until=FindFProperty<FDoubleProperty>(UPlayerGuardBreakComponent::StaticClass(),TEXT("StunUntil"));
        Probe->CollisionAt=Guard&&Until?Until->GetPropertyValue_InContainer(Guard)-2.:Now;Probe->ForceNetUpdate();
        Probe->ControlEndsAt=Probe->CollisionAt+2.;
    }
    if(!Stun&&AuthorityStunOn>=0.&&AuthorityStunOff<0.)AuthorityStunOff=Now;
    if(Probe->CaseId>=4){TickEdgeCase(Now,Host,Guest);return;}
    if(Host->Result.CaseId!=Probe->CaseId||Guest->Result.CaseId!=Probe->CaseId)return;
    const float Duration=AuthorityStunOff>=0.?float(AuthorityStunOff-AuthorityStunOn):-1.f;
    const bool AuthorityPass=ObservedDamage>0.f&&(Probe->ExpectStun?(Duration>1.85f&&Duration<2.15f):AuthorityStunOn<0.);
    UE_LOG(LogTemp,Display,TEXT("HEQUE_KICK_AUTHORITY case=%d pass=%d damage=%.3f stun_s=%.4f"),Probe->CaseId,AuthorityPass,ObservedDamage,Duration);
    if(!AuthorityPass||!Host->Result.Pass||!Guest->Result.Pass){Finish(false,TEXT("collision stun or recovery assertion failed"));return;}
    if(Probe->CaseId==3&&!FParse::Param(FCommandLine::Get(),TEXT("HeQueKickEdges"))){Finish(true,TEXT("host wall, guest wall and guest open path passed"));return;}
    BeginCase(Probe->CaseId+1,Host,Guest);
}

void AHeQueKickStunGameMode::TickEdgeCase(double Now,AHeQueKickStunController* Host,AHeQueKickStunController* Guest)
{
    if(Probe->CollisionAt<=0.)return;
    const int32 Id=Probe->CaseId;
    const double Age=Now-Probe->CollisionAt;
    auto* Status=UCombatStatusFormula::GetOrAdd(Probe->Target);
    if((Id==4||Id==5)&&EdgeStage==0&&Age>.2)
    {
        auto* Fear=Probe->Target->FindComponentByClass<UHandBrainFearComponent>();
        if(!Fear){Fear=NewObject<UHandBrainFearComponent>(Probe->Target);Probe->Target->AddInstanceComponent(Fear);Fear->RegisterComponent();}
        Fear->Apply(Boss);EdgeStage=1;
    }
    if((Id==4||Id==5)&&EdgeStage==1&&Age>.5)
    {Status->PurgeTransient();Probe->ControlEndsAt=Now;EdgeStage=2;}
    if(Id==6&&EdgeStage==0&&Age>.5){Status->AddStun(.25f);EdgeStage=1;}
    if(Id==6&&EdgeStage==1&&Age>1.25){Status->AddStun(2.f);Probe->ControlEndsAt=Now+2.;EdgeStage=2;}
    if((Id==8||Id==9)&&EdgeStage==0&&Age>.3)
    {Status->AddStun(5.f);Probe->ControlEndsAt=Now+5.;EdgeStage=1;}
    if((Id==8||Id==9)&&EdgeStage==1&&Age>.6)
    {Probe->Target->FindComponentByClass<UFPSCombatHealthComponent>()->ApplySurvivalDamage(10000.f);EdgeStage=2;}
    if(Id==10&&EdgeStage==0&&Age>.3)
    {
        auto* Fear=Probe->Target->FindComponentByClass<UHandBrainFearComponent>();
        if(!Fear){Fear=NewObject<UHandBrainFearComponent>(Probe->Target);Probe->Target->AddInstanceComponent(Fear);Fear->RegisterComponent();}
        Fear->Apply(Boss);EdgeStage=1;
    }
    Probe->ForceNetUpdate();
    if(Host->Result.CaseId!=Id||Guest->Result.CaseId!=Id)return;
    const auto* Guard=Probe->Target->FindComponentByClass<UPlayerGuardBreakComponent>();
    const bool AuthorityPass=ObservedDamage>0.f&&!HeQueKickAudit::Stunned(Probe->Target)&&(!Guard||!Guard->IsActive())
        &&((Id!=8&&Id!=9)||Probe->Respawned);
    UE_LOG(LogTemp,Display,TEXT("HEQUE_KICK_EDGE_AUTHORITY case=%d pass=%d damage=%.3f stage=%d respawned=%d"),Id,AuthorityPass,ObservedDamage,EdgeStage,Probe->Respawned);
    if(!AuthorityPass||!Host->Result.Pass||!Guest->Result.Pass){Finish(false,TEXT("control edge assertion failed"));return;}
    if(Id==10){Finish(true,TEXT("kick stun purge, overlap, menu lock, fear and respawn passed"));return;}
    BeginCase(Id+1,Host,Guest);
}
