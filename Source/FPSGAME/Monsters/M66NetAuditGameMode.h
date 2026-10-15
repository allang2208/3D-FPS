#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "M66NetAuditGameMode.generated.h"
class AM66IncineratorMonster;
class AM66BackMist;

/** Opt-in, empty-map, real socket replication fixture. Never selected by normal maps. */
UCLASS()
class FPSGAME_API AM66NetAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    UFUNCTION(Server,Reliable) void ServerHello(const FString& Label);
    UFUNCTION(Client,Reliable) void ClientInspect(AM66IncineratorMonster* Boss,AM66BackMist* Mist,uint32 PuffSerial,FVector PuffOrigin,double PuffBorn,
        FVector Eye,uint32 CorpseRevision,FTransform MeshWorld,const TArray<FTransform>& Pose,uint32 AudioSerial);
    UFUNCTION(Server,Reliable) void ServerReport(bool Smoke,bool Corpse,bool Audio,bool OldHistory,int32 Updates,float PositionError,float AngleError);
    FString AuditLabel;
    bool Reported=false,Passed=false,Requested=false;
private:
    UPROPERTY() TObjectPtr<AM66IncineratorMonster> Subject;
    UPROPERTY() TObjectPtr<AM66BackMist> Cloud;
    TArray<FTransform> ExpectedPose;
    FTransform ExpectedWorld;
    FVector ExpectedOrigin,ExposureEye;
    uint32 ExpectedPuff=0,ExpectedRevision=0,ExpectedAudio=0,SeenRevision=0;
    double ExpectedBorn=0.,JoinedAt=-1.,RequestedAt=0.,FinishedAt=-1.;
    int32 MovingUpdates=0;
};
UCLASS()
class FPSGAME_API AM66NetAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AM66NetAuditGameMode();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
private:
    UPROPERTY() TObjectPtr<AM66IncineratorMonster> Boss;
    double Started=-1.,LateJoined=-1.;
    int32 NextCue=0;
    bool Killed=false,LateProbe=false,Done=false,LateAnnounced=false;
};
