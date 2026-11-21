#include "VillageDefenseFootprint.h"
#include "VillageBuildDefense.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "PhysicsEngine/BodySetup.h"
#include "Math/Interval.h"

namespace VillageDefenseFootprint
{
    const FShape& Get(FName Id,UStaticMesh* Mesh)
    {
        // All three recipes have distinct authored static meshes. Cache their immutable
        // simple geometry across instances (including rebuilding a whole saved village).
        static TMap<TWeakObjectPtr<UStaticMesh>,FShape> Shapes;
        static const FShape Empty;
        if(!Mesh||!Mesh->GetBodySetup())return Empty;
        if(const auto* Found=Shapes.Find(Mesh))return *Found;
        FShape& Shape=Shapes.Add(Mesh);
        auto AddBox=[&Shape](FBox Box)
        {
            Box.Min.Z=FMath::Max(0.,Box.Min.Z);
            if(Box.Max.Z>Box.Min.Z){Shape.Boxes.Add(Box);Shape.Bounds+=Box;}
        };
        for(const FKBoxElem& Hull:Mesh->GetBodySetup()->AggGeom.BoxElems)
        {
            const FVector Extent=FVector(Hull.X,Hull.Y,Hull.Z)*.5;
            if(Hull.Rotation.IsNearlyZero())
            {
                AddBox(FBox(Hull.Center-Extent,Hull.Center+Extent));
                continue;
            }
            // Keep the free volume beneath the sloping bridge when mapping its
            // real inclined collision to the builder's 20 cm occupancy grid.
            const FTransform Tilt(Hull.Rotation,Hull.Center);
            const int32 Count=FMath::Max(1,FMath::CeilToInt(Hull.X/10.f));
            for(int32 I=0;I<Count;++I)
                AddBox(FBox(FVector(-Extent.X+Hull.X*I/Count,-Extent.Y,-Extent.Z),
                            FVector(-Extent.X+Hull.X*(I+1)/Count,Extent.Y,Extent.Z)).TransformBy(Tilt));
        }
        if(Id==VillageBuildDefense::StoneGate)
        {
            // Reserve only the grille's actual swept channel in the open arch.
            const FBox Travel(FVector(-337.5,-9.,0.),FVector(337.5,9.,955.));
            Shape.Boxes.Add(Travel);
            Shape.Bounds+=Travel;
        }
        return Shape;
    }

    void Rasterize(const FShape& Shape,const FTransform& Pose,TArray<FIntVector>& Cells)
    {
        // Disjoint height runs in each column keep the portal passage and both
        // stairwells open. Shared faces use a half-open horizontal ownership rule.
        TMap<FIntPoint,TArray<FInt32Interval,TInlineAllocator<2>>> Columns;
        constexpr double Size=20.;
        for(const FBox& Box:Shape.Boxes)
        {
            const FBox Bounds=Box.TransformBy(Pose);
            const int32 MinZ=FMath::FloorToInt((Bounds.Min.Z+.001)/Size);
            const int32 MaxZ=FMath::CeilToInt((Bounds.Max.Z-.001)/Size)-1;
            const FVector Center=Box.GetCenter(),Extent=Box.GetExtent();
            const double HalfX=FMath::Max(Extent.X,10.001);
            const double HalfY=FMath::Max(Extent.Y,10.001);
            for(int32 J=FMath::FloorToInt(Bounds.Min.Y/Size);J<=FMath::FloorToInt(Bounds.Max.Y/Size);++J)
            for(int32 I=FMath::FloorToInt(Bounds.Min.X/Size);I<=FMath::FloorToInt(Bounds.Max.X/Size);++I)
            {
                const FVector P=Pose.InverseTransformPosition(FVector((I+.5)*Size+.0003,(J+.5)*Size+.0001,Pose.GetLocation().Z))-Center;
                if(P.X < -HalfX || P.X >= HalfX || P.Y < -HalfY || P.Y >= HalfY)continue;
                Columns.FindOrAdd(FIntPoint(I,J)).Emplace(MinZ,MaxZ);
            }
        }
        Cells.Reset();
        for(auto& Column:Columns)
        {
            auto& Runs=Column.Value;
            Runs.Sort([](const auto& A,const auto& B){return A.Min<B.Min;});
            int32 Last=MIN_int32;
            for(const auto& Run:Runs)
            {
                for(int32 K=FMath::Max(Last+1,Run.Min);K<=Run.Max;++K)
                    Cells.Emplace(Column.Key.X,Column.Key.Y,K);
                Last=FMath::Max(Last,Run.Max);
            }
        }
    }

    void RasterizeGridEnvelope(FIntVector Footprint,const FTransform& Pose,TArray<FIntVector>& Cells)
    {
        // The catalog dimensions already include the actor's scale and both timber gate leaves.
        constexpr double Size=20., HalfCell=Size*.5, Epsilon=.001;
        const FVector Half=FVector(Footprint)*HalfCell;
        const FVector Origin=Pose.GetLocation();
        const FVector XAxis=Pose.GetUnitAxis(EAxis::X),YAxis=Pose.GetUnitAxis(EAxis::Y);
        const FVector Extent=XAxis.GetAbs()*Half.X+YAxis.GetAbs()*Half.Y;
        const int32 MinX=FMath::FloorToInt((Origin.X-Extent.X+Epsilon)/Size);
        const int32 MaxX=FMath::CeilToInt((Origin.X+Extent.X-Epsilon)/Size)-1;
        const int32 MinY=FMath::FloorToInt((Origin.Y-Extent.Y+Epsilon)/Size);
        const int32 MaxY=FMath::CeilToInt((Origin.Y+Extent.Y-Epsilon)/Size)-1;
        const int32 MinZ=FMath::RoundToInt(Origin.Z/Size);
        // Bounds above test the two world axes. Project each grid square onto both local axes
        // as well, so neither empty bounding-box corners nor mere edge contact claim a cell.
        const double LimitX=Half.X+HalfCell*(FMath::Abs(XAxis.X)+FMath::Abs(XAxis.Y))-Epsilon;
        const double LimitY=Half.Y+HalfCell*(FMath::Abs(YAxis.X)+FMath::Abs(YAxis.Y))-Epsilon;
        Cells.Reset();
        for(int32 Y=MinY;Y<=MaxY;++Y)for(int32 X=MinX;X<=MaxX;++X)
        {
            const FVector Delta((X+.5)*Size-Origin.X,(Y+.5)*Size-Origin.Y,0.);
            if(FMath::Abs(FVector::DotProduct(Delta,XAxis))>=LimitX||
                FMath::Abs(FVector::DotProduct(Delta,YAxis))>=LimitY)continue;
            for(int32 Z=0;Z<Footprint.Z;++Z)Cells.Emplace(X,Y,MinZ+Z);
        }
    }

    bool IsClear(UWorld& World,const FShape& Shape,const FTransform& Pose,const AActor* Builder)
    {
        if(Shape.Boxes.IsEmpty())return false;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageDefenseClearance),false,Builder);
        // Test the complete host while allowing neighbouring pieces to meet flush.
        const auto Blocked=[&](const FBox& Box,bool bPawns)
        {
            FVector Min=Box.Min+FVector(1.);
            const FVector Max=Box.Max-FVector(1.);
            // Terrain can be up to one lattice cell above a freely placed footing.
            if(!bPawns)Min.Z=FMath::Max(Min.Z,20.01);
            if(Min.X>=Max.X||Min.Y>=Max.Y||Min.Z>=Max.Z)return false;
            const FVector Center=Pose.TransformPosition((Min+Max)*.5);
            const auto Hull=FCollisionShape::MakeBox((Max-Min)*.5);
            return bPawns?World.OverlapAnyTestByObjectType(Center,Pose.GetRotation(),
                FCollisionObjectQueryParams(ECC_Pawn),Hull,Query)
                :World.OverlapBlockingTestByChannel(Center,Pose.GetRotation(),ECC_Pawn,Hull,Query);
        };
        // On clear ground both broad queries finish before per-part checks.
        const bool Pawns=Blocked(Shape.Bounds,true),Scenery=Blocked(Shape.Bounds,false);
        if(Pawns||Scenery)
            for(const FBox& Box:Shape.Boxes)
                if((Pawns&&Blocked(Box,true))||(Scenery&&Blocked(Box,false)))return false;
        return true;
    }
}
