#include "M09AnimInstance.h"
#include "HangingBellM09.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "TwoBoneIK.h"
struct FM09HandSupport : FAnimNode_SkeletalControlBase
{
 FBoneReference Upper[2],Lower[2],Hand[2],Eyes[5];
 FVector Goal[2],Pole[2],Aim=FVector::ZeroVector,Forward=FVector::ForwardVector;
 FQuat Rotation[2];float Weight[2]={0,0};bool Aiming=false;
 FM09HandSupport()
 {
  Alpha=1;
  for(int32 I=0;I<2;++I){const FString S=I==0?TEXT("L"):TEXT("R");Upper[I].BoneName=FName(TEXT("big_upperarm_")+S);Lower[I].BoneName=FName(TEXT("big_forearm_")+S);Hand[I].BoneName=FName(TEXT("big_hand_")+S);}
  for(int32 I=0;I<5;++I)Eyes[I].BoneName=FName(*FString::Printf(TEXT("eye_%02d"),I+1));
 }
 virtual void InitializeBoneReferences(const FBoneContainer& Bones) override
 {
  auto Ref=[&Bones](FCompactPoseBoneIndex B){FTransform T=Bones.GetRefPoseTransform(B);for(auto P=Bones.GetParentBoneIndex(B);P!=INDEX_NONE;P=Bones.GetParentBoneIndex(P))T*=Bones.GetRefPoseTransform(P);return T;};
  for(int32 I=0;I<2;++I)
  {
   Upper[I].Initialize(Bones);Lower[I].Initialize(Bones);Hand[I].Initialize(Bones);
   if(Upper[I].IsValidToEvaluate(Bones)&&Lower[I].IsValidToEvaluate(Bones)&&Hand[I].IsValidToEvaluate(Bones))
   {
    const FVector A=Ref(Upper[I].GetCompactPoseIndex(Bones)).GetLocation(),B=Ref(Lower[I].GetCompactPoseIndex(Bones)).GetLocation(),C=Ref(Hand[I].GetCompactPoseIndex(Bones)).GetLocation();
    const FVector Axis=(C-A).GetSafeNormal();Pole[I]=(B-A-Axis*FVector::DotProduct(B-A,Axis)).GetSafeNormal();
   }
  }
  for(auto& E:Eyes)E.Initialize(Bones);
 }
 virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer& B) override{return Upper[0].IsValidToEvaluate(B)&&Hand[1].IsValidToEvaluate(B);}
 virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& O,TArray<FBoneTransform>& Out) override
 {
  const auto& B=O.Pose.GetPose().GetBoneContainer();
  for(int32 I=0;I<2;++I)
  {
   if(Weight[I]<=0||!Upper[I].IsValidToEvaluate(B)||!Lower[I].IsValidToEvaluate(B)||!Hand[I].IsValidToEvaluate(B))continue;
   const auto U=Upper[I].GetCompactPoseIndex(B),L=Lower[I].GetCompactPoseIndex(B),H=Hand[I].GetCompactPoseIndex(B);
   FTransform A=O.Pose.GetComponentSpaceTransform(U),M=O.Pose.GetComponentSpaceTransform(L),E=O.Pose.GetComponentSpaceTransform(H);
   const FTransform OldA=A,OldM=M,OldE=E;const float Reach=FVector::Distance(A.GetLocation(),M.GetLocation())+FVector::Distance(M.GetLocation(),E.GetLocation());
   const FVector Dir=(Goal[I]-A.GetLocation()).GetSafeNormal();FVector Bend=Pole[I]-Dir*FVector::DotProduct(Pole[I],Dir);
   if(Bend.IsNearlyZero())Bend=FVector::CrossProduct(Dir,Forward);
   const FVector Target=A.GetLocation()+Dir*FMath::Min(float(FVector::Distance(A.GetLocation(),Goal[I])),Reach*.995f);
   AnimationCore::SolveTwoBoneIK(A,M,E,A.GetLocation()+Bend.GetSafeNormal()*Reach,Target,false,1.,1.);
   E.SetRotation(Rotation[I]);A.Blend(OldA,A,Weight[I]);M.Blend(OldM,M,Weight[I]);E.Blend(OldE,E,Weight[I]);
   Out.Emplace(U,A);Out.Emplace(L,M);Out.Emplace(H,E);
  }
  if(Aiming)for(const auto& Eye:Eyes)if(Eye.IsValidToEvaluate(B))
  {
   const auto I=Eye.GetCompactPoseIndex(B);FTransform E=O.Pose.GetComponentSpaceTransform(I);
   FQuat Q=FQuat::FindBetweenNormals(Forward,(Aim-E.GetLocation()).GetSafeNormal());
   const float Angle=Q.GetAngle();if(Angle>FMath::DegreesToRadians(24.f))Q=FQuat::Slerp(FQuat::Identity,Q,FMath::DegreesToRadians(24.f)/Angle);
   E.SetRotation((Q*E.GetRotation()).GetNormalized());Out.Emplace(I,E);
  }
  Out.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex.GetInt()<B.BoneIndex.GetInt();});
 }
};
struct FM09Proxy : FAnimInstanceProxy
{
 FAnimNode_PoseSnapshot Previous;
 FAnimNode_SequenceEvaluator_Standalone Current;
 FAnimNode_TwoWayBlend Blend;
 FAnimNode_ConvertLocalToComponentSpace ToComponent;
 FM09HandSupport Hands;
 FAnimNode_ConvertComponentToLocalSpace ToLocal;
 explicit FM09Proxy(UAnimInstance* I):FAnimInstanceProxy(I)
 {
  Previous.Mode=ESnapshotSourceMode::SnapshotPin;Blend.A.SetLinkNode(&Previous);Blend.B.SetLinkNode(&Current);
  ToComponent.LocalPose.SetLinkNode(&Blend);Hands.ComponentPose.SetLinkNode(&ToComponent);ToLocal.ComponentPose.SetLinkNode(&Hands);
 }
 virtual FAnimNode_Base* GetCustomRootNode() override{return &ToLocal;}
 virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Out) override{Out.Append({&Previous,&Current,&Blend,&ToComponent,&Hands,&ToLocal});}
 virtual void PreUpdate(UAnimInstance* I,float Dt) override
 {
  FAnimInstanceProxy::PreUpdate(I,Dt);const auto* A=CastChecked<UM09AnimInstance>(I);const auto* M=Cast<AHangingBellM09>(I->TryGetPawnOwner());if(!M)return;
  Previous.Snapshot=A->PreviousPose;Blend.Alpha=A->PreviousPose.bIsValid?A->BlendAlpha:1.f;
  Current.SetSequence(A->ActiveClip);Current.SetShouldLoop(A->bLooping);Current.SetTeleportToExplicitTime(true);Current.SetExplicitTime(A->ClipTime);
  const FTransform Frame=M->GetMesh()->GetComponentTransform();
  for(int32 S=0;S<2;++S)
  {
   Hands.Goal[S]=Frame.InverseTransformPosition(M->GripTargets[S]);
   Hands.Rotation[S]=(Frame.GetRotation().Inverse()*M->GripRotations[S].Quaternion()).GetNormalized();
   Hands.Weight[S]=M->GripTargets[S].IsNearlyZero()?0.f:M->HandIKWeight(S);
  }
  Hands.Aiming=M->State==EM09State::Gaze;Hands.Aim=Frame.InverseTransformPosition(M->LockedAim);Hands.Forward=Frame.InverseTransformVectorNoScale(M->GetActorForwardVector());
 }
};
FAnimInstanceProxy* UM09AnimInstance::CreateAnimInstanceProxy(){return new FM09Proxy(this);}
void UM09AnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* P){delete P;}
