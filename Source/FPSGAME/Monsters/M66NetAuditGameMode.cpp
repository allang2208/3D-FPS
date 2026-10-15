#include "M66NetAuditGameMode.h"
#include "M66IncineratorMonster.h"
#include "M66BackMist.h"
#include "M66AudioComponent.h"
#include "M66CorpseSyncComponent.h"
#include "MonsterAIController.h"
#include "MonsterCorpseRagdollComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/SpectatorPawn.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/PlatformMisc.h"
#include "Sound/SoundBase.h"

namespace M66Audit
{
bool Enabled(){return FParse::Param(FCommandLine::Get(),TEXT("M66NetAudit"));}
double Clock(UWorld* World){const auto* State=World->GetGameState();return State?State->GetServerWorldTimeSeconds():World->GetTimeSeconds();}
void Save(const FString& Text)
{
    FString Path;if(FParse::Value(FCommandLine::Get(),TEXT("M66AuditOutput="),Path))FFileHelper::SaveStringToFile(Text,*Path);
    UE_LOG(LogTemp,Display,TEXT("M66_NET_AUDIT %s"),*Text);
}
}
void AM66NetAuditController::BeginPlay()
{
    Super::BeginPlay();if(!M66Audit::Enabled())return;
    if(IsLocalController())
    {
        FParse::Value(FCommandLine::Get(),TEXT("M66AuditLabel="),AuditLabel);
        ServerHello(AuditLabel);
    }
}
void AM66NetAuditController::ServerHello_Implementation(const FString& Label)
{if(M66Audit::Enabled()){AuditLabel=Label;UE_LOG(LogTemp,Display,TEXT("M66_NET_HELLO role=%s time=%.3f"),*Label,GetWorld()->GetTimeSeconds());}}
void AM66NetAuditController::ClientInspect_Implementation(AM66IncineratorMonster* InBoss,AM66BackMist* InMist,uint32 PuffSerial,FVector PuffOrigin,double PuffBorn,
    FVector Eye,uint32 CorpseRevision,FTransform MeshWorld,const TArray<FTransform>& Pose,uint32 AudioSerial)
{
    Subject=InBoss;Cloud=InMist;ExpectedPuff=PuffSerial;ExpectedOrigin=PuffOrigin;ExpectedBorn=PuffBorn;ExposureEye=Eye;
    ExpectedRevision=CorpseRevision;ExpectedWorld=MeshWorld;ExpectedPose=Pose;ExpectedAudio=AudioSerial;RequestedAt=GetWorld()->GetRealTimeSeconds();Requested=true;
}
void AM66NetAuditController::Tick(float Dt)
{
    Super::Tick(Dt);if(!M66Audit::Enabled()||!IsLocalController())return;
    if(JoinedAt<0&&GetWorld()->GetGameState())JoinedAt=M66Audit::Clock(GetWorld());
    if(!Subject)for(TActorIterator<AM66IncineratorMonster> It(GetWorld());It;++It){Subject=*It;break;}
    if(Subject)
    {
        const auto& State=Subject->CorpseSync->State();
        if(State.Revision!=SeenRevision){if(!State.Frozen)++MovingUpdates;SeenRevision=State.Revision;}
    }
    if(FinishedAt>=0)
    {
        return;
    }
    if(!Requested||!Subject||!Cloud)return;
    bool Smoke=false,Old=false;
    for(const auto& Puff:Cloud->SmokeHistory())if(Puff.Serial==ExpectedPuff)
    {
        Smoke=FVector::Dist(Puff.Origins[0],ExpectedOrigin)<.2&&FMath::Abs(Puff.Born-ExpectedBorn)<.001;
        Old=AuditLabel!=TEXT("late")||Puff.Born<JoinedAt-1.;break;
    }
    Smoke&=Cloud->ContainsExposedEye(ExposureEye,GetPawn());
    const auto& Packet=Subject->CorpseSync->State();
    float PositionError=0.f,AngleError=0.f;FPoseSnapshot Actual;Subject->GetMesh()->SnapshotPose(Actual);
    bool Corpse=Packet.Frozen&&Packet.Revision>=ExpectedRevision&&Actual.bIsValid&&Actual.LocalTransforms.Num()==ExpectedPose.Num()
        &&!Subject->GetMesh()->IsSimulatingPhysics();
    if(Corpse)
    {
        PositionError=FVector::Dist(Subject->GetMesh()->GetComponentLocation(),ExpectedWorld.GetLocation());
        for(int32 I=0;I<ExpectedPose.Num();++I)
        {
            PositionError=FMath::Max(PositionError,float(FVector::Dist(Actual.LocalTransforms[I].GetLocation(),ExpectedPose[I].GetLocation())*100.));
            AngleError=FMath::Max(AngleError,float(FMath::RadiansToDegrees(Actual.LocalTransforms[I].GetRotation().AngularDistance(ExpectedPose[I].GetRotation()))));
        }
        Corpse=PositionError<.5f&&AngleError<.1f;
    }
    bool Audio=Subject->BodyAudio->ConsumedSerial()>=ExpectedAudio&&Subject->BodySounds.Num()==10;
    for(const auto& Pair:Subject->BodySounds)Audio&=Pair.Value&&Pair.Value->GetDuration()>0.f;
    Audio&=Subject->BodyAudio->ResolvedEvents()>0;
    if(AuditLabel==TEXT("late"))Audio&=Subject->BodyAudio->ResolvedEvents()==1; // Only the new probe, not old attacks/death.
    const bool Motion=AuditLabel!=TEXT("early")||MovingUpdates>=2;
    if((Smoke&&Old&&Corpse&&Audio&&Motion)||GetWorld()->GetRealTimeSeconds()-RequestedAt>15.)
    {
        const FString Text=FString::Printf(TEXT("{\"role\":\"%s\",\"smoke\":%s,\"old_history\":%s,\"corpse\":%s,\"audio_events\":%s,\"resolved_audio_events\":%d,\"moving_packets\":%d,\"position_error_cm\":%.6f,\"angle_error_deg\":%.6f,\"result\":%s}"),
            *AuditLabel,Smoke?TEXT("true"):TEXT("false"),Old?TEXT("true"):TEXT("false"),Corpse?TEXT("true"):TEXT("false"),Audio?TEXT("true"):TEXT("false"),Subject->BodyAudio->ResolvedEvents(),MovingUpdates,PositionError,AngleError,
            Smoke&&Old&&Corpse&&Audio&&Motion?TEXT("true"):TEXT("false"));
        if(AuditLabel!=TEXT("host"))M66Audit::Save(Text);
        ServerReport(Smoke,Corpse,Audio,Old,MovingUpdates,PositionError,AngleError);FinishedAt=GetWorld()->GetRealTimeSeconds();
    }
}
void AM66NetAuditController::ServerReport_Implementation(bool Smoke,bool Corpse,bool Audio,bool OldHistory,int32 Updates,float PositionError,float AngleError)
{
    if(!M66Audit::Enabled())return;
    Reported=true;Passed=Smoke&&Corpse&&Audio&&OldHistory&&(AuditLabel!=TEXT("early")||Updates>=2)&&PositionError<.5f&&AngleError<.1f;
    UE_LOG(LogTemp,Display,TEXT("M66_NET_CLIENT_REPORT role=%s pass=%d moving=%d error_cm=%.6f error_deg=%.6f"),*AuditLabel,Passed,Updates,PositionError,AngleError);
}
AM66NetAuditGameMode::AM66NetAuditGameMode()
{
    PrimaryActorTick.bCanEverTick=true;PlayerControllerClass=AM66NetAuditController::StaticClass();
    DefaultPawnClass=ASpectatorPawn::StaticClass();GameStateClass=AGameStateBase::StaticClass();
}
void AM66NetAuditGameMode::BeginPlay()
{
    Super::BeginPlay();if(!M66Audit::Enabled())return;
    auto* Floor=GetWorld()->SpawnActor<AActor>();auto* Mesh=NewObject<UStaticMeshComponent>(Floor);Floor->SetRootComponent(Mesh);
    Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Mesh->SetWorldScale3D(FVector(80,80,1));Mesh->SetWorldLocation(FVector(0,0,-50));Mesh->SetCollisionProfileName(TEXT("BlockAll"));Mesh->RegisterComponent();
    auto* Class=LoadClass<AM66IncineratorMonster>(nullptr,TEXT("/Game/Monsters/IncineratorBossM66/BP_M66RigPreview.BP_M66RigPreview_C"));
    if(!Class){M66Audit::Save(TEXT("{\"result\":false,\"error\":\"M66 blueprint missing\"}"));FPlatformMisc::RequestExit(false);return;}
    const FTransform Transform(FRotator::ZeroRotator,FVector(0,0,195));
    Boss=GetWorld()->SpawnActorDeferred<AM66IncineratorMonster>(Class,Transform,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    Boss->CorpseSeconds=360.f;Boss->BackSmokeHoldSeconds=300.f; // Fixture-only retention through two editor-client cold startups.
    UGameplayStatics::FinishSpawningActor(Boss,Transform);
    if(auto* AI=Cast<AMonsterAIController>(Boss->GetController()))AI->SetDecisionEnabled(false);
    UE_LOG(LogTemp,Display,TEXT("M66_NET_HOST_READY"));
}
void AM66NetAuditGameMode::Tick(float Dt)
{
    Super::Tick(Dt);if(!M66Audit::Enabled()||!Boss||Done)return;
    AM66NetAuditController* Early=nullptr;AM66NetAuditController* Late=nullptr;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)if(auto* PC=Cast<AM66NetAuditController>(It->Get()))
    {if(PC->AuditLabel==TEXT("early"))Early=PC;if(PC->AuditLabel==TEXT("late"))Late=PC;}
    const double Now=GetWorld()->GetTimeSeconds();
    if(Early&&Started<0)Started=Now;
    if(Started<0)return;
    const FName Cues[]={TEXT("SweepSwing"),TEXT("SweepImpact"),TEXT("SlamImpact"),TEXT("FootLeft"),TEXT("FootRight"),TEXT("Hurt"),TEXT("Land"),TEXT("Recover")};
    if(NextCue<UE_ARRAY_COUNT(Cues)&&Now-Started>=2.+NextCue*.4)
    {Boss->BodyAudio->Emit(Cues[NextCue++],Boss->GetActorLocation());}
    if(!Killed&&Now-Started>6.){Killed=true;UGameplayStatics::ApplyDamage(Boss,1000000.f,nullptr,nullptr,UDamageType::StaticClass());}
    if(Boss->CorpseSync->State().Frozen)
    {
        if(!LateAnnounced){LateAnnounced=true;UE_LOG(LogTemp,Display,TEXT("M66_NET_LATE_READY"));}
        if(Late&&LateJoined<0)LateJoined=Now;
        if(Late&&!LateProbe&&Now-LateJoined>2.){LateProbe=true;Boss->BodyAudio->Emit(TEXT("Land"),Boss->GetMesh()->GetComponentLocation());}
        AM66BackMist* Mist=nullptr;for(TActorIterator<AM66BackMist> It(GetWorld());It;++It){Mist=*It;break;}
        const auto& Packet=Boss->CorpseSync->State();
        if(Mist&&!Mist->SmokeHistory().IsEmpty())
        {
            const FM66SmokePuff* Puff=nullptr;for(const auto& P:Mist->SmokeHistory())if(P.Serial&&(!Puff||P.Serial<Puff->Serial))Puff=&P;
            if(Puff)
            {
                const float Age=float(M66Audit::Clock(GetWorld())-Puff->Born);
                FVector Eye=FVector(Puff->Origins[0])+FVector(Puff->Drift)*(2.2f*(1-FMath::Exp(-Age/2.2f)));
                Eye.Z=FMath::Max(Puff->Floors[0]+55.f,float(Puff->Origins[0].Z)-38.f*(Age-.5f*(1-FMath::Exp(-Age*2.f))));
                for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)if(auto* PC=Cast<AM66NetAuditController>(It->Get());PC&&!PC->Requested)
                    if(PC->AuditLabel==TEXT("early")||(PC->AuditLabel==TEXT("late")&&LateProbe&&Now-LateJoined>2.5))
                    {PC->Requested=true;PC->ClientInspect(Boss,Mist,Puff->Serial,Puff->Origins[0],Puff->Born,Eye,Packet.Revision,Packet.MeshWorld,Packet.LocalPose,Boss->BodyAudio->EmittedSerial());}
            }
        }
    }
    if(Early&&Late&&Early->Reported&&Late->Reported)
    {Done=true;M66Audit::Save(FString::Printf(TEXT("{\"result\":%s,\"early\":%s,\"late\":%s,\"transport\":\"real listen server plus two clients\"}"),Early->Passed&&Late->Passed?TEXT("true"):TEXT("false"),Early->Passed?TEXT("true"):TEXT("false"),Late->Passed?TEXT("true"):TEXT("false")));FPlatformMisc::RequestExit(false);}
}
