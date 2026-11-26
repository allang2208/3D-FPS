#include "VillageDefenseFootprint.h"
#include "VillageBuildDefense.h"
#include "VoxelBuildPrefabActor.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "Components/StaticMeshComponent.h"
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
            const FBox Travel(FVector(-263.,-9.,0.),FVector(263.,9.,958.));
            Shape.Boxes.Add(Travel);
            Shape.Bounds+=Travel;
        }
        return Shape;
    }

    static const FShape& Ballista()
    {
        // Local centimetres from the deployed base, stock, windlass, limbs, cord and loaded bolt.
        // In particular the nose and limbs can project above a parapet while the pedestal sits behind it.
        static const FShape Shape=[]()
        {
            FShape S;
            S.Boxes={
                FBox(FVector(-87,-79,0),FVector(75,82,15)),
                FBox(FVector(-44,-40,15),FVector(35,40,70)),
                FBox(FVector(-18,-26,70),FVector(10,26,133)),
                FBox(FVector(-167,-12,71),FVector(-60,12,122)),
                FBox(FVector(-65,-12,96),FVector(84,12,166)),
                FBox(FVector(17,-135,128),FVector(82,135,159)),
                FBox(FVector(-140,-98,96),FVector(21,98,141)),
                FBox(FVector(80,-23,146),FVector(197,23,195)),
                FBox(FVector(197,-12,182),FVector(268,12,217))};
            for(const FBox& Box:S.Boxes)S.Bounds+=Box;
            return S;
        }();
        return Shape;
    }

    FBox2D SiegeBase(FName Recipe)
    {
        if(Recipe==VillageBuildDefense::OilPot)return FBox2D(FVector2D(-79,-77),FVector2D(79,77));
        return Recipe==VillageBuildDefense::Trebuchet
            ? FBox2D(FVector2D(-256,-176),FVector2D(231,176))
            : FBox2D(FVector2D(-87,-82),FVector2D(87,82));
    }

    const FShape& Siege(FName Recipe)
    {
        if(Recipe==VillageBuildDefense::OilPot)
        {
            static const FShape Kettle=[](){
                FShape S;
                S.Boxes={FBox(FVector(-79,-77,0),FVector(79,77,10)),
                    FBox(FVector(-65,-65,10),FVector(65,65,96)),
                    FBox(FVector(-32,-91,76),FVector(32,91,98))};
                for(const FBox& Box:S.Boxes)S.Bounds+=Box;
                return S;
            }();
            return Kettle;
        }
        if(Recipe==VillageBuildDefense::Ballista)return Ballista();
        static const FShape Trebuchet=[]()
        {
            FShape S;
            auto Add=[&](double Back,double Front,double HalfWidth,double Bottom,double Top)
            {
                const FBox Box(FVector(Back,-HalfWidth,Bottom),FVector(Front,HalfWidth,Top));
                S.Boxes.Add(Box);
                S.Bounds+=Box;
            };
            // Fixed frame. The upright tapers above the chassis, leaving the corners clear.
            Add(-256,231,176,0,35);
            Add(-256,224,173,35,120);
            Add(-238,162,153,120,195);
            Add(-158,108,135,195,275);
            Add(-70,50,116,275,330);
            // Separate central envelope swept by ArmPose, its counterweight, sling and loaded stone.
            // Bands enclose the source meshes over a complete 7.8 s animation with sampling clearance.
            Add(-398,143,48,19,100);
            Add(-432,166,48,80,175);
            Add(-454,164,48,155,275);
            Add(-456,152,48,255,395);
            Add(-449,28,32,375,495);
            Add(-418,29,25,475,595);
            Add(-357,30,20,575,675);
            Add(-273,89,20,655,730);
            Add(-172,89,20,710,758);
            return S;
        }();
        return Trebuchet;
    }

    const FShape* SiegeRoof(const UPrimitiveComponent* Surface)
    {
        const auto* Body=Cast<UStaticMeshComponent>(Surface);
        const auto* Section=Body?Cast<AVillageDefenseSection>(Body->GetOwner()):nullptr;
        if(!Section || !Body->ComponentHasTag(TEXT("Traversal.FixedStructure")))return nullptr;
        if(const auto* Gate=Cast<AHighVillageGate>(Section))
        {
            if(Body!=Gate->GetStonePortal())return nullptr;
        }
        else
        {
            const auto* Holder=Cast<AVoxelBuildPrefabActor>(Section->GetAttachParentActor());
            if(!Holder || Holder->PrefabId()!=VillageBuildDefense::HighTower || Body!=Section->GetMasonry())return nullptr;
        }
        const UStaticMesh* Mesh=Body->GetStaticMesh();
        if(!Mesh || !Mesh->GetBodySetup())return nullptr;
        static TMap<TWeakObjectPtr<const UStaticMesh>,FShape> Decks;
        if(const auto* Cached=Decks.Find(Mesh))return Cached->Boxes.IsEmpty()?nullptr:Cached;
        FShape& Deck=Decks.Add(Mesh);
        // Both gate variants and the tower author their roof as four horizontal slab boxes.
        // Find the highest broad slabs, excluding railings, stair ramps and coping stones.
        for(const FKBoxElem& Hull:Mesh->GetBodySetup()->AggGeom.BoxElems)
        {
            if(!Hull.Rotation.IsNearlyZero() || Hull.X<120. || Hull.Y<120. || Hull.Z>40.)continue;
            const FVector Half=FVector(Hull.X,Hull.Y,Hull.Z)*.5;
            const FBox Slab(Hull.Center-Half,Hull.Center+Half);
            if(!Deck.Boxes.IsEmpty() && Slab.Max.Z<Deck.Bounds.Max.Z-.1)continue;
            if(Deck.Boxes.IsEmpty() || Slab.Max.Z>Deck.Bounds.Max.Z+.1)
            {
                Deck.Boxes.Reset();
                Deck.Bounds=FBox(ForceInit);
            }
            Deck.Boxes.Add(Slab);
            Deck.Bounds+=Slab;
        }
        return Deck.Boxes.IsEmpty()?nullptr:&Deck;
    }

    bool RoofOpening(const FShape& Deck,FBox2D& Opening)
    {
        // Two full-width slabs and the two returns surround the authored stair opening.
        const FBox2D Outer(FVector2D(Deck.Bounds.Min),FVector2D(Deck.Bounds.Max));
        Opening=Outer;
        for(const FBox& Slab:Deck.Boxes)
        {
            if(Slab.Min.X<=Outer.Min.X+.1 && Slab.Max.X>=Outer.Max.X-.1)
            {
                if(Slab.Min.Y<=Outer.Min.Y+.1)Opening.Min.Y=FMath::Max(Opening.Min.Y,Slab.Max.Y);
                if(Slab.Max.Y>=Outer.Max.Y-.1)Opening.Max.Y=FMath::Min(Opening.Max.Y,Slab.Min.Y);
            }
            else
            {
                if(Slab.Min.X<=Outer.Min.X+.1)Opening.Min.X=FMath::Max(Opening.Min.X,Slab.Max.X);
                if(Slab.Max.X>=Outer.Max.X-.1)Opening.Max.X=FMath::Min(Opening.Max.X,Slab.Min.X);
            }
        }
        return Opening.Min.X>Outer.Min.X && Opening.Min.Y>Outer.Min.Y &&
            Opening.Max.X<Outer.Max.X && Opening.Max.Y<Outer.Max.Y &&
            Opening.Max.X>Opening.Min.X && Opening.Max.Y>Opening.Min.Y;
    }

    bool TrebuchetFitsDeck(const FShape& Deck,const FTransform& Frame,const FTransform& Pose)
    {
        const FBox2D Base=SiegeBase(VillageBuildDefense::Trebuchet);
        const FVector2D Half=Base.GetExtent();
        const FVector2D Centre(Frame.InverseTransformPosition(Pose.TransformPosition(FVector(Base.GetCenter(),0.))));
        const FVector2D X(Frame.InverseTransformVector(Pose.TransformVector(FVector(Half.X,0,0))));
        const FVector2D Y(Frame.InverseTransformVector(Pose.TransformVector(FVector(0,Half.Y,0))));
        const FVector2D Radius(FMath::Abs(X.X)+FMath::Abs(Y.X),FMath::Abs(X.Y)+FMath::Abs(Y.Y));
        if(Centre.X-Radius.X<Deck.Bounds.Min.X || Centre.X+Radius.X>Deck.Bounds.Max.X ||
            Centre.Y-Radius.Y<Deck.Bounds.Min.Y || Centre.Y+Radius.Y>Deck.Bounds.Max.Y)return false;
        FBox2D Hatch;
        if(!RoofOpening(Deck,Hatch))return true;
        // All support samples may land on stone even when a long chassis bridges a stairwell.
        // Project both rectangles onto their four separating axes; edge contact is allowed.
        const FVector2D Gap=Centre-Hatch.GetCenter(),Hole=Hatch.GetExtent();
        for(const FVector2D Axis:{FVector2D(1,0),FVector2D(0,1),FVector2D(-X.Y,X.X),FVector2D(-Y.Y,Y.X)})
        {
            const double Span=FMath::Abs(X.Dot(Axis))+FMath::Abs(Y.Dot(Axis))+
                Hole.X*FMath::Abs(Axis.X)+Hole.Y*FMath::Abs(Axis.Y);
            if(FMath::Abs(Gap.Dot(Axis))>=Span)return true;
        }
        return false;
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

    bool IsClear(UWorld& World,const FShape& Shape,const FTransform& Pose,const AActor* Builder,TConstArrayView<AActor*> Replaced,double GroundAllowance)
    {
        if(Shape.Boxes.IsEmpty())return false;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageDefenseClearance),false,Builder);
        for(const AActor* Actor:Replaced)Query.AddIgnoredActor(Actor);
        // Test the complete host while allowing neighbouring pieces to meet flush.
        const auto Blocked=[&](const FBox& Box,bool bPawns)
        {
            FVector Min=Box.Min+FVector(1.);
            const FVector Max=Box.Max-FVector(1.);
            // Terrain can be up to one lattice cell above a freely placed footing.
            if(!bPawns)Min.Z=FMath::Max(Min.Z,GroundAllowance);
            if(Min.X>=Max.X||Min.Y>=Max.Y||Min.Z>=Max.Z)return false;
            const FVector Center=Pose.TransformPosition((Min+Max)*.5);
            const auto Hull=FCollisionShape::MakeBox((Max-Min)*.5*Pose.GetScale3D().GetAbs());
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
