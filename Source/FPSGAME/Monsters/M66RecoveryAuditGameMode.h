#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "M66RecoveryAuditGameMode.generated.h"
class AM66IncineratorMonster;

/** Explicitly selected, command-line-only recovery replication fixture. */
UCLASS()
class FPSGAME_API AM66RecoveryAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UFUNCTION(Server,Reliable) void ServerHello(const FString& Label);
    UFUNCTION(Client,Reliable) void ClientInspectDown(AM66IncineratorMonster* Boss,uint32 Serial,double Started,double Ends,
        const TArray<FName>& Bones,const TArray<FTransform>& Pose,FVector MeshOffset,FTransform MeshWorld);
    UFUNCTION(Server,Reliable) void ServerDownReport(bool Passed,float PositionError,float RotationError);
    void Watch(AM66IncineratorMonster* Boss);
    UFUNCTION(Client,Reliable) void ClientFinish();
    UFUNCTION(Server,Reliable) void ServerFinalReport(bool Passed);
    FString AuditLabel;
    bool DownReported=false,DownPassed=false,FinalReported=false,FinalPassed=false;
private:
    UPROPERTY() TObjectPtr<AM66IncineratorMonster> Held;
    UPROPERTY(Replicated) TObjectPtr<AM66IncineratorMonster> Subject;
    TArray<FName> ExpectedBones;
    TArray<FTransform> ExpectedPose;
    FVector ExpectedOffset=FVector::ZeroVector;
    FTransform ExpectedWorld;
    uint32 ExpectedSerial=0,LastSerial=0,Phases=0;
    double ExpectedStarted=0.,ExpectedEnds=0.,InspectAt=-1.,FinishAt=-1.;
    int32 AirEntries=0,DeathWaitSamples=0;
    float PoseError=0.f,AngleError=0.f,ClockError=0.f,DeathDrift=0.f,DeathAngle=0.f;
    float OffsetError=0.f,WorldError=0.f;
    bool DownSent=false,FinalSent=false,AuthorityPassed=false,ClipPassed=true,HadAir=false;
    TMap<TWeakObjectPtr<AM66IncineratorMonster>,FTransform> HeldDeathPoses;
};

UCLASS()
class FPSGAME_API AM66RecoveryAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AM66RecoveryAuditGameMode();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
private:
    AM66IncineratorMonster* SpawnSubject(const FVector& At);
    UPROPERTY() TObjectPtr<AM66IncineratorMonster> Held;
    UPROPERTY() TObjectPtr<AM66IncineratorMonster> Subject;
    int32 Stage=0;
    double StageAt=0.,GetUpAt=-1.;
    bool Extended=false,Relaunched=false,Done=false,ServerPassed=true;
};
