// Conservative convex envelopes for static dressing contacts. They are query data only:
// no simulated bodies, new collision channels, or per-frame physics are created.
#include "Chaos/Convex.h"
#include "Chaos/GJK.h"

namespace DungeonDressing
{
static TSharedPtr<Chaos::FConvex> PropHull(const TArray<Chaos::FConvex::FVec3Type>& Points)
{
    if(Points.Num()<4)return nullptr;
    TArray<Chaos::FConvex::FPlaneType> Planes;
    TArray<TArray<int32>> Faces;
    TArray<Chaos::FConvex::FVec3Type> Vertices;
    Chaos::FConvex::FAABB3Type Bounds;
    // Keep the full hull. Simplification/plane merging can cut off scan vertices,
    // which would invalidate the non-intersection guarantee of this envelope.
    Chaos::FConvexBuilder::Build(Points,Planes,Faces,Vertices,Bounds,Chaos::FConvexBuilder::EBuildMethod::ConvexHull3);
    if(Planes.Num()<4||Vertices.Num()<4)return nullptr;
    return MakeShared<Chaos::FConvex>(MoveTemp(Planes),MoveTemp(Faces),MoveTemp(Vertices));
}

struct FPropGeometry
{
    TSharedPtr<Chaos::FConvex> Hull;
    TArray<Chaos::FTriangleMeshImplicitObjectPtr> Triangles;
};

struct FPropBody
{
    TSharedPtr<Chaos::FConvex> Hull;
    FBox RelativeBounds=FBox(ForceInit);
    FVector Origin=FVector::ZeroVector;

    bool SetPose(const FPropGeometry& Geometry,const FTransform& Pose)
    {
        TArray<Chaos::FConvex::FVec3Type> Points;
        RelativeBounds=FBox(ForceInit);Origin=Pose.GetTranslation();
        for(const auto& Vertex:Geometry.Hull->GetVertices())
        {
            const FVector P=Pose.TransformVector(FVector(Vertex));
            Points.Add(Chaos::FConvex::FVec3Type(P));RelativeBounds+=P;
        }
        Hull=PropHull(Points);
        return Hull.IsValid();
    }
    FBox Bounds() const {return RelativeBounds.ShiftBy(Origin);}
    FVector Center() const {return Origin+RelativeBounds.GetCenter();}
};

static bool PropsTouch(const FPropBody& A,const FPropBody& B,double Margin=.08)
{
    if(!A.Bounds().ExpandBy(Margin).Intersect(B.Bounds()))return false;
    return Chaos::GJKIntersection(*A.Hull,*B.Hull,
        Chaos::FRigidTransform3(B.Origin-A.Origin,FQuat::Identity),Margin);
}

struct FSettledProp
{
    FPropBody Body;
    FTransform Transform;
    TSharedPtr<FPropGeometry> Geometry;
    EProp Type=EProp::Barrel;
    int32 Module=INDEX_NONE,Cluster=INDEX_NONE,Item=INDEX_NONE,Depth=0;
    double FloorZ=0;
};

static bool PropSurface(const FSettledProp& Prop,const FVector& Start,const FVector& End,FVector& Hit,FVector& Normal)
{
    const FVector From=Prop.Transform.InverseTransformPosition(Start),To=Prop.Transform.InverseTransformPosition(End);
    const FVector Delta=To-From;const double Length=Delta.Size();
    if(Length<UE_SMALL_NUMBER)return false;
    double Nearest=DBL_MAX;bool Found=false;
    for(const auto& Tri:Prop.Geometry->Triangles)if(Tri)
    {
        Chaos::FReal Time;Chaos::FVec3 Position,N;int32 Face;
        if(!Tri->Raycast(From,Delta/Length,Length,0,Time,Position,N,Face)||Time>=Nearest)continue;
        Nearest=Time;Found=true;Hit=Prop.Transform.TransformPosition(Position);
        Normal=Prop.Transform.TransformVectorNoScale(FVector(N)/Prop.Transform.GetScale3D()).GetSafeNormal();
    }
    return Found;
}

static bool SupportSurrounds(const FVector& Center,const TArray<FVector>& Contacts)
{
    TArray<double> Angles;
    for(const FVector& P:Contacts)
        if(FVector::DistSquared2D(P,Center)>4)Angles.Add(FMath::Atan2(P.Y-Center.Y,P.X-Center.X));
    if(Angles.Num()<3)return false;
    Angles.Sort();
    // A gap >= 180 degrees means all contacts lie on one side of the centre.
    double Gap=Angles[0]+2*PI-Angles.Last();
    for(int32 I=1;I<Angles.Num();++I)Gap=FMath::Max(Gap,Angles[I]-Angles[I-1]);
    return Gap<PI-.025;
}
}
