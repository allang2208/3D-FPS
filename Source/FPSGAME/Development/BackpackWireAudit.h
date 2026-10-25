#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "BackpackWireAudit.generated.h"
class AFPSGAMECharacter;

/** Isolated, explicit-command-line fixture using normal inventory upload/replication. */
UCLASS()
class ABackpackWireAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override;
    UFUNCTION(Client,Reliable) void ClientCase(int32 Phase,AFPSGAMECharacter* Subject);
    UFUNCTION(Server,Reliable) void ServerResult(int32 Phase,bool Passed,const FString& Details);
    UFUNCTION(Client,Reliable) void ClientFinish(bool Passed);
    UFUNCTION(Client,Reliable) void ClientObserveCase(int32 Phase,AFPSGAMECharacter* HostPawn,AFPSGAMECharacter* GuestPawn);
    UFUNCTION(Server,Reliable) void ServerObservation(int32 Phase,bool Passed,const FString& Details);
    int32 Finished=0;
    bool AllPassed=true;
    bool IsObserver=false,TransientSafe=true;
    int32 ObservedPhase=INDEX_NONE;
    bool ObservationPassed=false;
    FString ObservationDetails;
    TArray<TSharedPtr<class FJsonValue>> Results;
private:
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> Host;
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> ObservedGuest;
    int32 Current=INDEX_NONE;
    bool ReconnectRestored=true;
    double Started=0,LastSent=-10,ExitAt=-1;
    bool MovesOK=true;
};

UCLASS()
class ABackpackWireAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    ABackpackWireAuditGameMode();
    virtual void PostLogin(APlayerController* Player) override;
    virtual FString InitNewPlayer(APlayerController* Player,const FUniqueNetIdRepl& Id,const FString& Options,const FString& Portal) override;
    virtual void Tick(float Delta) override;
    bool ObserverReady(int32 Phase,bool& Passed,FString& Details) const;
private:
    UPROPERTY() TObjectPtr<ABackpackWireAuditController> Guest;
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> Host;
    UPROPERTY() TObjectPtr<ABackpackWireAuditController> Observer;
    int32 Prepared=INDEX_NONE,Connections=0;
    double LastSetup=-10,Joined=0,ExitAt=-1;
    bool HostSeeded=false,Passed=true;
    TArray<TSharedPtr<class FJsonValue>> History;
};
