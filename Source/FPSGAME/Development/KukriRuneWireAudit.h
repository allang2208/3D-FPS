#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "KukriRuneWireAudit.generated.h"
class AFPSGAMECharacter;
class UColdSteelStatusModel;

// Transport fixture: deterministic isolated profiles, production rune components.
// Full inventory upload and combat RPC validation belong to separate audits.
UCLASS()
class AKukriRuneWirePlayerState : public AColdSteelPlayerState
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override {}
};
UCLASS()
class AKukriRuneWireController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override;
    UFUNCTION(Client,Reliable) void ClientCase(int32 Phase,AFPSGAMECharacter* Subject);
    UFUNCTION(Server,Reliable) void ServerResult(int32 Phase,bool ClientPassed,const FString& Details);
    UFUNCTION(Client,Reliable) void ClientFinish();
    int32 Finished=0;
    bool Passed=true;
    TArray<TSharedPtr<class FJsonValue>> Rows;
private:
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> Host;
    int32 Current=INDEX_NONE;
    double Started=0,LastSent=-10,ExitAt=-1;
};
UCLASS()
class AKukriRuneWireGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AKukriRuneWireGameMode();
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Tick(float Delta) override;
private:
    UPROPERTY() TObjectPtr<AKukriRuneWireController> Guest;
    UPROPERTY() TObjectPtr<AFPSGAMECharacter> Host;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> GuestModel;
    int32 Prepared=INDEX_NONE;
    bool Seeded=false;
    double Joined=0,LastSetup=-10,ExitAt=-1;
};
