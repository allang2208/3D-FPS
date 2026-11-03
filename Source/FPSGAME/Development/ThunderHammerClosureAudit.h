#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "ThunderHammerClosureAudit.generated.h"
class AFPSGAMECharacter;

UCLASS()
class AThunderHammerClosureController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override;
    UFUNCTION(Server,Reliable) void ServerHello(bool Observer);
    UFUNCTION(Client,Reliable) void ClientPhase(int32 Phase);
    UFUNCTION(Server,Reliable) void ServerDone(int32 Phase,bool OK,const FString& Message);
    UFUNCTION(Client,Reliable) void ClientExit();
    UFUNCTION(Server,Reliable) void ServerObserved(bool Ground,bool Seat);
    bool Hello=false,IsObserver=false,Done=false,ClientOK=false,ObservedGround=false,ObservedSeat=false;
    FString Detail;
private:
    int32 Current=-1,InputCount=0;
    bool Seeded=false,Sent=false,Pressed=false,Released=false,SawCharge=false,SawOrdinarySwing=false,InstallAttempted=false;
    TWeakObjectPtr<AFPSGAMECharacter> Attached;
    double Started=0.,InputAt=0.,ExitAt=-1.;
    double InstalledAt=-1.;
};

UCLASS()
class AThunderHammerClosureGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AThunderHammerClosureGameMode();
    virtual void BeginPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Logout(AController* Player) override;
    virtual void Tick(float Delta) override;
private:
    UPROPERTY() TArray<TObjectPtr<AThunderHammerClosureController>> Peers;
    UPROPERTY() TObjectPtr<AThunderHammerClosureController> Guest;
    UPROPERTY() TObjectPtr<AThunderHammerClosureController> Observer;
    TWeakObjectPtr<AFPSGAMECharacter> DyingPawn;
    TSet<TWeakObjectPtr<AActor>> Waves;
    double Started=0.,CaseAt=0.,LastSetup=-10.,ExitAt=-1.;
    int32 Prepared=-1;
    uint32 RequestAtStart=0;
    bool Killed=false,LateRequested=false,Disconnected=false;
};
