#pragma once

#include "CoreMinimal.h"
#include "Engine/EngineTypes.h"
#include "Components/ActorComponent.h"
#include "FPSFurnitureRestComponent.generated.h"

class AFPSGAMECharacter;
class UStaticMeshComponent;
struct FMinimalViewInfo;

USTRUCT()
struct FFurnitureRestState
{
    GENERATED_BODY()
    // 0=free, 1=align, 2=enter, 3=idle, 4=leave.
    UPROPERTY() uint8 Phase=0;
    UPROPERTY() FName Kind;
    UPROPERTY() float Started=0.f;
    UPROPERTY() FTransform Root;
    UPROPERTY() FTransform Approach;
    UPROPERTY() FVector Exit=FVector::ZeroVector;
    UPROPERTY() float GroundZ=0.f;
    // Runtime reservation: authority matches component/instance/slot; replicas
    // use the published slot location for local interaction feedback.
    UPROPERTY() int32 SlotIndex=INDEX_NONE;
    UPROPERTY() FVector SlotLocation=FVector::ZeroVector;
    UPROPERTY() bool bMirror=false;
};

/** One rest interaction per pawn. Furniture stays in its original actor/ISM batch. */
UCLASS(ClassGroup=(Movement))
class FPSGAME_API UFPSFurnitureRestComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSFurnitureRestComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Props) const override;
    bool IsResting() const { return State.Phase!=0; }
    /** True only during the settled lying loop, excluding entry and exit. */
    bool IsRestingInBed() const;
    static bool IsResting(const AActor* Actor);
    /** Called by the same HUD cadence and E dispatch as searchable containers. */
    FString UpdateFocus(bool bAllowed);
    bool Interact();
    void RequestLeave();
    void AnimationSample(FName& Clip,float& Seconds,float& Weight) const;
    void ApplyCamera(FMinimalViewInfo& View);
    /** Consume first-person mouse look in the supported body's neck frame. */
    bool UpdateRestLook(const FRotator& Input,FRotator& OutRotation);
    float FootDrop() const;
    bool IsPoseMirrored() const { return IsResting()&&State.bMirror; }
private:
    UFUNCTION(Server,Reliable) void ServerInteract();
    UFUNCTION(Server,Reliable) void ServerLeave();
    UFUNCTION() void OnRep_State();
    UPROPERTY(ReplicatedUsing=OnRep_State) FFurnitureRestState State;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Outline;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> OutlineMaterial;
    TSharedPtr<struct FStreamableHandle> OutlineLoad;
    TWeakObjectPtr<AFPSGAMECharacter> Character;
    TWeakObjectPtr<UStaticMeshComponent> FocusMesh,ActiveMesh;
    int32 FocusInstance=INDEX_NONE,ActiveInstance=INDEX_NONE,FocusSlot=INDEX_NONE;
    FTransform FocusTransform,ActiveTransform;
    FTransform SavedTransform;
    FRotator SavedControlRotation;
    TWeakObjectPtr<class AController> LockedController;
    TEnumAsByte<ECollisionEnabled::Type> SavedCollision=ECollisionEnabled::QueryAndPhysics;
    uint8 SavedMovement=1;
    bool bApplied=false,bSavedControllerYaw=true;
    float LastHealth=0.f;
    double LastFocusTime=-1.;
    FString CachedPrompt;
    // Local rendered POV only; furniture/body poses and replicated clocks stay unchanged.
    bool bRestCameraActive=false,bRestCameraHasView=false;
    bool bRestCameraLookInitialized=false,bRestCameraLying=false;
    FRotator RestCameraLook=FRotator::ZeroRotator;
    FQuat RestCameraLookFrame=FQuat::Identity,RestCameraEntryRotation=FQuat::Identity;
    FQuat RestCameraLastRotation=FQuat::Identity,RestCameraReturnRotationOffset=FQuat::Identity;
    float RestCameraLookStarted=0.f;
    FVector RestCameraEntryLocation=FVector::ZeroVector,RestCameraLastLocation=FVector::ZeroVector;
    float RestCameraReturnStarted=-1.f;
    TWeakObjectPtr<class USkeletalMesh> RestCameraMesh;
    int32 RestCameraTorso=INDEX_NONE,RestCameraNeck=INDEX_NONE,RestCameraPelvis=INDEX_NONE;
    FVector RestCameraLocalFront=FVector::ForwardVector,RestCameraLocalUp=FVector::UpVector;
    void BeginRestCamera();
    void EndRestCamera(bool bDead);
    void ApplyRestCamera(FMinimalViewInfo& View,class USkeletalMeshComponent& Body,bool bLying);
    void ApplyRestCameraReturn(FMinimalViewInfo& View);
    void OutlineLoaded();
    bool ResolveFocus(FHitResult& Hit,FTransform& Transform,int32& Slot,FName& Kind,FVector& Seat,float& Yaw,bool& bOccupied) const;
    bool IsSlotOccupied(const UStaticMeshComponent* Mesh,int32 Instance,int32 Slot,const FVector& Location) const;
    bool FindExit(const FTransform& Root,FVector& Exit,FName Kind,bool bMirror) const;
    bool ExitClear(const FVector& Position) const;
    void StartRest();
    void SetPhase(uint8 Phase);
    void FinishRest();
    void ApplyState();
    void ClearFocus();
    float Clock() const;
    float PhaseDuration() const;
};
