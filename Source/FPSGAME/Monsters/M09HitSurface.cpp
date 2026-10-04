#include "HangingBellM09.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#if WITH_EDITOR
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif

bool AHangingBellM09::IsWeakpointHit(const FHitResult& Hit) const
{
 // Geometric classification also remains valid after a lethal damage callback,
 // when the bullet asks for its headshot sound. Damage/rewards own the alive gate.
 // The existing authoritative network hit receipt carries actor/bone/point,
 // but omits Component. Reject a different supplied component, not that receipt.
 return Hit.GetActor()==this&&(!Hit.GetComponent()||Hit.GetComponent()==GetMesh())&&!Hit.BoneName.IsNone()&&
  (Hit.BoneName==TEXT("eye_crown")||GetMesh()->BoneIsChildOf(Hit.BoneName,TEXT("eye_crown")));
}

void AHangingBellM09::RefreshHitPhysics()
{
 if(!VisualMesh)return;
 UPhysicsAsset* Desired=!Dead()&&HitSurfacePhysics?HitSurfacePhysics.Get():VisualMesh->GetPhysicsAsset();
 if(GetMesh()->GetPhysicsAsset()!=Desired)GetMesh()->SetPhysicsAsset(Desired);
}

bool AHangingBellM09::BuildHitSurfacePhysics(USkeletalMesh* InMesh,UPhysicsAsset* HitAsset)
{
#if WITH_EDITOR
 if(!InMesh||!HitAsset||HitAsset==InMesh->GetPhysicsAsset()||!InMesh->GetPhysicsAsset()||
    !InMesh->GetImportedModel()||InMesh->GetImportedModel()->LODModels.IsEmpty())return false;
 const auto& Ref=InMesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
 for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
 TArray<int32> Bones;TMap<int32,int32> Regions;
 for(int32 I=0;I<Ref.GetNum();++I)if(Ref.GetBoneName(I).ToString().StartsWith(TEXT("membrane_")))
 {Regions.Add(I,Bones.Num());Bones.Add(I);}
 if(Bones.Num()!=24)return false;
 TArray<TArray<FVector>> Points;Points.SetNum(Bones.Num());
 for(const auto& Section:InMesh->GetImportedModel()->LODModels[0].Sections)for(const auto& V:Section.SoftVertices)
 {
  // Include the blend boundary in adjacent segments, avoiding gaps when a leaf bends.
  uint32 Total=0;for(int32 J=0;J<MAX_TOTAL_INFLUENCES;++J)Total+=V.InfluenceWeights[J];
  for(int32 J=0;J<MAX_TOTAL_INFLUENCES;++J)
  {
   if(!V.InfluenceWeights[J]||uint32(V.InfluenceWeights[J])*5<Total)continue;
   const int32 Bone=Section.BoneMap[V.InfluenceBones[J]];
   if(const int32* Region=Regions.Find(Bone))Points[*Region].Add(Frames[Bone].InverseTransformPosition(FVector(V.Position)));
  }
 }
 for(const auto& Cloud:Points)if(Cloud.Num()<4)return false;
 HitAsset->Modify();HitAsset->SkeletalBodySetups.Reset();HitAsset->ConstraintSetup.Reset();HitAsset->CollisionDisableTable.Reset();
 // The live query asset has no simulated joints. The original corpse asset is
 // never modified and is restored before any death-pose capture or simulation.
 for(const USkeletalBodySetup* Source:InMesh->GetPhysicsAsset()->SkeletalBodySetups)
 {
  auto* Body=DuplicateObject<USkeletalBodySetup>(Source,HitAsset,NAME_None);
  Body->PhysicsType=PhysType_Kinematic;HitAsset->SkeletalBodySetups.Add(Body);
 }
 for(int32 I=0;I<Bones.Num();++I)
 {
  const int32 Bone=Bones[I];auto* Body=NewObject<USkeletalBodySetup>(HitAsset,NAME_None,RF_Transactional);
  Body->BoneName=Ref.GetBoneName(Bone);Body->PhysicsType=PhysType_Kinematic;
  Body->CollisionTraceFlag=CTF_UseSimpleAsComplex;
  FKConvexElem Hull;const float Padding=1.f/FMath::Max(Frames[Bone].GetScale3D().GetAbsMax(),.001f);
  for(int32 X=-1;X<=1;++X)for(int32 Y=-1;Y<=1;++Y)for(int32 Z=-1;Z<=1;++Z)
  {
   if(X==0&&Y==0&&Z==0)continue;
   const FVector Direction=FVector(X,Y,Z).GetSafeNormal();float Best=-FLT_MAX;FVector Point=FVector::ZeroVector;
   for(const FVector& P:Points[I])if(const float Dot=FVector::DotProduct(P,Direction);Dot>Best){Best=Dot;Point=P;}
   Hull.VertexData.AddUnique(Point+Direction*Padding);
  }
  Hull.UpdateElemBox();Body->AggGeom.ConvexElems.Add(Hull);
  Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
  Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::QueryOnly);
  Body->InvalidatePhysicsData();Body->CreatePhysicsMeshes();HitAsset->SkeletalBodySetups.Add(Body);
 }
 HitAsset->UpdateBodySetupIndexMap();HitAsset->UpdateBoundsBodiesArray();HitAsset->MarkPackageDirty();return true;
#else
 return false;
#endif
}
