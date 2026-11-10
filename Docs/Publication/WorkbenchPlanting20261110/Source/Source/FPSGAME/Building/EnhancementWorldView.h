#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EnhancementWorldView.generated.h"
class AVoxelBuildPrefabActor;
class AColdSteelPickup;
class UCameraComponent;
class AEnhancementRitualEffect;

/** Local presentation only: the selected instance never leaves the profile.
 * Import contract: ArcaneItem and ArcaneCamera sockets must be saved on the final
 * imported static mesh, using its actual UE axes. Missing sockets reject Begin.
 * V6 author geometry (0,-5.2,96.85) cm/front -Y and FBX-node rotated position
 * (0,+5.2,96.85) cm/front +Y are references only, never runtime fallback coordinates.
 */
UCLASS(Transient,NotBlueprintable)
class FPSGAME_API AEnhancementWorldView : public AActor
{
    GENERATED_BODY()
public:
    AEnhancementWorldView();
    bool Begin(APlayerController* Controller,AVoxelBuildPrefabActor* Bench);
    bool SetItem(const FString& InstanceId);
    // Call only after a successful place receipt; SetItem/Refresh never starts it.
    void PlayPlacement(const FString& InstanceId);
    void PlayRitual(bool bEnchant);
    bool HitItem(FVector2D ViewportPixel) const;
    void SetItemHovered(bool Hovered);
    void End();
    bool IsSessionValid() const;
    bool IsOpen() const { return bEntered; }
    FVector RitualLocation() const;
    static bool HasActiveSession(const APlayerController* Controller);
    virtual void CalcCamera(float DeltaTime,struct FMinimalViewInfo& OutResult) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void UpdatePose();
    void UpdateDisplayPose();
    void StopPlacement();
    float PlacementOffset() const;
    float PlacementTime=-1.f,PlacementWait=0.f,SessionCheckElapsed=0.f;
    double PlacementStartedAt=0.;
    bool bPlacementWaiting=false;
    void ApplyItemHover();
    TSharedPtr<struct FStreamableHandle> OutlineLoad;
    bool bItemHovered=false;
    UPROPERTY() TObjectPtr<UCameraComponent> Camera;
    UPROPERTY() TObjectPtr<AColdSteelPickup> Display;
    UPROPERTY() TObjectPtr<AEnhancementRitualEffect> RitualEffect;
    TWeakObjectPtr<APlayerController> Player;
    TWeakObjectPtr<AVoxelBuildPrefabActor> Station;
    TWeakObjectPtr<APawn> WorkingPawn;
    TWeakObjectPtr<AActor> PreviousView;
    FString SelectedId,SelectedData;
    bool bEntered=false,bHidPawn=false;
};
