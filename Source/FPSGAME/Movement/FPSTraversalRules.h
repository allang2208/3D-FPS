#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "FPSTraversalRules.generated.h"

UENUM(BlueprintType)
enum class EFPSTraversalAction : uint8
{
    None, Step, Vault, Mantle
};

// Measurements are in cm, from the standing foot plane, not the camera.
// Geometry flags must come from collision queries; defaults cannot grant traversal.
USTRUCT(BlueprintType)
struct FPSGAME_API FFPSTraversalProbe
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Height = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Depth = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float EdgeDistance = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float FacingDot = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float LandingHeightDelta = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bJumpPressed = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bStandingGrounded = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bAirborne = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bAirReachable = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bTraversalAvailable = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bStableObstacle = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bApproachClear = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bTopGrippable = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bTopStandingSpace = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bVaultPathClear = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bLandingStandingSpace = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bMantlePathClear = false;
};

// Immutable CDO configuration owned by the engine. No tick, animation or movement side effects.
UCLASS(Config=Game, DefaultConfig)
class FPSGAME_API UFPSTraversalSettings : public UObject
{
    GENERATED_BODY()
public:
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Height") float StepHeight = 50.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Height") float VaultMaxHeight = 120.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Height") float MantleMaxHeight = 200.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Geometry") float VaultMaxDepth = 120.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Geometry") float MaxEdgeDistance = 20.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Geometry") float MaxFacingAngle = 40.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Geometry") float MaxLandingDrop = 60.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Geometry") float MaxLandingRise = 50.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Air") float AirMinLedgeHeight = 20.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Air") float AirMaxLedgeHeight = 200.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Air") float AirMaxFallSpeed = 900.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Air") float AirMaxLandingDrop = 200.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Animation", meta=(ClampMin="0.1")) float VaultPlaybackRate = 2.f;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Animation") TSoftObjectPtr<class USkeletalMesh> ArmsMesh;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Animation") TSoftObjectPtr<class UAnimSequence> VaultAnimation;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Animation") TSoftObjectPtr<class UAnimSequence> MantleAnimation;
    UPROPERTY(Config, EditAnywhere, Category="Traversal|Animation") TSoftObjectPtr<class UAnimSequence> ClimbAnimation;

    bool IsValidConfiguration() const;
    EFPSTraversalAction ClassifyHeight(float Height) const;
    EFPSTraversalAction Evaluate(const FFPSTraversalProbe& Probe) const;
};

UCLASS()
class FPSGAME_API UFPSTraversalRules : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    // Pure single-player eligibility only. Does not move a character or consume Jump.
    UFUNCTION(BlueprintPure, Category="FPS|Traversal")
    static EFPSTraversalAction ClassifyObstacleHeight(float Height);
    UFUNCTION(BlueprintPure, Category="FPS|Traversal")
    static EFPSTraversalAction EvaluateObstacle(const FFPSTraversalProbe& Probe);
};
