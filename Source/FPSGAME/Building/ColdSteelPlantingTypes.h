#pragma once
#include "CoreMinimal.h"
#include "ColdSteelPlantingTypes.generated.h"

/** Stored with inventory in one checked profile transaction; older saves default empty. */
USTRUCT()
struct FColdSteelCropPlant
{
    GENERATED_BODY()
    UPROPERTY() FGuid PlantId;
    UPROPERTY() FString WorldKey;
    UPROPERTY() FGuid BedId;
    UPROPERTY() FIntVector BedCell=FIntVector::ZeroValue;
    UPROPERTY() int32 Slot=0;
    UPROPERTY() FIntPoint Footprint=FIntPoint(1,1);
    UPROPERTY() FName Crop;
    UPROPERTY() FName Variant;
    UPROPERTY() FVector LocalRootCm=FVector::ZeroVector;
    UPROPERTY() float YawDegrees=0.f;
    UPROPERTY() float UniformScale=1.f;
    UPROPERTY() int64 PlantedUtcTicks=0;
    UPROPERTY() double GrowthSeconds=1200.;
    UPROPERTY() FString OutputItem;
    UPROPERTY() int64 OutputCount=3;

    static bool Fits(int32 Anchor,FIntPoint Size)
    {return Anchor>=0&&Anchor<16&&Size.X>0&&Size.Y>0&&Anchor/4+Size.X<=4&&Anchor%4+Size.Y<=4;}
    bool Occupies(int32 Index) const
    {return Fits(Slot,Footprint)&&Index>=0&&Index<16&&Index/4>=Slot/4&&Index/4<Slot/4+Footprint.X&&Index%4>=Slot%4&&Index%4<Slot%4+Footprint.Y;}
    double AgeSeconds(int64 NowTicks) const
    {return FMath::Max(0.,double(NowTicks-PlantedUtcTicks)/ETimespan::TicksPerSecond);}
    int32 Stage(int64 NowTicks) const
    {return AgeSeconds(NowTicks)>=GrowthSeconds?3:AgeSeconds(NowTicks)>=GrowthSeconds*.5?2:1;}
};

/** Public world state only. Never merged into a player's personal profile. */
USTRUCT()
struct FColdSteelPlantingNetState
{
    GENERATED_BODY()
    UPROPERTY() FString WorldKey;
    UPROPERTY() int64 Revision=-1;
    // Runtime publication order, including save-lock changes with no crop commit.
    UPROPERTY() uint64 SnapshotSequence=0;
    UPROPERTY() bool bReady=false;
    UPROPERTY() bool bSaveBlocked=false;
    UPROPERTY() TArray<FColdSteelCropPlant> Plants;
    UPROPERTY() int64 UtcAnchorTicks=0;
    UPROPERTY() double ServerAnchorSeconds=0.;
};
