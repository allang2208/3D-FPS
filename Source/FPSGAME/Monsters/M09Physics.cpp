#include "HangingBellM09.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#if WITH_EDITOR
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif
bool AHangingBellM09::BuildPhysics(USkeletalMesh* Mesh,UPhysicsAsset* Asset)
{
#if WITH_EDITOR
 if(!Mesh||!Asset||!Mesh->GetImportedModel()||Mesh->GetImportedModel()->LODModels.IsEmpty())return false;
 const auto& Ref=Mesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
 for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
 TArray<FName> Names={TEXT("root"),TEXT("spine_01"),TEXT("spine_02"),TEXT("spine_03"),TEXT("spine_04"),TEXT("crown_neck"),TEXT("eye_crown")};
 for(const TCHAR* Size:{TEXT("big"),TEXT("small")})for(const TCHAR* Side:{TEXT("L"),TEXT("R")})
  for(const TCHAR* Part:{TEXT("upperarm"),TEXT("forearm"),TEXT("hand")})Names.Add(FName(*FString::Printf(TEXT("%s_%s_%s"),Size,Part,Side)));
 TArray<TArray<FVector>> Points;Points.SetNum(Names.Num());
 for(const auto& Section:Mesh->GetImportedModel()->LODModels[0].Sections)for(const auto& V:Section.SoftVertices)
 {
  int32 Dominant=0;for(int32 J=1;J<MAX_TOTAL_INFLUENCES;++J)if(V.InfluenceWeights[J]>V.InfluenceWeights[Dominant])Dominant=J;
  int32 Bone=Section.BoneMap[V.InfluenceBones[Dominant]];
  if(Ref.GetBoneName(Bone).ToString().StartsWith(TEXT("membrane_")))continue;
  while(Bone>=0)
  {
   const int32 Region=Names.IndexOfByKey(Ref.GetBoneName(Bone));
   if(Region>=0){if(Region>0)Points[Region].Add(Frames[Bone].InverseTransformPosition(FVector(V.Position)));break;}
   Bone=Ref.GetParentIndex(Bone);
  }
 }
 Asset->Modify();Asset->SkeletalBodySetups.Reset();Asset->ConstraintSetup.Reset();Asset->CollisionDisableTable.Reset();
 for(int32 I=0;I<Names.Num();++I)
 {
  const int32 B=Ref.FindBoneIndex(Names[I]);if(B<0)return false;
  auto* Body=NewObject<USkeletalBodySetup>(Asset,NAME_None,RF_Transactional);Body->BoneName=Names[I];
  Body->PhysicsType=PhysType_Default;Body->CollisionTraceFlag=CTF_UseSimpleAsComplex;
  if(I==0||Points[I].Num()<4)
  {
   FKSphereElem Shape;Shape.Radius=I==0?1.f:4.f;Body->AggGeom.SphereElems.Add(Shape);
  }
  else
  {
   FKConvexElem Hull;
   for(int32 X=-1;X<=1;++X)for(int32 Y=-1;Y<=1;++Y)for(int32 Z=-1;Z<=1;++Z)
   {
    if(X==0&&Y==0&&Z==0)continue;const FVector D(X,Y,Z);float Best=-FLT_MAX;FVector P=FVector::ZeroVector;
    for(const FVector V:Points[I]){const float Dot=FVector::DotProduct(V,D);if(Dot>Best){Best=Dot;P=V;}}
    Hull.VertexData.AddUnique(P);
   }
   Hull.UpdateElemBox();Body->AggGeom.ConvexElems.Add(Hull);
  }
  Body->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));
  Body->DefaultInstance.SetMassOverride(I==0?.1f:I==1?18.f:I<7?7.f:Names[I].ToString().StartsWith(TEXT("big"))?4.f:1.f);
  Body->DefaultInstance.LinearDamping=.3f;Body->DefaultInstance.AngularDamping=.9f;
  Body->DefaultInstance.bUseCCD=true;Body->DefaultInstance.PositionSolverIterationCount=12;Body->DefaultInstance.VelocitySolverIterationCount=4;
  if(I==0)Body->DefaultInstance.SetCollisionEnabled(ECollisionEnabled::NoCollision);
  Body->InvalidatePhysicsData();Body->CreatePhysicsMeshes();Asset->SkeletalBodySetups.Add(Body);
 }
 Asset->UpdateBodySetupIndexMap();
 for(int32 I=1;I<Names.Num();++I)
 {
  const int32 B=Ref.FindBoneIndex(Names[I]);int32 P=Ref.GetParentIndex(B);
  while(P>=0&&!Names.Contains(Ref.GetBoneName(P)))P=Ref.GetParentIndex(P);
  if(P<0)return false;
  auto* Joint=NewObject<UPhysicsConstraintTemplate>(Asset,NAME_None,RF_Transactional);auto& C=Joint->DefaultInstance;
  C.JointName=Names[I];C.ConstraintBone1=Names[I];C.ConstraintBone2=Ref.GetBoneName(P);
  const FTransform Anchor(Frames[B].GetRotation(),Frames[B].GetLocation());
  C.SetRefFrame(EConstraintFrame::Frame1,Anchor.GetRelativeTransform(Frames[B]));C.SetRefFrame(EConstraintFrame::Frame2,Anchor.GetRelativeTransform(Frames[P]));
  C.SetLinearXLimit(LCM_Locked,0);C.SetLinearYLimit(LCM_Locked,0);C.SetLinearZLimit(LCM_Locked,0);
  const bool Arm=Names[I].ToString().Contains(TEXT("arm"));const bool Elbow=Names[I].ToString().Contains(TEXT("forearm"));
  C.SetAngularSwing1Limit(ACM_Limited,Elbow?75.f:Arm?45.f:22.f);
  C.SetAngularSwing2Limit(ACM_Limited,Elbow?12.f:Arm?30.f:18.f);C.SetAngularTwistLimit(ACM_Limited,Elbow?12.f:22.f);
  C.SetDisableCollision(true);C.DisableProjection();C.SetShockPropagationParams(false,0);
  C.SetOrientationDriveTwistAndSwing(false,false);C.SetAngularVelocityDriveTwistAndSwing(false,false);
  Joint->SetDefaultProfile(C);Asset->ConstraintSetup.Add(Joint);
 }
 // Crossed hands and layered tissue overlap in the authored rest pose; collision is with the world.
 for(int32 I=0;I<Names.Num();++I)for(int32 J=I+1;J<Names.Num();++J)Asset->DisableCollision(I,J);
 Asset->UpdateBoundsBodiesArray();Asset->MarkPackageDirty();Mesh->SetPhysicsAsset(Asset);Mesh->MarkPackageDirty();return true;
#else
 return false;
#endif
}
