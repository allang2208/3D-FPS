#include "FatZombiePusPool.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
double Cross2(FVector2D A, FVector2D B) { return A.X*B.Y-A.Y*B.X; }
FVector2D ClosestOnEdge(FVector2D P, FVector2D A, FVector2D B)
{
    const FVector2D Edge=B-A;
    const double T=FMath::Clamp(FVector2D::DotProduct(P-A,Edge)/FMath::Max(1.e-8,Edge.SizeSquared()),0.,1.);
    return A+Edge*T;
}
struct FPusVertex
{
    FVector Ground=FVector::ZeroVector;
    FVector Normal=FVector::UpVector;
    float Coverage=0;
    float Thickness=0;
    float Variation=0;
    float Arrival=0;
    bool Valid=false;
};
}

bool AFatZombiePusPool::TraceGround(FVector LocalXY, FVector& Ground, FVector& Normal) const
{
    const FVector Probe=GetActorTransform().TransformPosition(FVector(LocalXY.X,LocalXY.Y,0));
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FatPusGround),false,this);
    if(SourcePawn.IsValid())Query.AddIgnoredActor(SourcePawn.Get());
    TArray<FHitResult> Hits;
    GetWorld()->LineTraceMultiByObjectType(Hits,Probe+FVector(0,0,40),Probe-FVector(0,0,85),Objects,Query);
    for(const auto& Hit:Hits)
    {
        const auto* Component=Hit.GetComponent();
        if(!Component || Cast<APawn>(Hit.GetActor()) || Component->GetCollisionResponseToChannel(ECC_Pawn)!=ECR_Block)continue;
        // Reject steep faces and surfaces above/below the corpse's ground layer.
        if(Hit.ImpactNormal.Z<.85f || Hit.ImpactPoint.Z>GetActorLocation().Z+14.f || Hit.ImpactPoint.Z<GetActorLocation().Z-65.f)return false;
        // A downward projection alone would paint the far side of a nearby wall.
        TArray<FHitResult> Barriers;
        GetWorld()->LineTraceMultiByObjectType(Barriers,GetActorLocation()+FVector(0,0,7),Hit.ImpactPoint+FVector(0,0,7),Objects,Query);
        for(const auto& Barrier:Barriers)
            if(const auto* Body=Barrier.GetComponent();Body && !Cast<APawn>(Barrier.GetActor()) && Body->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block)return false;
        Ground=GetActorTransform().InverseTransformPosition(Hit.ImpactPoint);
        Normal=GetActorTransform().InverseTransformVectorNoScale(Hit.ImpactNormal).GetSafeNormal();
        return true;
    }
    return false;
}

bool AFatZombiePusPool::BuildFootprint()
{
    using namespace UE::Geometry;
    FRandomStream Random(Seed);
    const float Phase3=Random.FRandRange(0,2*PI),Phase5=Random.FRandRange(0,2*PI),Phase9=Random.FRandRange(0,2*PI);
    const float RX=Tuning.LongRadius*Random.FRandRange(.9f,1.1f);
    const float RY=Tuning.ShortRadius*Random.FRandRange(.9f,1.1f);
    const float Angle=Random.FRandRange(-PI,PI),Cos=FMath::Cos(Angle),Sin=FMath::Sin(Angle);
    auto Rotate=[&](FVector2D P){return FVector2D(P.X*Cos-P.Y*Sin,P.X*Sin+P.Y*Cos);};
    auto Radius=[&](float A){return 1.f+.13f*FMath::Sin(3*A+Phase3)+.075f*FMath::Sin(5*A+Phase5)+.035f*FMath::Sin(9*A+Phase9);};
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();Mesh.Attributes()->EnablePrimaryColors();
    auto* Normals=Mesh.Attributes()->PrimaryNormals();
    auto* UVs=Mesh.Attributes()->PrimaryUV();
    auto* Colors=Mesh.Attributes()->PrimaryColors();
    GroundTriangles.Reset();QueryRadius=0;
    auto Emit=[&](FPusVertex A,FPusVertex B,FPusVertex C)
    {
        if(!A.Valid || !B.Valid || !C.Valid)return;
        FVector Cross=FVector::CrossProduct(B.Ground-A.Ground,C.Ground-A.Ground);
        if(Cross.SizeSquared()<.001)return;
        // Do not stretch film across a stair riser or a drop between samples.
        const float HeightRange=FMath::Max3(A.Ground.Z,B.Ground.Z,C.Ground.Z)-FMath::Min3(A.Ground.Z,B.Ground.Z,C.Ground.Z);
        if(HeightRange>12.f || FMath::Abs(Cross.GetSafeNormal().Z)<.82f)return;
        if(Cross.Z>0)Swap(B,C); // UE clockwise front face; shading normals remain upward.
        const int32 Start=Mesh.VertexCount();
        for(const FPusVertex& V:{A,B,C})
        {
            const FVector Film=V.Ground+V.Normal*(.35f+V.Thickness*1.1f);
            Mesh.AppendVertex(FVector3d(Film));
            Normals->AppendElement(FVector3f(V.Normal));
            UVs->AppendElement(FVector2f(V.Ground.X/110.f,V.Ground.Y/110.f));
            Colors->AppendElement(FVector4f(V.Thickness,V.Variation,V.Arrival,V.Coverage));
            QueryRadius=FMath::Max(QueryRadius,static_cast<float>(V.Ground.Size2D()));
        }
        const int32 ID=Mesh.AppendTriangle(Start,Start+1,Start+2);
        const FIndex3i Indices(Start,Start+1,Start+2);
        Normals->SetTriangle(ID,Indices);UVs->SetTriangle(ID,Indices);Colors->SetTriangle(ID,Indices);
        GroundTriangles.Add({A.Ground,B.Ground,C.Ground,FVector(A.Coverage,B.Coverage,C.Coverage),FVector(A.Arrival,B.Arrival,C.Arrival)});
    };
    auto Patch=[&](FVector2D Center,FVector2D Extent,float Heading,int32 Sectors,int32 Rings,bool Main)
    {
        const float C=FMath::Cos(Heading),S=FMath::Sin(Heading),Variant=Random.FRand();
        auto Sample=[&](FVector2D P,float T)
        {
            FPusVertex V;
            V.Valid=TraceGround(FVector(P.X,P.Y,0),V.Ground,V.Normal);
            V.Thickness=FMath::Pow(1.f-T,.65f);
            V.Coverage=FMath::Clamp((1.f-T)/.18f,0.f,1.f);
            V.Variation=Variant;
            // Main film flows outward; each detached drop then grows from its
            // own center. Reuse the patch variation without rerolling the shape.
            V.Arrival=Main?T:(.72f+.16f*Variant+.12f*T);
            return V;
        };
        const FPusVertex Middle=Sample(Center,0);
        TArray<FPusVertex> Previous;
        for(int32 Ring=1;Ring<=Rings;++Ring)
        {
            TArray<FPusVertex> Current;Current.Reserve(Sectors);
            const float T=Ring/static_cast<float>(Rings);
            for(int32 I=0;I<Sectors;++I)
            {
                const float A=2*PI*I/Sectors;
                const float R=Main?Radius(A):1.f+.09f*FMath::Sin(3*A+Variant*6.28f);
                const FVector2D P(FMath::Cos(A)*Extent.X*R*T,FMath::Sin(A)*Extent.Y*R*T);
                Current.Add(Sample(Center+FVector2D(P.X*C-P.Y*S,P.X*S+P.Y*C),T));
            }
            for(int32 I=0;I<Sectors;++I)
            {
                const int32 Next=(I+1)%Sectors;
                if(Ring==1)Emit(Middle,Current[I],Current[Next]);
                else {Emit(Previous[I],Current[I],Current[Next]);Emit(Previous[I],Current[Next],Previous[Next]);}
            }
            Previous=MoveTemp(Current);
        }
    };
    Patch(FVector2D::ZeroVector,FVector2D(RX,RY),Angle,64,5,true);
    struct FDrop {FVector2D Center;float Radius;};
    TArray<FDrop> Placed;
    const int32 Droplets=Random.RandRange(Tuning.MinDroplets,Tuning.MaxDroplets);
    for(int32 Attempt=0;Attempt<Droplets*4 && Placed.Num()<Droplets;++Attempt)
    {
        const float A=Random.FRandRange(0,2*PI),Size=Random.FRandRange(3.f,11.f);
        const FVector2D Edge=Rotate(FVector2D(FMath::Cos(A)*RX,FMath::Sin(A)*RY)*Radius(A));
        const FVector2D Center=Edge+Edge.GetSafeNormal()*(Size*1.8f+Random.FRandRange(4.f,35.f));
        if(Placed.ContainsByPredicate([&](const FDrop& Drop){return FVector2D::Distance(Center,Drop.Center)<Size+Drop.Radius+3.f;}))continue;
        Placed.Add({Center,Size});
        Patch(Center,FVector2D(Size,Size*Random.FRandRange(.45f,.85f)),A+Angle,16,2,false);
    }
    if(GroundTriangles.IsEmpty())return false;
    Surface->SetMesh(MoveTemp(Mesh));
    return true;
}

bool AFatZombiePusPool::TouchesGround(const APawn* Target, float Spread) const
{
    if(const auto* Character=Cast<ACharacter>(Target))
        if(!Character->GetCharacterMovement()->IsMovingOnGround())return false;
    const FVector WorldFeet=Target->GetActorLocation()-FVector(0,0,Target->GetSimpleCollisionHalfHeight());
    const FVector Feet=GetActorTransform().InverseTransformPosition(WorldFeet);
    const FVector2D P(Feet.X,Feet.Y);
    const double FootRadius=FMath::Max(4.f,Target->GetSimpleCollisionRadius()*.65f);
    struct FWetVertex { FVector Ground; double Coverage; double Arrival; };
    auto TouchesTriangle=[&](const FWetVertex& VA,const FWetVertex& VB,const FWetVertex& VC)
    {
        const FVector2D A(VA.Ground.X,VA.Ground.Y),B(VB.Ground.X,VB.Ground.Y),C(VC.Ground.X,VC.Ground.Y);
        const double Denominator=Cross2(B-A,C-A);
        if(FMath::Abs(Denominator)<1.e-8)return false;
        FVector2D Contact=P;
        const double WB=Cross2(P-A,C-A)/Denominator,WC=Cross2(B-A,P-A)/Denominator;
        if(WB<0 || WC<0 || WB+WC>1)
        {
            const FVector2D AB=ClosestOnEdge(P,A,B),BC=ClosestOnEdge(P,B,C),CA=ClosestOnEdge(P,C,A);
            Contact=FVector2D::DistSquared(P,AB)<FVector2D::DistSquared(P,BC)?AB:BC;
            if(FVector2D::DistSquared(P,CA)<FVector2D::DistSquared(P,Contact))Contact=CA;
            if(FVector2D::DistSquared(P,Contact)>FootRadius*FootRadius)return false;
        }
        const double V=Cross2(Contact-A,C-A)/Denominator,W=Cross2(B-A,Contact-A)/Denominator,U=1-V-W;
        const double GroundZ=VA.Ground.Z*U+VB.Ground.Z*V+VC.Ground.Z*W;
        const double Coverage=VA.Coverage*U+VB.Coverage*V+VC.Coverage*W;
        // The transparent outer fringe is cosmetic. No hit through another floor or while airborne.
        return Coverage>.12 && FMath::Abs(Feet.Z-GroundZ)<10.f;
    };
    for(const auto& Triangle:GroundTriangles)
    {
        if(Spread<FMath::Min3(Triangle.Arrival.X,Triangle.Arrival.Y,Triangle.Arrival.Z))continue;
        const FWetVertex Vertices[]={{Triangle.A,Triangle.Coverage.X,Triangle.Arrival.X},
            {Triangle.B,Triangle.Coverage.Y,Triangle.Arrival.Y},{Triangle.C,Triangle.Coverage.Z,Triangle.Arrival.Z}};
        if(Spread>=FMath::Max3(Triangle.Arrival.X,Triangle.Arrival.Y,Triangle.Arrival.Z))
        {
            if(TouchesTriangle(Vertices[0],Vertices[1],Vertices[2]))return true;
            continue;
        }
        // Clip the triangle at the same arrival threshold as the visible front.
        // Contact against this polygon also handles a foot overlapping its edge.
        TArray<FWetVertex,TInlineAllocator<4>> Wet;
        for(int32 I=0;I<3;++I)
        {
            const FWetVertex& A=Vertices[I];
            const FWetVertex& B=Vertices[(I+1)%3];
            const bool InsideA=A.Arrival<=Spread,InsideB=B.Arrival<=Spread;
            if(InsideA)Wet.Add(A);
            if(InsideA!=InsideB)
            {
                const double T=(Spread-A.Arrival)/(B.Arrival-A.Arrival);
                Wet.Add({FMath::Lerp(A.Ground,B.Ground,T),FMath::Lerp(A.Coverage,B.Coverage,T),Spread});
            }
        }
        for(int32 I=1;I+1<Wet.Num();++I)
            if(TouchesTriangle(Wet[0],Wet[I],Wet[I+1]))return true;
    }
    return false;
}
