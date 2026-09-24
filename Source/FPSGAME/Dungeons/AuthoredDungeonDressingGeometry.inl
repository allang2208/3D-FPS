// Queries the cooked triangle data directly: staged actors intentionally have collision
// disabled, and some visible rails/fixtures have NoCollision. Neither means empty space.
#include "PhysicsEngine/BodySetup.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Chaos/Box.h"
#include "AuthoredDungeonDressingBodies.inl"

namespace DungeonDressing
{
struct FGeometry
{
    FTransform Transform;
    FBox Bounds;
    TArray<Chaos::FTriangleMeshImplicitObjectPtr> Triangles;
    FString Name;
    int32 Module = INDEX_NONE;
    bool Floor = false, Wall = false;
};

// A box wholly inside a closed column need not cross any triangles. Count oriented
// surface crossings as well as overlaps, including meshes containing disconnected solids.
static bool InsideSolid(const Chaos::FTriangleMeshImplicitObject& Mesh,const FVector& Point)
{
    const auto& Bounds=Mesh.BoundingBox();
    for(int32 Axis=0;Axis<3;++Axis)
        if(Point[Axis]<Bounds.Min()[Axis] || Point[Axis]>Bounds.Max()[Axis]) return false;
    const double Rise=Bounds.Max().Z-Point.Z+1;
    const FVector End=Point+FVector(.013*Rise,.007*Rise,Rise);
    FBox RayBounds(ForceInit);RayBounds+=Point;RayBounds+=End;
    TArray<TPair<double,int32>> Crossings;
    Mesh.VisitTriangles(Chaos::FAABB3(RayBounds.Min,RayBounds.Max),Chaos::FRigidTransform3::Identity,
        [&](const Chaos::FTriangle& Triangle,int32,int32,int32,int32)
        {
            FVector Hit,Normal;
            if(FMath::SegmentTriangleIntersection(Point,End,Triangle[0],Triangle[1],Triangle[2],Hit,Normal))
            {
                const double Sign=FVector::DotProduct(Normal,End-Point);
                if(FMath::Abs(Sign)>UE_SMALL_NUMBER) Crossings.Emplace((Hit-Point).Size(),Sign>0?1:-1);
            }
        });
    Crossings.Sort([](const auto& A,const auto& B){return A.Key<B.Key;});
    int32 Winding=0;
    for(int32 I=0;I<Crossings.Num();)
    {
        const double Distance=Crossings[I].Key;int32 Sign=0;
        do {Sign+=Crossings[I++].Value;} while(I<Crossings.Num() && FMath::Abs(Crossings[I].Key-Distance)<.001);
        Winding+=FMath::Sign(Sign); // shared triangle edges represent one surface crossing
    }
    return Winding!=0;
}

struct FPlacementScene
{
    TArray<FGeometry> Geometry;
    TArray<FBox> FixedBoxes,Accepted;
    TSet<FIntPoint> AcceptedClusters;
    TArray<FSettledProp> Settled;
    TMap<UStaticMesh*,TSharedPtr<FPropGeometry>> PropGeometry;
    int32 StackCount=0,LeanCount=0,FallenCount=0,PlacementAttempts=0;

    bool Place(UStaticMesh* Mesh,const FObject& Part,const FObject& Module,const FTransform& Room,
        int32 ModuleIndex,FTransform& World,FString& Reason);
    bool PropBlocked(const FPropBody& Body,FString& Reason) const;
    bool FloorContact(FPropBody& Body,int32 Module,double Expected,double& Height,FString& Reason) const;
    bool StackContact(FPropBody& Body,const FSettledProp& Parent,FString& Reason) const;
    bool LeanContact(FPropBody& Body,const FSettledProp& Parent,const FVector& Direction,FString& Reason) const;

    void AddMesh(UStaticMesh* Mesh,const FTransform& Transform,int32 Module,const FString& Name)
    {
        FGeometry G;G.Transform=Transform;G.Bounds=Mesh->GetBoundingBox().TransformBy(Transform);
        G.Module=Module;G.Name=Name;
        // Only authored walkable slabs are supports. Stair treads, rail tops, machine
        // bases, crates and fluid sheets must never become a new floor for a decoration.
        G.Floor=Module!=INDEX_NONE && (Name.EndsWith(TEXT("_Floors")) || Name.EndsWith(TEXT("_Dock")) || Name.EndsWith(TEXT("_GalleryDeck")));
        G.Wall=Module!=INDEX_NONE && (Name.EndsWith(TEXT("_Shell")) || Name.EndsWith(TEXT("_Tiles")) || Name.EndsWith(TEXT("_Frames")));
        if(auto* Body=Mesh->GetBodySetup()) {Body->CreatePhysicsMeshes();G.Triangles=Body->TriMeshGeometries;}
        Geometry.Add(MoveTemp(G));
    }

    void AddPlacedActors(UWorld* World,const AActor* Generator,const FBox& LayoutBounds)
    {
        for(TActorIterator<AActor> It(World);It;++It)
        {
            AActor* Actor=*It;
            if(Actor==Generator || Actor->GetOwner()==Generator || Actor->IsA<APawn>() || Actor->IsHidden()) continue;
            TInlineComponentArray<UStaticMeshComponent*> Meshes;Actor->GetComponents(Meshes);
            for(auto* C:Meshes)
            {
                if(!C->IsVisible() || !C->GetStaticMesh() || !C->Bounds.GetBox().Intersect(LayoutBounds)) continue;
                if(auto* Instances=Cast<UInstancedStaticMeshComponent>(C))
                {
                    for(int32 I=0;I<Instances->GetInstanceCount();++I)
                    {
                        FTransform T;Instances->GetInstanceTransform(I,T,true);
                        if(C->GetStaticMesh()->GetBoundingBox().TransformBy(T).Intersect(LayoutBounds))
                            AddMesh(C->GetStaticMesh(),T,INDEX_NONE,C->GetStaticMesh()->GetName());
                    }
                }
                else AddMesh(C->GetStaticMesh(),C->GetComponentTransform(),INDEX_NONE,C->GetStaticMesh()->GetName());
            }
        }
    }

    bool Trace(const FVector& Start,const FVector& End,int32 Module,bool Wall,FVector& Hit,FVector& Normal) const
    {
        double Nearest=DBL_MAX;bool Found=false;
        FBox Segment(ForceInit);Segment+=Start;Segment+=End;
        for(const auto& G:Geometry)
        {
            if(G.Module!=Module || !(Wall?G.Wall:G.Floor) || !G.Bounds.Intersect(Segment)) continue;
            const FVector From=G.Transform.InverseTransformPosition(Start),To=G.Transform.InverseTransformPosition(End);
            const FVector Delta=To-From;const double Length=Delta.Size();
            if(Length<UE_SMALL_NUMBER) continue;
            for(const auto& Tri:G.Triangles) if(Tri)
            {
                Chaos::FReal Time;Chaos::FVec3 Position,LocalNormal;int32 Face;
                if(!Tri->Raycast(From,Delta/Length,Length,0,Time,Position,LocalNormal,Face)) continue;
                const FVector WorldPoint=G.Transform.TransformPosition(Position);
                const double Distance=FVector::DistSquared(Start,WorldPoint);
                if(Distance>=Nearest) continue;
                Normal=G.Transform.TransformVectorNoScale(FVector(LocalNormal)/G.Transform.GetScale3D()).GetSafeNormal();
                Hit=WorldPoint;Nearest=Distance;Found=true;
            }
        }
        return Found;
    }

    bool Blocked(const FBox& Box,FString& Reason) const
    {
        for(const FBox& Other:Accepted) if(Other.ExpandBy(3).Intersect(Box)) {Reason=TEXT("another_prop");return true;}
        for(const auto& Other:Settled) if(Other.Body.Bounds().ExpandBy(.1).Intersect(Box)) {Reason=TEXT("another_prop");return true;}
        for(const FBox& Other:FixedBoxes) if(Other.Intersect(Box)) {Reason=TEXT("fixed_prop");return true;}
        for(const auto& G:Geometry)
        {
            if(!G.Bounds.Intersect(Box)) continue;
            // Missing cooked geometry is not permission to overlap the visible mesh.
            if(G.Triangles.IsEmpty()) {Reason=TEXT("unresolved_geometry:")+G.Name;return true;}
            const FBox LocalBox=Box.TransformBy(G.Transform.Inverse());
            const Chaos::TBox<Chaos::FReal,3> Shape(LocalBox.Min,LocalBox.Max);
            for(const auto& Tri:G.Triangles) if(Tri &&
                (Tri->OverlapGeom(Shape,Chaos::FRigidTransform3::Identity,0) || InsideSolid(*Tri,LocalBox.GetCenter())))
            {Reason=TEXT("scene_geometry:")+G.Name;return true;}
        }
        return false;
    }

    bool Place(const FBox& MeshBounds,const FObject& Part,const FObject& Module,const FTransform& Room,
        int32 ModuleIndex,FTransform& World,FString& Reason)
    {
        bool Wall=false;Part->TryGetBoolField(TEXT("dressing_wall"),Wall);
        int32 Cluster=INDEX_NONE;Part->TryGetNumberField(TEXT("dressing_cluster"),Cluster);
        bool Primary=false;Part->TryGetBoolField(TEXT("dressing_primary"),Primary);
        if(!Wall && Cluster!=INDEX_NONE && !Primary && !AcceptedClusters.Contains(FIntPoint(ModuleIndex,Cluster)))
        {Reason=TEXT("cluster_primary_rejected");return false;}
        const FVector WallNormal=Wall?Room.TransformVectorNoScale(Vector(Part,TEXT("dressing_normal"))).GetSafeNormal():FVector::ZeroVector;
        FBox Bounds=MeshBounds.TransformBy(World);
        if(!Wall)
        {
            // The authored floor height restricts the search to this storey (12 cm).
            // An absent gallery cannot fall through to the ground floor below it.
            FVector SupportPosition=Vector(Part,TEXT("position"));
            Part->TryGetNumberField(TEXT("dressing_base_z"),SupportPosition.Z);
            const double Expected=Room.TransformPosition(SupportPosition).Z;
            double Low=DBL_MAX,High=-DBL_MAX;
            const FVector Center=Bounds.GetCenter(),Extent=Bounds.GetExtent();
            for(int32 X=-1;X<=1;++X) for(int32 Y=-1;Y<=1;++Y)
            {
                const FVector Sample(Center.X+Extent.X*.94*X,Center.Y+Extent.Y*.94*Y,Expected);
                FVector Hit,Normal;
                if(!Trace(Sample+FVector(0,0,12),Sample-FVector(0,0,12),ModuleIndex,false,Hit,Normal) || Normal.Z<.985)
                {Reason=TEXT("missing_or_sloping_support");return false;}
                Low=FMath::Min(Low,Hit.Z);High=FMath::Max(High,Hit.Z);
            }
            if(High-Low>1.5) {Reason=TEXT("uneven_support");return false;}
            // Actual asset bounds handle an off-centre pivot and imported build scale.
            World.AddToTranslation(FVector(0,0,High+.2-Bounds.Min.Z));
        }
        else
        {
            const FVector N=WallNormal;
            const FVector Tangent(-N.Y,N.X,0),Center=Bounds.GetCenter(),E=Bounds.GetExtent();
            const double Depth=FMath::Abs(N.X)*E.X+FMath::Abs(N.Y)*E.Y;
            const double Span=FMath::Abs(Tangent.X)*E.X+FMath::Abs(Tangent.Y)*E.Y;
            double Near=-DBL_MAX,Far=DBL_MAX;
            for(int32 I=-1;I<=1;++I)
            {
                const FVector Sample=Center+Tangent*(Span*.65*I)+FVector(0,0,I==0?0:E.Z*.4);
                FVector Hit,Normal;
                if(!Trace(Sample+N*8,Sample-N*(Depth+40),ModuleIndex,true,Hit,Normal) || FVector::DotProduct(Normal,N)<.9)
                {Reason=TEXT("missing_wall_support");return false;}
                const double Plane=FVector::DotProduct(Hit,N);Near=FMath::Max(Near,Plane);Far=FMath::Min(Far,Plane);
            }
            if(Near-Far>3) {Reason=TEXT("uneven_wall_support");return false;}
            World.AddToTranslation(N*(Near+.3-(FVector::DotProduct(Center,N)-Depth)));
        }
        Bounds=MeshBounds.TransformBy(World);
        const FBox LocalBounds=MeshBounds.TransformBy(World.GetRelativeTransform(Room));
        if(!Fits(LocalBounds,Module,Profile(Module),{},Wall))
        {Reason=TEXT("reserved_space_after_snap");return false;}
        // Side/top clearance includes thin rails and overhead pipes. Do not expand
        // downward across the support plane, or a correct floor contact would fail.
        const FVector Margin=Wall?FVector(FMath::Abs(WallNormal.Y)*3+.05,FMath::Abs(WallNormal.X)*3+.05,2):FVector(3,3,2);
        const FBox Clearance(Bounds.Min-FVector(Margin.X,Margin.Y,Wall?2:-.05),Bounds.Max+Margin);
        if(Blocked(Clearance,Reason)) return false;
        Accepted.Add(Bounds);
        if(!Wall && Primary && Cluster!=INDEX_NONE) AcceptedClusters.Add(FIntPoint(ModuleIndex,Cluster));
        return true;
    }
};
}
#include "AuthoredDungeonDressingSettlement.inl"
