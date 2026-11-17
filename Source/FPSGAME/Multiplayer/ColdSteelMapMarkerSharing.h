#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ColdSteelMapMarkerSharing.generated.h"

class APlayerController;
class ATemperateHillsWorld;
struct FColdSteelMapMarker;

/** Only an explicitly shared marker is ever serialized. The owning PlayerState supplies identity. */
USTRUCT()
struct FColdSteelSharedMapMarker
{
    GENERATED_BODY()
    UPROPERTY() FGuid Id;
    UPROPERTY() FString Region;
    UPROPERTY() FString Area;
    UPROPERTY() FString Label;
    UPROPERTY() FVector AbsolutePosition=FVector::ZeroVector;
    UPROPERTY() int32 Floor=0;
    UPROPERTY() uint8 ColorIndex=0;
    UPROPERTY() bool bDungeon=false;
};

struct FColdSteelMapShareResult
{
    FGuid Id;
    uint32 Request=0;
    bool bAccepted=false;
    FString Reason;
};

/** Cooperation-room visibility. Private markers and fog never enter this component. */
UCLASS()
class FPSGAME_API UColdSteelMapMarkerSharing : public UActorComponent
{
    GENERATED_BODY()
public:
    UColdSteelMapMarkerSharing();
    static UColdSteelMapMarkerSharing* For(const APlayerController* Player);
    uint32 Publish(const FColdSteelMapMarker& Marker);
    uint32 Withdraw(FGuid Id);
    void TakeResults(TArray<FColdSteelMapShareResult>& Out);
    const TArray<FColdSteelSharedMapMarker>& Shared() const { return SharedMarkers; }
    uint32 Revision() const { return ChangeSerial; }
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* Tick) override;

private:
    friend class AColdSteelMapMarkerWireController;
    friend class UColdSteelDungeonFogCheckCommandlet;
    UPROPERTY(ReplicatedUsing=OnRep_SharedMarkers) TArray<FColdSteelSharedMapMarker> SharedMarkers;
    UFUNCTION() void OnRep_SharedMarkers();
    UFUNCTION(Server,Reliable) void ServerPublish(FColdSteelSharedMapMarker Marker,uint32 Request);
    UFUNCTION(Server,Reliable) void ServerWithdraw(FGuid Id,uint32 Request);
    UFUNCTION(Client,Reliable) void ClientResult(FGuid Id,uint32 Request,bool bAccepted,const FString& Reason);
    TArray<FColdSteelMapShareResult> Results;
    TWeakObjectPtr<UWorld> BoundWorld;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    bool bSearchedHills=false;
    uint32 NextRequest=0,LastRequest=0,ChangeSerial=0;
    void BindWorld();
    void Changed();
    FString NonDungeonRegion();
    bool RegionIsCurrent(const FColdSteelSharedMapMarker& Marker);
    bool Validate(const FColdSteelSharedMapMarker& Marker,FString& Reason);
};
