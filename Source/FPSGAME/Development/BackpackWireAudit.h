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
    int32 Finished=0;
    bool AllPassed=true;
    TArray<TSharedPtr<class FJsonValue>> Results;
private:
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> Host;
    int32 Current=INDEX_NONE;
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
    virtual void Tick(float Delta) override;
private:
    UPROPERTY() TObjectPtr<ABackpackWireAuditController> Guest;
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> Host;
    int32 Prepared=INDEX_NONE,Connections=0;
    double LastSetup=-10,Joined=0,ExitAt=-1;
    bool HostSeeded=false,Passed=true;
    TArray<TSharedPtr<class FJsonValue>> History;
};
