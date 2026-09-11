#pragma once
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "SkeletalRenderPublic.h"

// Read the current physics-blended surface without refreshing the animation pose.
namespace MonsterSurfaceAudit
{
inline TArray<FVector> WorldVertices(USkeletalMeshComponent* Mesh)
{
 TArray<FMatrix44f> Matrices;Mesh->GetCurrentRefToLocalMatrices(Matrices,0);
 TArray<FVector3f> Skinned;const auto& LOD=Mesh->GetSkeletalMeshAsset()->GetResourceForRendering()->LODRenderData[0];
 USkinnedMeshComponent::ComputeSkinnedPositions(Mesh,Skinned,Matrices,LOD,*Mesh->GetSkinWeightBuffer(0));
 TArray<FVector> Result;Result.Reserve(Skinned.Num());for(const auto& V:Skinned)Result.Add(Mesh->GetComponentTransform().TransformPosition(FVector(V)));return Result;
}
struct FGroundResult { FBox Bounds{ForceInit};float Minimum=10000;int32 Samples=0,Missing=0,Underground=0; };
inline FGroundResult Ground(USkeletalMeshComponent* Mesh,UPrimitiveComponent* Floor)
{
 FGroundResult R;const auto Vertices=WorldVertices(Mesh);for(const auto& V:Vertices)R.Bounds+=V;
 FCollisionQueryParams Q(SCENE_QUERY_STAT(MonsterSurfaceGround),true);
 for(int32 I=0;I<Vertices.Num();I+=17){const FVector V=Vertices[I];FHitResult Hit;
  if(Floor&&Floor->LineTraceComponent(Hit,V+FVector(0,0,400),V-FVector(0,0,600),Q)&&!Hit.bStartPenetrating&&Hit.ImpactNormal.Z>.6){float Gap=V.Z-Hit.ImpactPoint.Z;R.Minimum=FMath::Min(R.Minimum,Gap);++R.Samples;if(Gap< -3)++R.Underground;}else ++R.Missing;}
 return R;
}
}
