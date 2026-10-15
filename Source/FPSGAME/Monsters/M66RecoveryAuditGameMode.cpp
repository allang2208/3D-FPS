#include "M66RecoveryAuditGameMode.h"
#include "M66RecoveryAuditScene.h"
#include "M66IncineratorMonster.h"
#include "M66AnimInstance.h"
#include "M66CorpseSyncComponent.h"
#include "MonsterCombatComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "MonsterRagdollPhysics.h"
#include "PhysicsEngine/BodyInstance.h"
#include "MonsterAIController.h"
#include "Animation/AnimSequence.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Engine/DamageEvents.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/SpectatorPawn.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "UObject/UnrealType.h"
#include "Serialization/JsonSerializer.h"
#include "HAL/PlatformMisc.h"
#include "Net/UnrealNetwork.h"

namespace M66RecoveryAudit
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("M66RecoveryAudit"));}
double Clock(UWorld* W){return W->GetGameState()?W->GetGameState()->GetServerWorldTimeSeconds():W->GetTimeSeconds();}
const FM66ReactionState& State(const AM66IncineratorMonster* M)
{
    const auto* Property=FindFProperty<FStructProperty>(AM66IncineratorMonster::StaticClass(),TEXT("Reaction"));
    check(Property);return *Property->ContainerPtrToValuePtr<FM66ReactionState>(M);
}
void Save(const TSharedRef<FJsonObject>& Json)
{
    FString Text;FJsonSerializer::Serialize(Json,TJsonWriterFactory<>::Create(&Text));
    FString Path;if(FParse::Value(FCommandLine::Get(),TEXT("M66RecoveryOutput="),Path))FFileHelper::SaveStringToFile(Text,*Path);
    UE_LOG(LogTemp,Display,TEXT("M66_RECOVERY_RESULT %s"),*Text);
}
}
void AM66RecoveryAuditController::BeginPlay()
{
    Super::BeginPlay();if(!M66RecoveryAudit::Enabled()||!IsLocalController())return;
    M66RecoveryAuditScene::Create(GetWorld());
    FParse::Value(FCommandLine::Get(),TEXT("M66RecoveryRole="),AuditLabel);ServerHello(AuditLabel);
}
void AM66RecoveryAuditController::ServerHello_Implementation(const FString& Label)
{if(M66RecoveryAudit::Enabled()){AuditLabel=Label;UE_LOG(LogTemp,Display,TEXT("M66_RECOVERY_HELLO %s"),*AuditLabel);}}
void AM66RecoveryAuditController::ClientInspectDown_Implementation(AM66IncineratorMonster* Boss,uint32 Serial,double Started,double Ends,
    const TArray<FName>& Bones,const TArray<FTransform>& Pose,FVector MeshOffset,FTransform MeshWorld)
{
    Held=Boss;ExpectedSerial=Serial;ExpectedStarted=Started;ExpectedEnds=Ends;ExpectedBones=Bones;ExpectedPose=Pose;
    ExpectedOffset=MeshOffset;ExpectedWorld=MeshWorld;
    InspectAt=GetWorld()->GetRealTimeSeconds();
}
void AM66RecoveryAuditController::ServerDownReport_Implementation(bool Passed,float PositionError,float RotationError)
{
    if(!M66RecoveryAudit::Enabled())return;DownReported=true;DownPassed=Passed;
    UE_LOG(LogTemp,Display,TEXT("M66_RECOVERY_DOWN role=%s pass=%d position_cm=%.4f angle_deg=%.4f"),*AuditLabel,Passed,PositionError,RotationError);
}
void AM66RecoveryAuditController::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AM66RecoveryAuditController,Subject);}
void AM66RecoveryAuditController::Watch(AM66IncineratorMonster* Boss){Subject=Boss;ForceNetUpdate();}
void AM66RecoveryAuditController::ClientFinish_Implementation(){FinishAt=GetWorld()->GetRealTimeSeconds();}
void AM66RecoveryAuditController::ServerFinalReport_Implementation(bool Passed)
{if(M66RecoveryAudit::Enabled()){FinalReported=true;FinalPassed=Passed;}}
void AM66RecoveryAuditController::Tick(float Dt)
{
    Super::Tick(Dt);if(!M66RecoveryAudit::Enabled()||!IsLocalController())return;
    M66RecoveryAuditScene::Observe(this,Subject?Subject.Get():Held.Get());
    if(AuditLabel==TEXT("host"))return;
    const double Real=GetWorld()->GetRealTimeSeconds();
    if(Held&&!DownSent&&InspectAt>=0.&&Real-InspectAt>.5)
    {
        const auto& State=M66RecoveryAudit::State(Held);float Seconds=0.f;bool Loop=false;
        auto* Clip=Held->ReactionClip(Seconds,Loop);
        bool Pass=State.Phase==EM66Reaction::Down&&State.Serial==ExpectedSerial&&FMath::Abs(State.StartedAt-ExpectedStarted)<.001
            &&FMath::Abs(State.EndsAt-ExpectedEnds)<.001&&Clip==Held->LandClip&&!Loop&&FMath::IsNearlyEqual(Seconds,Clip->GetPlayLength(),.001f);
        PoseError=AngleError=0.f;
        for(int32 I=0;I<ExpectedBones.Num();++I)
        {
            const FTransform Actual=Held->GetMesh()->GetSocketTransform(ExpectedBones[I],RTS_Component);
            PoseError=FMath::Max(PoseError,float(FVector::Dist(Actual.GetLocation(),ExpectedPose[I].GetLocation())));
            AngleError=FMath::Max(AngleError,float(FMath::RadiansToDegrees(Actual.GetRotation().AngularDistance(ExpectedPose[I].GetRotation()))));
        }
        const float Health=Held->Health;const uint32 Serial=Held->ReactionSerial();
        AuthorityPassed=!Held->HasAuthority()&&!Held->StartLaunch(nullptr,FVector(0,0,400),1.f)
            &&!Held->Combat->ReceiveKnockdown(nullptr,FVector(0,0,400),1.f)
            &&Held->TakeDamage(100.f,FDamageEvent(),nullptr,nullptr)==0.f;
        Held->InterruptAttack(100.f);Held->ExtendControl(100.f);
        AuthorityPassed&=Held->Health==Health&&Held->ReactionSerial()==Serial&&M66RecoveryAudit::State(Held).EndsAt==ExpectedEnds;
        OffsetError=float(FVector::Dist(Held->GetBaseTranslationOffset(),ExpectedOffset));
        WorldError=float(FVector::Dist(Held->GetMesh()->GetComponentLocation(),ExpectedWorld.GetLocation()));
        Pass&=AuthorityPassed&&PoseError<.5f&&AngleError<.1f&&OffsetError<.1f&&WorldError<3.f;
        if(Pass||Real-InspectAt>8.){DownSent=true;ServerDownReport(Pass,PoseError,AngleError);}
    }
    if(Subject)
    {
        const auto& State=M66RecoveryAudit::State(Subject);const auto Phase=State.Phase;
        if(Phase==EM66Reaction::Airborne){HadAir=true;if(State.Serial!=LastSerial)++AirEntries;}
        LastSerial=State.Serial;if(HadAir)Phases|=1u<<uint8(Phase);
        float Seconds;bool Loop;auto* Clip=Subject->ReactionClip(Seconds,Loop);
        if(Phase==EM66Reaction::Landing||Phase==EM66Reaction::Down)ClipPassed&=Clip==Subject->LandClip;
        if(Phase==EM66Reaction::GetUp)ClipPassed&=Clip==Subject->GetUpClip;
        if(auto* Anim=Cast<UM66AnimInstance>(Subject->GetMesh()->GetAnimInstance());Anim&&Anim->ReactionVersion==State.Serial&&Phase==EM66Reaction::GetUp)
            ClockError=FMath::Max(ClockError,FMath::Abs(Anim->ReactionTime-Seconds));
    }
    for(AM66IncineratorMonster* M:{Held.Get(),Subject.Get()})
    {
        if(!M||!M->HoldKnockdownDeathPose())continue;
        const auto* Anim=Cast<UM66AnimInstance>(M->GetMesh()->GetAnimInstance());
        if(!Anim||!Anim->bHoldKnockdownDeath)continue;
        ++DeathWaitSamples;ClipPassed&=Anim->Reaction!=M->DeathClip&&!M->GetMesh()->IsSimulatingPhysics();
        const FTransform Pose=M->GetMesh()->GetSocketTransform(TEXT("Bone_000"),RTS_Component);
        if(const FTransform* Previous=HeldDeathPoses.Find(M))
        {
            DeathDrift=FMath::Max(DeathDrift,float(FVector::Dist(Previous->GetLocation(),Pose.GetLocation())));
            DeathAngle=FMath::Max(DeathAngle,float(FMath::RadiansToDegrees(Previous->GetRotation().AngularDistance(Pose.GetRotation()))));
        }
        else HeldDeathPoses.Add(M,Pose);
    }
    if(FinishAt>=0.&&!FinalSent&&Real-FinishAt>1.)
    {
        const uint32 Required=(1u<<uint8(EM66Reaction::Airborne))|(1u<<uint8(EM66Reaction::Landing))|(1u<<uint8(EM66Reaction::Down))
            |(1u<<uint8(EM66Reaction::GetUp))|(1u<<uint8(EM66Reaction::None))|(1u<<uint8(EM66Reaction::Dying));
        const bool Corpse=Held&&Subject&&Held->CorpseSync->State().Frozen&&Subject->CorpseSync->State().Frozen
            &&!Held->GetMesh()->IsSimulatingPhysics()&&!Subject->GetMesh()->IsSimulatingPhysics();
        const int32 HeldDeaths=FParse::Param(FCommandLine::Get(),TEXT("M66AuditStandingDeath"))?1:2;
        const bool Pass=DownSent&&AuthorityPassed&&ClipPassed&&(Phases&Required)==Required&&AirEntries>=3&&ClockError<.15f
            &&DeathWaitSamples>=2&&HeldDeathPoses.Num()==HeldDeaths&&DeathDrift<.5f&&DeathAngle<.1f&&Corpse;
        auto Result=MakeShared<FJsonObject>();Result->SetStringField(TEXT("role"),AuditLabel);Result->SetBoolField(TEXT("result"),Pass);
        Result->SetNumberField(TEXT("phase_mask"),Phases);Result->SetNumberField(TEXT("air_entries"),AirEntries);
        Result->SetBoolField(TEXT("authority_guards"),AuthorityPassed);Result->SetBoolField(TEXT("clips"),ClipPassed);
        Result->SetNumberField(TEXT("down_pose_error_cm"),PoseError);Result->SetNumberField(TEXT("down_angle_error_deg"),AngleError);
        Result->SetNumberField(TEXT("mesh_offset_error_cm"),OffsetError);Result->SetNumberField(TEXT("mesh_world_error_cm"),WorldError);
        Result->SetNumberField(TEXT("animation_clock_error_s"),ClockError);Result->SetNumberField(TEXT("death_wait_samples"),DeathWaitSamples);
        Result->SetNumberField(TEXT("death_pose_drift_cm"),DeathDrift);Result->SetNumberField(TEXT("death_pose_angle_deg"),DeathAngle);
        Result->SetBoolField(TEXT("server_corpse_received"),Corpse);M66RecoveryAudit::Save(Result);FinalSent=true;ServerFinalReport(Pass);
    }
}
AM66RecoveryAuditGameMode::AM66RecoveryAuditGameMode()
{
    PrimaryActorTick.bCanEverTick=true;PlayerControllerClass=AM66RecoveryAuditController::StaticClass();
    DefaultPawnClass=ASpectatorPawn::StaticClass();GameStateClass=AGameStateBase::StaticClass();
}
AM66IncineratorMonster* AM66RecoveryAuditGameMode::SpawnSubject(const FVector& At)
{
    auto* Class=LoadClass<AM66IncineratorMonster>(nullptr,TEXT("/Game/Monsters/IncineratorBossM66/BP_M66RigPreview.BP_M66RigPreview_C"));
    if(!Class)return nullptr;
    const FTransform Transform(FRotator::ZeroRotator,At);
    auto* M=GetWorld()->SpawnActorDeferred<AM66IncineratorMonster>(Class,Transform,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    M->bEnableBackSmoke=false;M->CorpseSeconds=300.f;UGameplayStatics::FinishSpawningActor(M,Transform);
    ServerPassed&=M->LandClip&&M->GetUpClip&&M->LandClip->GetName()==TEXT("A_M66_Landing_V21")&&M->GetUpClip->GetName()==TEXT("A_M66_GetUp_V21");
    if(auto* AI=Cast<AMonsterAIController>(M->GetController()))AI->SetDecisionEnabled(false);
    M->Combat->ToughnessThreshold=0.f; // Fixture-only admission; normal boss poise is unchanged.
    return M;
}
void AM66RecoveryAuditGameMode::BeginPlay()
{
    Super::BeginPlay();if(!M66RecoveryAudit::Enabled())return;
    FString Room;FParse::Value(FCommandLine::Get(),TEXT("M66AuditRoom="),Room);
    M66RecoveryAuditScene::Create(GetWorld());
    if(Room.IsEmpty())
    {
    auto* Floor=GetWorld()->SpawnActor<AActor>();auto* Mesh=NewObject<UStaticMeshComponent>(Floor);Floor->SetRootComponent(Mesh);
    Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Mesh->SetWorldScale3D(FVector(80,80,1));
    Mesh->SetWorldLocation(FVector(0,0,-50));Mesh->SetCollisionProfileName(TEXT("BlockAll"));Mesh->RegisterComponent();
    Floor->SetReplicates(true);Mesh->SetIsReplicated(true);
    }
    Held=SpawnSubject(M66RecoveryAuditScene::SpawnPoint(GetWorld(),true));ServerPassed&=Held!=nullptr;
    UE_LOG(LogTemp,Display,TEXT("M66_RECOVERY_HOST_READY"));
}
void AM66RecoveryAuditGameMode::Tick(float Dt)
{
    Super::Tick(Dt);if(!M66RecoveryAudit::Enabled()||Done||!Held)return;
    AM66RecoveryAuditController* Early=nullptr;AM66RecoveryAuditController* Late=nullptr;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)if(auto* PC=Cast<AM66RecoveryAuditController>(It->Get()))
    {if(PC->AuditLabel==TEXT("early"))Early=PC;if(PC->AuditLabel==TEXT("late"))Late=PC;}
    const double Now=M66RecoveryAudit::Clock(GetWorld());
    auto Advance=[&](int32 Next){Stage=Next;StageAt=Now;UE_LOG(LogTemp,Display,TEXT("M66_RECOVERY_STAGE %d time=%.3f"),Stage,Now);};
    switch(Stage)
    {
    case 0:if(Early){ServerPassed&=Held->Combat->ReceiveKnockdown(nullptr,FVector(80,0,420),900.f);Advance(1);}break;
    case 1:
        if(Held->ReactionPhase()==EM66Reaction::Down){UE_LOG(LogTemp,Display,TEXT("M66_RECOVERY_LATE_READY"));Advance(2);}break;
    case 2:
        if(Late&&Now-StageAt>1.)
        {
            TArray<FName> Bones={TEXT("M66_Root"),TEXT("Bone_000"),TEXT("Bone_006"),TEXT("Bone_010"),TEXT("Bone_015"),TEXT("Bone_037")};
            TArray<FTransform> Pose;for(FName Bone:Bones)Pose.Add(Held->GetMesh()->GetSocketTransform(Bone,RTS_Component));
            const auto& State=M66RecoveryAudit::State(Held);
            Early->ClientInspectDown(Held,State.Serial,State.StartedAt,State.EndsAt,Bones,Pose,Held->GetMesh()->GetRelativeLocation(),Held->GetMesh()->GetComponentTransform());
            Late->ClientInspectDown(Held,State.Serial,State.StartedAt,State.EndsAt,Bones,Pose,Held->GetMesh()->GetRelativeLocation(),Held->GetMesh()->GetComponentTransform());Advance(3);
        }break;
    case 3:
        if(Early&&Late&&Early->DownReported&&Late->DownReported)
        {
            ServerPassed&=Early->DownPassed&&Late->DownPassed;Subject=SpawnSubject(M66RecoveryAuditScene::SpawnPoint(GetWorld(),false));
            if(!Subject){ServerPassed=false;break;}
            for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
                if(auto* PC=Cast<AM66RecoveryAuditController>(It->Get()))PC->Watch(Subject);
            Advance(4);
        }break;
    case 4:if(Now-StageAt>2.){ServerPassed&=Subject->Combat->ReceiveKnockdown(nullptr,FVector(90,0,420),3.f);Advance(5);}break;
    case 5:
        if(Subject->ReactionPhase()==EM66Reaction::Down&&!Extended)
        {Extended=true;Subject->Combat->ReceiveStun(nullptr,2.f,0.f);}
        if(Subject->ReactionPhase()==EM66Reaction::GetUp)
        {
            if(GetUpAt<0)GetUpAt=Now;
            if(!Relaunched&&Now-GetUpAt>.7)
            {Relaunched=true;ServerPassed&=Subject->Combat->ReceiveKnockdown(nullptr,FVector(-60,0,400),2.8f);}
        }
        if(Relaunched&&Subject->ReactionPhase()==EM66Reaction::None){ServerPassed&=!Subject->Busy()&&!Subject->Combat->IsControlled();Advance(6);}
        break;
    case 6:if(Now-StageAt>1.){ServerPassed&=Subject->Combat->ReceiveKnockdown(nullptr,FVector(0,0,400),2.5f);GetUpAt=-1.;Advance(7);}break;
    case 7:
        if(Subject->ReactionPhase()==(FParse::Param(FCommandLine::Get(),TEXT("M66AuditStandingDeath"))?EM66Reaction::None:EM66Reaction::GetUp))
        {
            if(GetUpAt<0)GetUpAt=Now;
            if(Now-GetUpAt>.7)
            {
                for(auto* M:{Held.Get(),Subject.Get()})
                {
                    UGameplayStatics::ApplyDamage(M,1000000.f,nullptr,nullptr,UDamageType::StaticClass());
                    M->CorpseSync->SetComponentTickEnabled(false); // Force a .6 s reaction-before-corpse delivery gap.
                    ServerPassed&=M->Dead();
                }
                Advance(8);
            }
        }break;
    case 8:if(Now-StageAt>.6){Held->CorpseSync->Wake();Subject->CorpseSync->Wake();Advance(9);}break;
    case 9:
        if(FMath::FloorToInt(Now-StageAt)!=FMath::FloorToInt(Now-StageAt-Dt))
            for(auto* M:{Held.Get(),Subject.Get()})M66RecoveryAuditScene::CorpseDetails(M);
        if(Now-StageAt>5.&&FMath::FloorToInt((Now-StageAt)/5.)!=FMath::FloorToInt((Now-StageAt-Dt)/5.))
        {
            for(auto* M:{Held.Get(),Subject.Get()})
            {
                FHitResult Support;const bool Grounded=MonsterRagdollPhysics::FindSupport(M->GetMesh(),Support);
                float Linear=0.f,Angular=0.f,MinZ=MAX_flt;
                for(const auto* Body:M->GetMesh()->Bodies)if(Body&&Body->IsInstanceSimulatingPhysics())
                {Linear=FMath::Max(Linear,float(Body->GetUnrealWorldVelocity().Size()));Angular=FMath::Max(Angular,float(Body->GetUnrealWorldAngularVelocityInRadians().Size()));MinZ=FMath::Min(MinZ,float(Body->GetBodyBounds().Min.Z));}
                UE_LOG(LogTemp,Display,TEXT("M66_RECOVERY_CORPSE %s sim=%d frozen=%d support=%d settled=%d linear=%.3f angular=%.3f min_z=%.3f packet=%u sync_tick=%d body_tick=%d mesh_tick=%d"),
                    *M->GetName(),M->CorpseRagdoll->SimulatedBodyCount(),M->CorpseRagdoll->IsFrozen(),Grounded,MonsterRagdollPhysics::IsSettled(M->GetMesh(),10.f,.3f),
                    Linear,Angular,MinZ,M->CorpseSync->State().Revision,M->CorpseSync->IsComponentTickEnabled(),M->CorpseRagdoll->IsComponentTickEnabled(),M->GetMesh()->IsComponentTickEnabled());
            }
        }
        if(Held->CorpseSync->State().Frozen&&Subject->CorpseSync->State().Frozen)
        {Early->ClientFinish();Late->ClientFinish();Advance(10);}
        else if(Now-StageAt>30.)
        {ServerPassed=false;Early->ClientFinish();Late->ClientFinish();Advance(10);}
        break;
    case 10:
        if(Early->FinalReported&&Late->FinalReported)
        {
            auto Result=MakeShared<FJsonObject>();Result->SetBoolField(TEXT("result"),ServerPassed&&Early->FinalPassed&&Late->FinalPassed);
            Result->SetBoolField(TEXT("server_flow"),ServerPassed);Result->SetBoolField(TEXT("early"),Early->FinalPassed);Result->SetBoolField(TEXT("late"),Late->FinalPassed);
            Result->SetStringField(TEXT("transport"),TEXT("listen server plus online and late-joining socket clients"));
            M66RecoveryAudit::Save(Result);Done=true;FPlatformMisc::RequestExit(false);
        }break;
    }
}
