#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GunAssemblyInteraction.generated.h"
class UGunAssemblySystem;
class UColdSteelHUDWidget;
class UGunAssemblyActionWidget;
class AVoxelBuildPrefabActor;
class UCameraComponent;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UForgeArmsMeshComponent;
class USoundBase;
class USoundCue;
class UAudioComponent;
struct FStreamableHandle;
struct FInputKeyEventArgs;

UCLASS()
class FPSGAME_API AGunAssemblyInteraction : public AActor
{
    GENERATED_BODY()
public:
    AGunAssemblyInteraction();
    void Prepare(APlayerController* Player,AVoxelBuildPrefabActor* Table,UColdSteelHUDWidget* OwnerHUD);
    bool Ready(FString& Reason) const;
    bool Start(FString& Reason);
    void Enter();
    bool IsRunning() const {return bRunning;}
    bool HandleInput(const FInputKeyEventArgs& Event);
    void Stop(bool bReturnPanel);
    virtual void Tick(float Dt) override;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void AssetsLoaded();
    void CacheWorkspace();
    void FrameWorkspace();
    void RestorePlayer();
    void Drop();
    void ClearRotationInput();
    void ResetLoose(int32 Part);
    bool CursorOnPlane(float Height,FVector& Local) const;
    void Present(float Dt);
    void PoseHands(float Dt);
    void SolveHand(int32 Side,const FTransform& Target,float Curl);
    void SetupHands();
    void PlayContact(float Pitch);
    void UpdateCalibrationAudio(bool bSuccessful,float DeltaTime);
    void StopCalibrationAudio();
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Ghost;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UForgeArmsMeshComponent> Arms;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Parts;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> GhostMaterial;
    UPROPERTY(Transient) TObjectPtr<UGunAssemblySystem> System;
    UPROPERTY(Transient) TObjectPtr<UGunAssemblyActionWidget> Prompt;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ContactSound;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UAudioComponent> CalibrationAudio;
    UPROPERTY(Transient) TObjectPtr<USoundCue> CalibrationLoop;
    TWeakObjectPtr<APlayerController> PC;
    TWeakObjectPtr<AVoxelBuildPrefabActor> Station;
    TWeakObjectPtr<UColdSteelHUDWidget> HUD;
    TWeakObjectPtr<AActor> PreviousView;
    TWeakObjectPtr<APawn> WorkingPawn;
    TSharedPtr<FStreamableHandle> Load;
    TArray<FVector> Positions;
    TArray<float> Angles;
    TArray<FTransform> Reference,LocalReference,Pose;
    TMap<int32,FQuat> Fingers;
    TArray<int32> ArmBones;
    struct FAssemblyHand {int32 Clavicle=-1,Upper=-1,Lower=-1,Hand=-1;TArray<int32> Bones;FTransform Grip;};
    FAssemblyHand Hands[2];
    FVector2D Aim=FVector2D(.5,.45),CalibrationTarget=FVector2D(.5,.42);
    FVector DragOffset=FVector::ZeroVector,HandPosition=FVector::ZeroVector;
    FBox Workspace=FBox(ForceInit),DragBounds=FBox(ForceInit);
    FIntPoint FramedViewport=FIntPoint::ZeroValue;
    float WorkspaceBottom=.6f;
    FString Error,Feedback;
    int32 Dragged=INDEX_NONE,Hovered=INDEX_NONE,Snapping=INDEX_NONE;
    float SnapTime=0,Clock=0,FinishRetryAt=0,FeedbackUntil=0,RefreshClock=0;
    float CalibrationClock=0;
    float CalibrationSuccessTime=0;
    bool bCalibrationAudioWanted=false;
    uint32 CalibrationSeed=0;
    float RotationDelayRemaining=0;
    bool bRotateLeft=false,bRotateRight=false;
    FVector SnapFrom=FVector::ZeroVector;float SnapAngle=0;
    bool bReady=false,bRunning=false,bHeld=false,bInputLocked=false,bHiddenPawn=false,bWasCursor=false,bHandsReady=false,bContactPlayed=false;
};
