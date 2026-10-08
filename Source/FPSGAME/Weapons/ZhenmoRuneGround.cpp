#include "ZhenmoRuneComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

namespace ZhenmoGround
{
    // One conforming grid: metre spacing around the readable seal, coarser at
    // the perimeter. All coordinates share world cells, so movement reuses hits.
    constexpr int32 Axis[]={-18,-14,-10,-7,-5,-4,-3,-2,-1,0,1,2,3,4,5,7,10,14,18};
    constexpr int32 Side=UE_ARRAY_COUNT(Axis),Count=Side*Side;
    constexpr float CellCM=100.f,LiftCM=8.f;
    constexpr int32 TraceBudget=16,CacheExtent=20;
    constexpr double SampleInterval=.05,MeshInterval=.1;
    struct FSample
    {
        FVector Point=FVector::ZeroVector,Normal=FVector::UpVector;
        double At=-100.;
        bool Valid=false;
    };
}

struct FZhenmoGroundCache
{
    TMap<FIntPoint,ZhenmoGround::FSample> Samples;
    TArray<int32> NearFirst;
    FIntPoint Center=FIntPoint::ZeroValue;
    FVector Normal=FVector::UpVector;
    double NextSample=0.;
    bool Dirty=true;
    FZhenmoGroundCache()
    {
        for(int32 I=0;I<ZhenmoGround::Count;++I)NearFirst.Add(I);
        NearFirst.Sort([](int32 A,int32 B)
        {
            using namespace ZhenmoGround;
            return FMath::Square(Axis[A%Side])+FMath::Square(Axis[A/Side])
                <FMath::Square(Axis[B%Side])+FMath::Square(Axis[B/Side]);
        });
    }
};

FVector UZhenmoRuneComponent::GroundMoteSlope() const
{
    const FVector N=GroundCache?GroundCache->Normal:FVector::UpVector;
    return FVector(-N.X/FMath::Max(.65,N.Z),-N.Y/FMath::Max(.65,N.Z),0.);
}

void UZhenmoRuneComponent::RefreshGround(const FVector& Feet)
{
    using namespace ZhenmoGround;
    using namespace UE::Geometry;
    if(!FieldSurface)return;
    const double Now=Clock();
    const FIntPoint Center(FMath::RoundToInt(Feet.X/CellCM),FMath::RoundToInt(Feet.Y/CellCM));
    if(!bGroundReady||!GroundCache||FMath::Abs(Feet.Z-GroundAnchor.Z)>120.f)
    {
        GroundCache=MakeShared<FZhenmoGroundCache>();
        GroundCache->Center=Center;
        GroundAnchor=FVector(Center.X*CellCM,Center.Y*CellCM,Feet.Z);
        NextGroundUpdate=0.;bGroundReady=true;
    }
    auto& Cache=*GroundCache;
    if(Cache.Center!=Center)
    {
        Cache.Center=Center;Cache.Dirty=true;
        GroundAnchor=FVector(Center.X*CellCM,Center.Y*CellCM,Feet.Z);
        // At most 41x41 retained world cells; no unbounded travel history.
        for(auto It=Cache.Samples.CreateIterator();It;++It)
            if(FMath::Abs(It.Key().X-Center.X)>CacheExtent||FMath::Abs(It.Key().Y-Center.Y)>CacheExtent)It.RemoveCurrent();
        if(const auto* Sample=Cache.Samples.Find(Center);Sample&&Sample->Valid)Cache.Normal=Sample->Normal;
    }
    if(Now>=Cache.NextSample)
    {
        Cache.NextSample=Now+SampleInterval;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(ZhenmoGroundCached),true,GetOwner());
        FCollisionObjectQueryParams Objects;
        Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
        int32 Budget=TraceBudget;
        TArray<FHitResult> Hits;
        // Missing cells first, stale cells second; centre first in either pass.
        for(int32 Pass=0;Pass<2&&Budget>0;++Pass)for(const int32 Index:Cache.NearFirst)
        {
            const int32 X=Axis[Index%Side],Y=Axis[Index/Side];
            const FIntPoint Key=Center+FIntPoint(X,Y);
            const auto* Existing=Cache.Samples.Find(Key);
            if((Pass==0&&Existing)||(Pass==1&&!Existing))continue;
            const double TTL=FMath::Max(FMath::Abs(X),FMath::Abs(Y))<=5?1.25:4.;
            if(Existing&&Now-Existing->At<TTL)continue;
            const FVector XY(Key.X*CellCM,Key.Y*CellCM,Feet.Z);
            const FVector Slope=GroundMoteSlope();
            const float ExpectedZ=Existing&&Existing->Valid?Existing->Point.Z:
                Feet.Z+FVector::DotProduct(XY-Feet,Slope);
            const FVector Sample(XY.X,XY.Y,ExpectedZ);
            Hits.Reset();
            GetWorld()->LineTraceMultiByObjectType(Hits,Sample+FVector(0,0,120),Sample-FVector(0,0,350),Objects,Query);
            FSample Fresh;Fresh.Point=Sample;Fresh.At=Now;
            for(const auto& Hit:Hits)
            {
                const auto* Actor=Hit.GetActor();
                if(!Hit.bBlockingHit||!Actor||Actor->IsA<APawn>()||Cast<USkinnedMeshComponent>(Hit.GetComponent())
                    ||Actor->FindComponentByClass<UFPSCombatHealthComponent>()||Hit.ImpactNormal.Z<.65f)continue;
                Fresh.Point=Hit.ImpactPoint;Fresh.Normal=Hit.ImpactNormal;Fresh.Valid=true;break;
            }
            if(X==0&&Y==0&&Fresh.Valid)Cache.Normal=Fresh.Normal;
            const bool Changed=!Existing||Existing->Valid!=Fresh.Valid
                ||FVector::DistSquared(Existing->Point,Fresh.Point)>.25f
                ||FVector::DotProduct(Existing->Normal,Fresh.Normal)<.999f;
            Cache.Samples.Add(Key,Fresh);Cache.Dirty|=Changed;
            if(--Budget<=0)break;
        }
    }
    if(!Cache.Dirty||Now<NextGroundUpdate)return;
    Cache.Dirty=false;NextGroundUpdate=Now+MeshInterval;
    FDynamicMesh3 Surface;Surface.EnableAttributes();
    bool Valid[Count]{};
    FVector Points[Count],Normals[Count];
    for(int32 Y=0;Y<Side;++Y)for(int32 X=0;X<Side;++X)
    {
        const int32 I=Y*Side+X;
        const FIntPoint Key=Center+FIntPoint(Axis[X],Axis[Y]);
        const auto* Sample=Cache.Samples.Find(Key);
        Valid[I]=Sample&&Sample->Valid;
        Points[I]=Sample?Sample->Point:FVector(Key.X*CellCM,Key.Y*CellCM,Feet.Z);
        Normals[I]=Sample?Sample->Normal:FVector::UpVector;
        Surface.AppendVertex(FVector3d(Points[I]+Normals[I]*LiftCM-GroundAnchor));
        Surface.Attributes()->PrimaryNormals()->AppendElement(FVector3f(Normals[I]));
        Surface.Attributes()->PrimaryUV()->AppendElement(FVector2f(float(X)/(Side-1),float(Y)/(Side-1)));
    }
    const auto Connected=[&](int32 A,int32 B)
    {
        const FVector D=Points[B]-Points[A];
        const FVector N=(Normals[A]+Normals[B]).GetSafeNormal();
        // Continuous slopes survive; a height discontinuity across floors does
        // not. The old absolute 140 cm limit incorrectly cut long slope cells.
        return FMath::Abs(FVector::DotProduct(D,N))<=55.f&&FVector::DotProduct(Normals[A],Normals[B])>.55f;
    };
    const auto Triangle=[&](int32 A,int32 B,int32 C)
    {
        if(!Valid[A]||!Valid[B]||!Valid[C]||!Connected(A,B)||!Connected(B,C)||!Connected(C,A))return;
        const int32 T=Surface.AppendTriangle(A,B,C);
        if(T>=0)
        {
            const FIndex3i V(A,B,C);
            Surface.Attributes()->PrimaryNormals()->SetTriangle(T,V);
            Surface.Attributes()->PrimaryUV()->SetTriangle(T,V);
        }
    };
    for(int32 Y=0;Y<Side-1;++Y)for(int32 X=0;X<Side-1;++X)
    {
        const int32 A=Y*Side+X,B=A+1,C=A+Side,D=C+1;
        Triangle(A,D,B);Triangle(A,C,D);
    }
    FieldSurface->SetWorldLocation(GroundAnchor);FieldSurface->SetMesh(MoveTemp(Surface));
}
