#include "ProductionToolComponent.h"
#include "RuneboundHammerTuning.h"
#include "../FPSGAMECharacter.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
constexpr int32 Arcs=6,Steps=24,Sides=5,Rings=Steps+1;
UE::Geometry::FDynamicMesh3 MakeLightning()
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    auto* UV=Mesh.Attributes()->PrimaryUV();auto* Normals=Mesh.Attributes()->PrimaryNormals();
    for(int32 A=0;A<Arcs;++A)
    {
        const int32 Base=A*Rings*Sides;
        for(int32 I=0;I<Rings;++I)for(int32 J=0;J<Sides;++J)
        {
            Mesh.AppendVertex(FVector3d(I*.01,J*.01,A*.01));
            UV->AppendElement(FVector2f(float(I)/Steps,float(J)/Sides));
            Normals->AppendElement(FVector3f(0.f,0.f,1.f));
        }
        for(int32 I=0;I<Steps;++I)for(int32 J=0;J<Sides;++J)
        {
            const int32 V=Base+I*Sides+J,N=Base+I*Sides+(J+1)%Sides;
            for(const FIndex3i& T:{FIndex3i(V,N,V+Sides),FIndex3i(N,N+Sides,V+Sides)})
            {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
        }
    }
    return Mesh;
}
}

void UProductionToolComponent::UpdateFinalTollLightning(float Delta,bool Equipped)
{
    const auto* Head=FinalTollLightningHead.Get();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    auto* PC=Pawn?UGameplayStatics::GetPlayerController(Pawn,0):nullptr;
    const auto* ViewerCamera=PC?PC->PlayerCameraManager.Get():nullptr;
    const bool Show=Equipped&&bFinalTollVisual&&Head&&Head->IsVisible()&&!Head->bHiddenInGame&&ViewerCamera&&
        FVector::DistSquared(ViewerCamera->GetCameraLocation(),Head->GetComponentLocation())<FMath::Square(3500.f);
    if(!Show){if(FinalTollLightningMesh)FinalTollLightningMesh->SetVisibility(false);return;}
    if(!FinalTollLightningMesh)
    {
        auto* Material=Cast<UMaterialInterface>(FSoftObjectPath(RuneboundHammer::FinalTollLightning).ResolveObject());
        if(!Material)return; // Existing equipment streamable handle owns this resource.
        FinalTollLightningMesh=NewObject<UDynamicMeshComponent>(Pawn);
        FinalTollLightningMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        FinalTollLightningMesh->SetGenerateOverlapEvents(false);FinalTollLightningMesh->SetCanEverAffectNavigation(false);
        FinalTollLightningMesh->SetCastShadow(false);FinalTollLightningMesh->SetReceivesDecals(false);
        FinalTollLightningMesh->bVisibleInRayTracing=false;FinalTollLightningMesh->bAffectDistanceFieldLighting=false;
        FinalTollLightningMesh->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
        FinalTollLightningMesh->RegisterComponent();FinalTollLightningMesh->SetMesh(MakeLightning());
        FinalTollLightningMID=UMaterialInstanceDynamic::Create(Material,this);
        FinalTollLightningMesh->SetMaterial(0,FinalTollLightningMID);
    }
    FinalTollLightningMesh->SetVisibility(true);
    // Follow the actual selected head every frame; only bolt shape is 30 Hz.
    FinalTollLightningMesh->SetWorldTransform(Head->GetComponentTransform());
    FinalTollLightningMID->SetScalarParameterValue(TEXT("Strength"),.55f+.65f*RuneboundVisual);
    FinalTollLightningRefresh-=Delta;if(FinalTollLightningRefresh>0.f)return;
    FinalTollLightningRefresh=1.f/30.f;
    const float Time=float(FMath::Fmod(RuneboundClock(),1200.));
    const FBox Box=Head->GetStaticMesh()->GetBoundingBox();
    const FVector Extent=Box.GetExtent(),Center=Box.GetCenter();
    FinalTollLightningMesh->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& Mesh)
    {
        for(int32 A=0;A<Arcs;++A)
        {
            FVector Points[Rings];
            const float Beat=Time*(A<2?7.5f:6.f)+A*.37f;
            const float Pulse=FMath::Clamp((.63f-FMath::Frac(Beat))*9.f,0.f,1.f);
            const float Seed=FMath::FloorToFloat(Beat)*3.71f+A*2.13f;
            for(int32 I=0;I<Rings;++I)
            {
                const float U=float(I)/Steps,Angle=Seed*.53f+U*PI*1.55f;
                const float Jitter=.65f*FMath::Sin(I*2.31f+Seed)+.32f*FMath::Sin(I*5.17f-Seed);
                if(A<2)
                    Points[I]=Center+FVector((A==0?-1.f:1.f)*Extent.X*.64f+FMath::Sin(Angle*2.f)*1.4f+Jitter,
                        FMath::Cos(Angle)*(Extent.Y+1.2f)+Jitter*.45f,FMath::Sin(Angle)*(Extent.Z+1.0f));
                else if(A<4)
                    Points[I]=FVector(FMath::Cos(Angle+A*PI)*(2.8f+Jitter*.25f),
                        FMath::Sin(Angle+A*PI)*(2.8f+Jitter*.25f),-6.f-U*29.f+Jitter);
                else
                    Points[I]=Center+FVector((U*2.f-1.f)*Extent.X*.95f,
                        (A==4?-1.f:1.f)*(Extent.Y+1.2f)+Jitter,
                        FMath::Sin(U*PI)*(Extent.Z+1.4f)+Jitter*.6f);
            }
            for(int32 I=0;I<Rings;++I)
            {
                const FVector Tangent=(Points[FMath::Min(I+1,Steps)]-Points[FMath::Max(I-1,0)]).GetSafeNormal();
                FVector X,Y;Tangent.FindBestAxisVectors(X,Y);
                const float U=float(I)/Steps,Radius=(.035f+.018f*(A<2))*Pulse*FMath::Sin(U*PI);
                for(int32 J=0;J<Sides;++J)
                {
                    const float Angle=J*2.f*PI/Sides;
                    Mesh.SetVertex(A*Rings*Sides+I*Sides+J,FVector3d(Points[I]+Radius*(X*FMath::Cos(Angle)+Y*FMath::Sin(Angle))));
                }
            }
        }
    },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions);
}
