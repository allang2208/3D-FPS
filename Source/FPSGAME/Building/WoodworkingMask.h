#pragma once
#include "CoreMinimal.h"

namespace ColdSteelWoodworking
{
struct FSettings
{
    int32 Width=512,Height=256,UndoLimit=3,EdgeBandPixels=4;
    double Seconds=90,RequiredClearance=.98,MaximumDamage=.12;
    double IntegrityWeight=.50,EdgeWeight=.25,ClearanceWeight=.20,SpeedWeight=.05;
    bool bAutoPeel=true,bCheckConnections=true;
};
struct FMetrics
{
    double Clearance=0,Integrity=1,EdgeFit=0;
    double Quality(const FSettings& Settings,double Elapsed) const;
};
/** Presentation telemetry from actual saw removal only; never emitted by peel or undo. */
struct FCutFeedback
{
    int32 Removed=0,Damaged=0;
    FVector2D DamagePoint=FVector2D::ZeroVector;
    TArray<FVector2D,TInlineAllocator<8>> Samples;
};
/** One bounded raster is shared by drawing, cutting, damage, scoring and the target preview.
 * Coordinates are mask pixels; no viewport/DPI or inventory state enters this class. */
class FMask
{
public:
    bool Initialize(const FSettings& Settings,const TArray<FVector2D>& Polygon,const TArray<FVector2D>& Anchors,FString& Error);
    void SerializeNetwork(FArchive& Ar);
    bool RestoreNetwork(const TArray<uint8>& Bytes);
    void BeginStroke();
    bool CutSawSweep(const FVector2D& A0,const FVector2D& B0,const FVector2D& A1,const FVector2D& B1,double HalfKerf);
    bool SawTouches(const FVector2D& A0,const FVector2D& B0,const FVector2D& A1,const FVector2D& B1,double HalfKerf,bool IncludeRemoved=false) const;
    bool SawEntersWood(const FVector2D& A0,const FVector2D& B0,const FVector2D& A1,const FVector2D& B1,double HalfKerf) const;
    const FCutFeedback& LastCut() const {return CutFeedback;}
    uint64 CutSerial() const {return CutGeneration;}
    const TArray<uint8>& DetachedWaste() const {return PeeledMask;}
    uint64 PeelSerial() const {return PeelGeneration;}
    void EndStroke();
    bool Undo();
    bool CanUndo() const {return UndoRemaining>0&&!LastStroke.IsEmpty()&&!bStroke;}
    bool ConnectionsIntact() const;
    bool DamageExceeded() const {return Metrics().Integrity<1.0-Config.MaximumDamage;}
    FMetrics Metrics() const;
    const TArray<uint8>& Wood() const {return WoodMask;}
    const TArray<uint8>& Target() const {return TargetMask;}
    const TArray<uint8>& Damage() const {return DamageMask;}
    const TArray<uint8>& Boundary() const {return TargetBoundary;}
    int32 Revision() const {return ChangeSerial;}
    int32 Undos() const {return UndoRemaining;}
    bool StrokeActive() const {return bStroke;}
private:
    void Remove(int32 Cell);
    void PeelWaste();
    void Neighbours(int32 Cell,TArray<int32,TInlineAllocator<4>>& Out) const;
    FSettings Config;
    TArray<uint8> WoodMask,TargetMask,DamageMask,TargetBoundary,EdgeBand;
    TArray<int32> CriticalCells,LastStroke;
    int32 TargetCount=0,WasteCount=0,BoundaryCount=0,BandCount=0;
    int32 KeptTarget=0,RemainingWaste=0,KeptBoundary=0,RemainingBand=0;
    int32 ChangeSerial=0,UndoRemaining=0;
    bool bStroke=false;
    FCutFeedback CutFeedback;
    uint64 CutGeneration=0;
    TArray<uint8> PeeledMask;
    uint64 PeelGeneration=0;
};
}
