#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "VillageOilCarry.generated.h"

class AVillageOilKettle;
class UColdSteelStatusModel;
class UForgeArmsMeshComponent;
class USkeletalMeshComponent;
class AFPSGAMECharacter;
class FPrimitiveComponentId;
struct FInputKeyEventArgs;

UENUM()
enum class EOilCarryPhase : uint8 { Empty, Held, Pour };
USTRUCT()
struct FOilHandState
{
    GENERATED_BODY()
    UPROPERTY() EOilCarryPhase Phase=EOilCarryPhase::Empty;
    UPROPERTY() double Since=0.;
};

UCLASS()
class UVillageOilCarry final : public UActorComponent
{
    GENERATED_BODY()
public:
    UVillageOilCarry();
    bool Occupied() const {return State.Phase!=EOilCarryPhase::Empty;}
    bool HandleInput(const FInputKeyEventArgs& Event);
    void Cancel();
    void RefreshEquipment(const UColdSteelStatusModel& Model);
    bool PourLip(FVector& WorldPoint) const;
    void Take(AVillageOilKettle* Kettle);
    void HideFirstPersonEquipment(const AActor* ViewTarget,TSet<FPrimitiveComponentId>& Hidden) const;
    void PoseWorldArms(USkeletalMeshComponent& Mesh,TArray<FTransform>& Pose) const;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    virtual void TickComponent(float Delta,ELevelTick Tick,FActorComponentTickFunction* Fn) override;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_Hands) FOilHandState State;
    UFUNCTION() void OnRep_Hands();
    UFUNCTION(Server,Reliable) void ServerTake(AVillageOilKettle* Kettle);
    UFUNCTION(Server,Reliable) void ServerPour();
    UFUNCTION(Server,Reliable) void ServerCancel();
    UFUNCTION(Client,Reliable) void ClientTakeResult(bool Accepted);
    void SetState(EOilCarryPhase NewPhase);
    bool CanTake() const;
    bool HandsInUse() const;
    void RememberEquipment();
    void UpdateVisual();
    void PrepareVisual();
    void PrepareWorldGrip(USkeletalMesh* BodyMesh);
    FTransform PanPose(bool CameraSpace) const;
    AFPSGAMECharacter* Player() const;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> ViewPot;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> WorldPot;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> ViewOil;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> WorldOil;
    UPROPERTY() TObjectPtr<UForgeArmsMeshComponent> Arms;
    TArray<FTransform> RestPose;
    TArray<int32> ArmBones;
    FTransform BaseContact[2];
    TWeakObjectPtr<USkeletalMesh> WorldGripMesh;
    FTransform WorldHandleInWrist[2];
    TArray<int32> WorldFingers[2];
    TArray<FTransform> WorldFingerPose;
    int32 OffhandSlotAtTake=INDEX_NONE;
    FString MainItemAtTake,OffhandItemAtTake;
    bool bTakePending=false,bLeftPressed=false,bReleasedOil=false,bLocalCancel=false,bPourQueued=false;
};
