#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "VillageOilCarry.generated.h"

class AVillageOilKettle;
class ATemperateHillsWorld;
class UColdSteelStatusModel;
class UVillageOilArmsMeshComponent;
class USkeletalMeshComponent;
class UDecalComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
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
    USkeletalMeshComponent* GetFirstPersonArms() const;
    UDecalComponent* GetPourPreviewDecal() const;
    UMaterialInstanceDynamic* GetPourPreviewMID() const;
    const FVector& GetCachedPreviewPoint() const {return CachedPreviewPoint;}
    bool HasPreviewPoint() const {return bHasPreviewPoint;}
    void RefreshPourPreview(float Delta);
    bool IsPresentationActive() const {return Occupied() && !bLocalCancel;}
    bool IsPendingOrOccupied() const {return (Occupied() || bTakePending) && !bLocalCancel;}
    static bool IsStowingEquipment(const AActor* Owner);
    static bool IsBlockingWeaponActions(const AActor* Owner);
    bool CanTakeNow(FString* OutReason=nullptr) const;
    bool ResolvePourTarget(FVector& OutGroundPoint,FVector& OutNormal) const;
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
    bool CanTake(bool bAllowInspect=false,FString* OutReason=nullptr) const;
    bool HandsInUse(bool bAllowInspect=false) const;
    void RememberEquipment();
    void ClearStaleWeaponActions();
    void AdvanceLocomotionFeedback(float Delta);
    void UpdatePourPreview(float Delta);
    void HidePourPreview();
    void UpdateVisual();
    void PrepareVisual();
    void PrepareWorldGrip(USkeletalMesh* BodyMesh);
    FTransform PanPose(bool CameraSpace,bool bIncludeLocalSway=true) const;
    AFPSGAMECharacter* Player() const;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> ViewPot;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> WorldPot;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> ViewOil;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> WorldOil;
    UPROPERTY() TObjectPtr<UVillageOilArmsMeshComponent> Arms;
    UPROPERTY(Transient) TObjectPtr<UDecalComponent> PourPreviewDecal;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> PourPreviewMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> PourPreviewMaterial;
    TWeakObjectPtr<ATemperateHillsWorld> CachedHillsWorld;
    TArray<FTransform> BindPose;
    TArray<FTransform> RestPose;
    TArray<int32> ArmBones;
    FTransform BaseContact[2];
    TWeakObjectPtr<USkeletalMesh> WorldGripMesh;
    TArray<FTransform> WorldBindPose;
    FTransform WorldHandleInWrist[2];
    TArray<int32> WorldFingers[2];
    TArray<FTransform> WorldFingerPose;
    int32 OffhandSlotAtTake=INDEX_NONE;
    FString MainItemAtTake,OffhandItemAtTake,ToolItemAtTake;
    FVector2D LookSway=FVector2D::ZeroVector,LookSwayVel=FVector2D::ZeroVector;
    FVector2D OilSlosh=FVector2D::ZeroVector,OilSloshVel=FVector2D::ZeroVector;
    FVector2D PrevOilShake=FVector2D::ZeroVector;
    FRotator PrevControlRot=FRotator::ZeroRotator;
    float LandingDip=0.f,LandingDipVel=0.f;
    double TakePendingSince=-100.,NextPreviewSampleAt=-100.;
    FVector CachedPreviewPoint=FVector::ZeroVector,CachedPreviewNormal=FVector::UpVector;
    FVector LastPreviewEye=FVector::ZeroVector;
    FRotator LastPreviewAim=FRotator::ZeroRotator;
    FVector2D CachedPreviewRadii=FVector2D::ZeroVector;
    bool bHasPreviewPoint=false,bHasPreviewCamera=false,bHasPrevControlRot=false,bWasFalling=false;
    bool bTakePending=false,bLeftPressed=false,bRightPressed=false,bReleasedOil=false,bLocalCancel=false,bPourQueued=false;
};
