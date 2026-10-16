#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AlchemyTabletop.h"
#include "AlchemyWorldView.generated.h"
class UCameraComponent;
class UForgeArmsMeshComponent;
class AVoxelBuildPrefabActor;
class UPotionWorkbenchVisualComponent;
struct FStreamableHandle;
UCLASS(Transient,NotBlueprintable)
class FPSGAME_API AAlchemyWorldView : public AActor
{
    GENERATED_BODY()
public:
    AAlchemyWorldView();
    void Configure(AVoxelBuildPrefabActor* Bench,APlayerController* Player);
    bool Ready() const;
    bool Failed() const;
    void Enter();
    void Leave();
    virtual void Tick(float Delta) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void Loaded();
    void Solve(int32 Side,const FTransform& Target,const FTransform& Torso);
    UPROPERTY() TObjectPtr<UCameraComponent> Camera;
    UPROPERTY() TObjectPtr<UForgeArmsMeshComponent> Arms;
    TWeakObjectPtr<AVoxelBuildPrefabActor> Station;
    TWeakObjectPtr<UPotionWorkbenchVisualComponent> Visual;
    TWeakObjectPtr<APlayerController> Player;
    TWeakObjectPtr<APawn> WorkingPawn;
    TWeakObjectPtr<AActor> PreviousView;
    TSharedPtr<FStreamableHandle> Loading;
    TArray<FTransform> Reference,LocalReference,Pose;
    TArray<int32> ArmBones;
    struct FHand {int32 Clavicle=-1,Upper=-1,Lower=-1,Hand=-1;TArray<int32> Bones;FTransform Grip;};
    FHand Hands[2];
    TMap<int32,FQuat> Fingers;
    bool bReady=false,bEntered=false,bLoadFinished=false,bHidPawn=false;
    FVector Eye=AlchemyTabletop::Eye;
    FVector Aim=AlchemyTabletop::Aim;
};
