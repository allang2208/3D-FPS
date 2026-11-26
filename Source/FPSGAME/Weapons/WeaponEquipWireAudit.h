#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "WeaponEquipWireAudit.generated.h"

UCLASS()
class AWeaponEquipWireFloor : public AActor
{
    GENERATED_BODY()
public:
    AWeaponEquipWireFloor();
};

// Explicit local UDP review. Uses production PlayerState upload/mirror ticks.
UCLASS()
class AWeaponEquipWireController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void Tick(float DeltaSeconds) override;
    UFUNCTION(Server,Reliable) void ServerCaseReport(int32 Case,const FString& Expected,const FString& Json);
    UFUNCTION(Client,Reliable) void ClientCaseAck(int32 Case,bool Accepted);
    UFUNCTION(Client,Reliable) void ClientFinish();
    UFUNCTION(Server,Reliable) void ServerWristBegin(int32 Case,const FString& Expected);
    void TickM249Wrist(float DeltaSeconds);
    void TickM249WristVisual();
    void TickM249Parts();
    TArray<TSharedPtr<class FJsonValue>> Results;
    bool bFinished=false,bPassed=true;
private:
    int32 CaseIndex=0,Stage=0,SwitchCount=0;
    double StageAt=-1.,NextSwitch=0.,ExitAt=-1.;
    FString ExpectedInstance;
    bool bCasePassed=true,bWaiting=false;
    double JumpFOV=0,JumpAngle=0,JumpPosition=0;
    int32 UnexpectedEquipment=0;
    int32 PendingCase=-1;
    double PendingAt=0.;
    FString PendingExpected,PendingJson;
    bool bWristSawAim=false,bWristSawReload=false,bWristFinite=true;
    int32 WristSamples=0,WristBadEquipment=0;
    double WristBoundary=0.;
    FVector WristPrevious=FVector::ZeroVector;
    bool bWristWasReloading=false,bWristSaveRestored=false;
};

UCLASS()
class AWeaponEquipWireGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AWeaponEquipWireGameMode();
    virtual void BeginPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Tick(float DeltaSeconds) override;
private:
    double Started=0.,ExitAt=-1.;
};
