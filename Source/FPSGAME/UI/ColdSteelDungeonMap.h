#pragma once

#include "CoreMinimal.h"

class APawn;
class APlayerController;
class UDungeonRunSubsystem;

struct FColdSteelDungeonPatch
{
    FBox2D Bounds;
    int32 Footprint;
    bool bPassage;
    double GroundZ = 0.;
};

struct FColdSteelDungeonLabel
{
    FVector2D Point;
    FString Text;
    int32 RampNode = INDEX_NONE;
    TOptional<int32> Destination;
};

struct FColdSteelDungeonMapFloor
{
    FBox2D Bounds = FBox2D(ForceInit);
    TArray<FColdSteelDungeonPatch> Patches;
    TMap<FIntPoint, TArray<int32>> Tiles;
    TArray<FColdSteelDungeonLabel> Labels;
    void ForEachVisiblePatch(const FBox2D& View,TFunctionRef<void(const FColdSteelDungeonPatch&)> Draw) const;
};

/** Owned by the local player's menu and updated even when the M map is closed. */
struct FColdSteelDungeonMap
{
    /** Maintain this local player's current run even while the map is closed or the player is in the hub. */
    bool Update(APlayerController* Player);
    bool IsKnown(FVector2D Point, int32 Floor) const;
    bool MarkerGround(APawn& Viewer,FVector2D Point,int32 Floor,FVector& Position) const;
    bool IsLandmarkKnown(FVector Position, int32 Floor) const;
    int32 LandmarkFloor(FVector Position) const;
    static FString FloorName(int32 Floor);

    TArray<int32> DiscoveredFloors;
    TMap<int32, FColdSteelDungeonMapFloor> Layers;
    int32 PlayerFloor = 0;
    FString PlayerArea;
    uint32 Revision = 0;
    uint32 LayoutSerial = 0;

private:
    friend class UColdSteelDungeonFogCheckCommandlet;
    struct FFootprint
    {
        FBox Box;
        int32 Node, Floor;
        double GroundZ;
        bool bPassage, bFallback;
        FName ModuleTag;
    };
    struct FRamp
    {
        double MiddleZ;
        int32 Lower, Upper;
        TArray<FVector> Path;
        TArray<double> Distance;
        double HalfWidth;
        void SetPath(const TArray<FVector>& Anchors,FVector Low,FVector High);
        double Project(FVector At,double& Along) const;
    };

    TWeakObjectPtr<UDungeonRunSubsystem> Source;
    TWeakObjectPtr<APlayerController> Owner;
    TWeakObjectPtr<APawn> SamplingPawn;
    TWeakObjectPtr<ULevel> BoundLevel;
    FString RunId;
    TArray<FFootprint> Footprints;
    TMap<FIntPoint, TArray<int32>> SpatialBins;
    TMap<int32, FRamp> Ramps;
    struct FDeckAnchor { FVector Point; int32 Floor; };
    TMap<int32,TArray<FDeckAnchor>> DeckAnchors;
    int32 LastFootprint = INDEX_NONE;
    FVector LastSample = FVector(UE_DOUBLE_BIG_NUMBER);
    double RetryBlockedAt = DBL_MAX;
    void Bind(UDungeonRunSubsystem& Run);
    void ResetExploration();
    void PauseSampling();
    void Record(APawn& Pawn);
    int32 FindFootprint(FVector At,const UPrimitiveComponent* Support=nullptr) const;
    int32 FloorFor(int32 Footprint, FVector At,const UPrimitiveComponent* Support=nullptr) const;
    void RecordGround(APawn& Pawn,FVector At,const UPrimitiveComponent* Support);
    TWeakObjectPtr<const UPrimitiveComponent> LastSupport;
    bool Reveal(FIntPoint Tile, int32 Footprint, int32 Floor, const FBox2D& Rect, double GroundZ=UE_DOUBLE_BIG_NUMBER);
};
