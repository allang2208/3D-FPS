#include "M66CorpseSurface.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "PhysicsEngine/BodyInstance.h"

bool M66CorpseSurface::FindPhysicalSupport(const USkeletalMeshComponent* Mesh,FHitResult& Out)
{
    if(!Mesh||!Mesh->GetWorld())return false;
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(M66PhysicalCorpseSupport),false,Mesh->GetOwner());
    for(const FBodyInstance* Body:Mesh->Bodies)
    {
        if(!Body||!Body->IsInstanceSimulatingPhysics()||Body->GetCollisionEnabled()==ECollisionEnabled::NoCollision)continue;
        const FBox Bounds=Body->GetBodyBounds();if(!Bounds.IsValid)continue;
        // A rotated convex's AABB bottom need not lie on its surface, nor over
        // the same stair tread as its contact. Keep the existing 2 cm contact
        // tolerance, but measure from the real shape to the traced floor.
        static constexpr double Fractions[]={.5,.25,.75,0.,1.};
        for(double X:Fractions)for(double Y:Fractions)
        {
            const FVector At(FMath::Lerp(Bounds.Min.X,Bounds.Max.X,X),FMath::Lerp(Bounds.Min.Y,Bounds.Max.Y,Y),Bounds.Max.Z+6.);
            FHitResult Hit;
            if(!Mesh->GetWorld()->LineTraceSingleByObjectType(Hit,At,FVector(At.X,At.Y,Bounds.Min.Z-6.),Objects,Query)||Hit.ImpactNormal.Z<=.5f)continue;
            // Query from outside the shape. GetDistanceToBody returns zero
            // for interior points, which alone would also accept deep overlap.
            FVector Surface;const float Distance=Body->GetDistanceToBody(Hit.ImpactPoint-FVector(0,0,4),Surface);
            if(Distance>0.f&&Distance<=6.f&&FVector::DistSquared(Surface,Hit.ImpactPoint)<=4.){Out=Hit;return true;}
        }
    }
    return false;
}

bool M66CorpseSurface::GroundAnimated(USkeletalMeshComponent* Mesh)
{
    if(!Mesh||!Mesh->GetWorld()||Mesh->IsSimulatingPhysics()||!Mesh->GetSkeletalMeshAsset())return false;
    const auto* Info=Mesh->GetSkeletalMeshAsset()->GetLODInfo(0);
    const auto* Data=Mesh->GetSkeletalMeshRenderData();
    auto* Skin=Mesh->GetSkinWeightBuffer(0);
    if(!Info||!Info->bAllowCPUAccess||!Data||Data->LODRenderData.IsEmpty()||!Skin)return false;
    const auto& LOD=Data->LODRenderData[0];
    if(LOD.GetNumVertices()==0||Skin->GetNumVertices()!=LOD.GetNumVertices())return false;
    TArray<FMatrix44f> RefToLocal;Mesh->GetCurrentRefToLocalMatrices(RefToLocal,0);
    TArray<FVector> Points;Points.Reserve(4096);FBox Bounds(ForceInit);
    const FTransform World=Mesh->GetComponentTransform();
    int32 Remaining=4096;
    for(const auto& Section:LOD.RenderSections)
    {
        if(Section.bDisabled||Section.NumVertices==0||Remaining==0)continue;
        const int32 Count=FMath::Min3(int32(Section.NumVertices),Remaining,
            FMath::Max(32,int32(int64(4096)*Section.NumVertices/LOD.GetNumVertices())));
        Remaining-=Count;
        for(int32 I=0;I<Count;++I)
        {
            const uint32 Vertex=Section.BaseVertexIndex+(Count==1?0:uint32(int64(I)*(Section.NumVertices-1)/(Count-1)));
            const FVector Point=World.TransformPosition(FVector(USkinnedMeshComponent::GetSkinnedVertexPosition(Mesh,Vertex,LOD,*Skin,RefToLocal)));
            Points.Add(Point);Bounds+=Point;
        }
    }
    if(Points.IsEmpty())return false;
    FVector Lowest[64];bool Used[64]={};const FVector Cell=Bounds.GetSize()/8.;
    for(const FVector& Point:Points)
    {
        const int32 X=FMath::Clamp(FMath::FloorToInt((Point.X-Bounds.Min.X)/FMath::Max(1.,Cell.X)),0,7);
        const int32 Y=FMath::Clamp(FMath::FloorToInt((Point.Y-Bounds.Min.Y)/FMath::Max(1.,Cell.Y)),0,7);
        const int32 Index=Y*8+X;
        if(!Used[Index]||Point.Z<Lowest[Index].Z){Lowest[Index]=Point;Used[Index]=true;}
    }
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(M66AnimatedCorpseSurface),true,Mesh->GetOwner());
    double Gap=TNumericLimits<double>::Max();
    for(int32 I=0;I<64;++I)
    {
        if(!Used[I])continue;FHitResult Floor;
        if(Mesh->GetWorld()->LineTraceSingleByObjectType(Floor,Lowest[I]+FVector(0,0,35),Lowest[I]-FVector(0,0,600),Objects,Query)&&Floor.ImpactNormal.Z>.5)
            Gap=FMath::Min(Gap,Lowest[I].Z-Floor.ImpactPoint.Z-.5);
    }
    if(Gap!=TNumericLimits<double>::Max())
        Mesh->AddWorldOffset(FVector(0,0,FMath::Clamp(-Gap,-600.,60.)),false,nullptr,ETeleportType::TeleportPhysics);
    return true;
}
