#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "HeQueKickStunAudit.generated.h"
class AHeQueMonster;
class AFPSGAMECharacter;

UCLASS()
class AHeQueKickStunProbe : public AActor
{
    GENERATED_BODY()
public:
    AHeQueKickStunProbe();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(Replicated) int32 CaseId=0;
    UPROPERTY(Replicated) bool ExpectStun=true;
    UPROPERTY(Replicated) TObjectPtr<AFPSGAMECharacter> Target;
    UPROPERTY(Replicated) FVector Start=FVector::ZeroVector;
    UPROPERTY(Replicated) double FiredAt=0.;
    UPROPERTY(Replicated) double CollisionAt=0.;
    UPROPERTY(Replicated) double ControlEndsAt=0.;
    UPROPERTY(Replicated) bool Respawned=false;
};

/** Readouts from the real owner/observer processes, including attempted input. */
USTRUCT()
struct FHeQueKickStunReport
{
    GENERATED_BODY()
    UPROPERTY() int32 CaseId=0;
    UPROPERTY() bool Owner=false;
    UPROPERTY() bool Pass=false;
    UPROPERTY() bool SawStun=false;
    UPROPERTY() bool SawLock=false;
    UPROPERTY() bool SawStatusCard=false;
    UPROPERTY() bool LockCorrect=true;
    UPROPERTY() bool InputRestored=false;
    UPROPERTY() bool Jumped=false;
    UPROPERTY() bool EdgeStateCorrect=true;
    UPROPERTY() bool SawEdge=false;
    UPROPERTY() float StunSeconds=0.f;
    UPROPERTY() float LockSeconds=0.f;
    UPROPERTY() float ExpiryError=0.f;
    UPROPERTY() float BlockedMove=0.f;
    UPROPERTY() float BlockedYaw=0.f;
    UPROPERTY() float ResumedMove=0.f;
    UPROPERTY() float ResumedYaw=0.f;
    UPROPERTY() float PushX=0.f;
};

UCLASS()
class AHeQueKickStunController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void PlayerTick(float Dt) override;
    UFUNCTION(Server,Reliable) void ServerHello(const FString& InRole);
    UFUNCTION(Server,Reliable) void ServerReady(int32 CaseId);
    UFUNCTION(Server,Reliable) void ServerResult(const FHeQueKickStunReport& Report);
    FString AuditRole;
    int32 ReadyCase=0;
    FHeQueKickStunReport Result;
private:
    void SampleCase(float Dt);
    void SampleEdgeCase(const AHeQueKickStunProbe* Probe);
    int32 LocalCase=0,SentCase=0;
    FHeQueKickStunReport Sample;
    double StunOn=-1.,StunOff=-1.,LockOn=-1.,LockOff=-1.,ResumeAt=-1.;
    FVector BlockedAt=FVector::ZeroVector,ResumeFrom=FVector::ZeroVector;
    float BlockedFromYaw=0.f,ResumeFromYaw=0.f;
    bool CapturedBlock=false,CapturedPush=false,RequestedJump=false;
    bool MenuLock=false,MenuReleased=false;
};

/** Opt-in empty-map fixture with real HeQue kick, health and player movement. */
UCLASS()
class AHeQueKickStunGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AHeQueKickStunGameMode();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
private:
    void BeginCase(int32 Id,AHeQueKickStunController* Host,AHeQueKickStunController* Guest);
    void Finish(bool Pass,const FString& Reason);
    void TickEdgeCase(double Now,AHeQueKickStunController* Host,AHeQueKickStunController* Guest);
    UPROPERTY() TObjectPtr<AHeQueKickStunProbe> Probe;
    UPROPERTY() TObjectPtr<AHeQueMonster> Boss;
    double BeganAt=0.,CaseAt=0.,AuthorityStunOn=-1.,AuthorityStunOff=-1.;
    float BeforeHealth=0.f,ObservedDamage=0.f;
    bool Done=false;
    int32 EdgeStage=0;
};
