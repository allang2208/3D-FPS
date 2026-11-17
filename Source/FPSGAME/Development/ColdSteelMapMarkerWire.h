#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../UI/ColdSteelMapMarkers.h"
#include "../UI/ColdSteelDungeonMap.h"
#include "ColdSteelMapMarkerWire.generated.h"
class FJsonValue;

/** Explicit opt-in fixture. Exercises the real marker model and PlayerState RPCs over UDP. */
UCLASS()
class AColdSteelMapMarkerWireController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override;
    UFUNCTION(Client,Reliable) void ClientStage(int32 Value);
    UFUNCTION(Client,Reliable) void ClientExit();
    UFUNCTION(Server,Reliable) void ServerReport(int32 Value,const FString& Json);
    int32 Expected=INDEX_NONE;
private:
    FColdSteelMapMarkers Markers;
    FColdSteelDungeonMap Fog;
    FGuid PrivateId,SharedId,ProbeId;
    int32 Stage=INDEX_NONE;
    bool Started=false,Reported=false,ActionsOK=true,Rejected=false;
    double StageAt=0.;
    bool Exercise();
    bool Observe(FString& Detail);
};

UCLASS()
class AColdSteelMapMarkerWireGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AColdSteelMapMarkerWireGameMode();
    virtual void BeginPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Tick(float Delta) override;
    void Receive(AColdSteelMapMarkerWireController* PC,int32 Value,const FString& Json);
private:
    UPROPERTY() TObjectPtr<AColdSteelMapMarkerWireController> Host;
    TWeakObjectPtr<AColdSteelMapMarkerWireController> Guest;
    TArray<TSharedPtr<FJsonValue>> Rows;
    int32 Phase=INDEX_NONE,Replies=0,GuestCount=0;
    bool Passed=true,Advance=false,AwaitingDisconnect=false,Finished=false;
    double PhaseAt=0.,ExitAt=-1.;
    void Dispatch(int32 Value);
    void Finish(bool Success);
};
