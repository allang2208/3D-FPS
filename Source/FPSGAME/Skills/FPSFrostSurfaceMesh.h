#pragma once
#include "CoreMinimal.h"

class AActor;
class APawn;
class USceneComponent;
class UDynamicMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;

/** Terrain-conforming polar frost surface / sigil mesh builder shared by Blizzard & AbsoluteZero.
 *  Drapes a continuous translucent mesh over real colliding ground, roads, cobbles, wood decks,
 *  stairs, and slopes — completely immune to terrain material decal truncation, bReceivesDecals=false,
 *  and higher-SortOrder ground decals.
 */
namespace FrostSurfaceMesh
{
    inline constexpr const TCHAR* SheetMaterialPath =
        TEXT("/Game/Skills/AbsoluteZero/M_FrostSurfaceSheet.M_FrostSurfaceSheet");
    inline constexpr const TCHAR* SigilMaterialPath =
        TEXT("/Game/Skills/AbsoluteZero/M_AbsoluteZeroSigil.M_AbsoluteZeroSigil");
    inline constexpr const TCHAR* InwardMistPath =
        TEXT("/Game/Skills/AbsoluteZero/NS_AbsoluteZeroInwardMist.NS_AbsoluteZeroInwardMist");
    inline constexpr const TCHAR* BurstWavePath =
        TEXT("/Game/Skills/AbsoluteZero/NS_AbsoluteZeroBurstWave.NS_AbsoluteZeroBurstWave");
    inline constexpr const TCHAR* SpireMaterialPath =
        TEXT("/Game/Skills/AbsoluteZero/M_AbsoluteZeroSpire.M_AbsoluteZeroSpire");
    inline constexpr const TCHAR* SpireShellMaterialPath =
        TEXT("/Game/Skills/AbsoluteZero/M_AbsoluteZeroSpireShell.M_AbsoluteZeroSpireShell");
    inline constexpr const TCHAR* ShockRingMaterialPath =
        TEXT("/Game/Skills/AbsoluteZero/M_AbsoluteZeroShockRing.M_AbsoluteZeroShockRing");

    UDynamicMeshComponent* BuildConformingDisc(
        AActor* Owner,
        USceneComponent* AttachParent,
        APawn* Caster,
        const FVector& Center,
        const FVector& AxisX,
        float RadiusX,
        float RadiusY,
        UMaterialInterface* Material,
        TObjectPtr<UMaterialInstanceDynamic>& OutMID,
        int32 NumAngles = 56,
        int32 NumRings = 14,
        bool bWallOcclude = true,
        float LiftCM = 3.8f);

    /** Swept 3D cryo shockwave ring / elevated frost crest skirt centered on Origin (unit radius 100 cm,
     *  scaled outward smoothly by the caller from inner hub to blast rim). */
    UDynamicMeshComponent* BuildShockRing(
        AActor* Owner,
        USceneComponent* AttachParent,
        const FVector& Origin,
        UMaterialInterface* Material,
        TObjectPtr<UMaterialInstanceDynamic>& OutMID,
        int32 NumAngles = 64);
}
