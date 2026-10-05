// Stepping design adapted from WeaverDev/Bonehead (MIT, copyright 2019 WeaverDev).
// License: Content/ThirdPartyNotices/Bonehead.txt. No Bonehead art is used.
#include "LurkerM08ContactNode.h"
#include "LurkerM08Monster.h"
#include "QuadrupedAnimationTemplate.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TwoBoneIK.h"

namespace
{
const TCHAR* FootNames[] = {TEXT("hand_L"), TEXT("hand_R"), TEXT("hindfoot_L"), TEXT("hindfoot_R")};
const TCHAR* UpperNames[] = {TEXT("upperarm_L"), TEXT("upperarm_R"), TEXT("thigh_L"), TEXT("thigh_R")};
const TCHAR* LowerNames[] = {TEXT("forearm_L"), TEXT("forearm_R"), TEXT("calf_L"), TEXT("calf_R")};
const TCHAR* AnkleNames[] = {TEXT("hand_L"), TEXT("hand_R"), TEXT("ankle_L"), TEXT("ankle_R")};
float Ease(float T) { T = FMath::Clamp(T, 0.f, 1.f); return T*T*(3.f-2.f*T); }
void Damped(FVector& Value, FVector& Velocity, const FVector& Goal, float Dt, float Omega=15.f)
{
    const FVector Error = Value - Goal, J = Velocity + Omega*Error;
    const float Decay = FMath::Exp(-Omega*Dt);
    Value = Goal + (Error + J*Dt)*Decay; Velocity = (Velocity - Omega*J*Dt)*Decay;
}
}

FLurkerM08ContactNode::FLurkerM08ContactNode() { Alpha = 1.f; }

void FLurkerM08ContactNode::ResetLocomotionMotion()
{
    StepMotion=StepVelocity=NeckMotion=NeckVelocity=FVector::ZeroVector;
    HeadMotion=HeadVelocity=ArchMotion=ArchVelocity=FVector::ZeroVector;
    MoveWeight=0.f;
}

void FLurkerM08ContactNode::CacheReference(const ALurkerM08Monster* Monster)
{
    USkeletalMesh* Mesh = Monster->GetMesh()->GetSkeletalMeshAsset();
    if (CachedMesh == Mesh && ReferenceReady) return;
    CachedMesh = Mesh; ReferenceReady = false; WasEnabled = false;
    if (!Mesh) return;
    const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
    TArray<FTransform> CS = Ref.GetRefBonePose();
    for (int32 I=0; I<CS.Num(); ++I)
        if (Ref.GetParentIndex(I) != INDEX_NONE) CS[I] *= CS[Ref.GetParentIndex(I)];
    for (int32 I=0; I<4; ++I)
    {
        const int32 F=Ref.FindBoneIndex(FootNames[I]), U=Ref.FindBoneIndex(UpperNames[I]);
        const int32 L=Ref.FindBoneIndex(LowerNames[I]), A=Ref.FindBoneIndex(AnkleNames[I]);
        if (F==INDEX_NONE || U==INDEX_NONE || L==INDEX_NONE || A==INDEX_NONE) return;
        auto& Foot=Feet[I]; Foot=FFoot();
        Foot.Reference=CS[F].GetLocation(); Foot.ReferenceRotation=CS[F].GetRotation();
        // The mesh authoring origin is the sole plane, in UE component cm.
        Foot.Height=FMath::Max(0.f, float(Foot.Reference.Z));
        const FVector Root=CS[U].GetLocation(), Knee=CS[L].GetLocation();
        const FVector Axis=(CS[A].GetLocation()-Root).GetSafeNormal();
        Foot.Pole=(Knee-Root-Axis*FVector::DotProduct(Knee-Root,Axis)).GetSafeNormal();
        Foot.Hock=(CS[F].GetLocation()-CS[A].GetLocation()).GetSafeNormal();
    }
    MouthSamples.Reset(); MouthProbeCS=FVector::ZeroVector;
    for (const auto& Vertex:Monster->MouthSupportSamples)
    {
        if (MouthSamples.Num()>=12) break;
        FMouthSample Sample;
        FVector Point=FVector::ZeroVector;
        for (const auto& Influence:Vertex.Influences)
        {
            const int32 Bone=Ref.FindBoneIndex(Influence.Bone);
            if (Bone==INDEX_NONE || Sample.Count>=4) continue;
            const int32 J=Sample.Count++;
            Sample.Bones[J]=Influence.Bone; Sample.Local[J]=Influence.BoneLocalPosition;
            Sample.Weights[J]=Influence.Weight;
            Point+=CS[Bone].TransformPosition(Influence.BoneLocalPosition)*Influence.Weight;
        }
        if (Sample.Count>0) { MouthSamples.Add(Sample); MouthProbeCS+=Point; }
    }
    if (!MouthSamples.IsEmpty()) MouthProbeCS/=MouthSamples.Num();
    ReferenceReady=true;
}

void FLurkerM08ContactNode::Prepare(const ALurkerM08Monster* M, const UQuadrupedTemplateAnimInstance* Anim, float Dt)
{
    Enabled=false;
    if (!M || !Anim) { WasEnabled=false; ResetLocomotionMotion(); return; }
    const auto* Mesh=M->GetMesh();
    const auto* Movement=M->GetCharacterMovement();
    const bool Leap=Anim->ActiveAction==TEXT("AttackPounce")||Anim->ActiveAction==TEXT("TraverseJump");
    const bool Cannon=Anim->ActiveAction==TEXT("AttackAirCannon");
    const bool Supported=M->bSurfaceAttached||Movement->IsMovingOnGround();
    const bool WasActionSupport=ActionSupport;
    ActionTime=Anim->ActionTime;
    ActionSupport=Supported&&(Cannon||(Leap&&(ActionTime<.24f||(ActionTime>=.74f&&ActionTime<1.14f))));
    CannonSupport=Cannon&&ActionSupport;
    FlightOnly=Leap&&!Supported&&ActionTime>=.24f&&ActionTime<.74f;
    const bool Locomotion=(Anim->ActiveAction.IsNone()&&!M->bTraversalJump&&Supported)||ActionSupport||FlightOnly;
    if (!Locomotion||M->Dead()||Mesh->IsSimulatingPhysics())
    { WasEnabled=false; BodyOffset=BodyVelocity=FVector::ZeroVector; Turn=Pitch=0.f; ResetLocomotionMotion(); return; }
    CacheReference(M); if (!ReferenceReady) return;
    const FTransform Frame=Mesh->GetComponentTransform();
    const FVector Up=M->GetActorUpVector(), Forward=M->GetActorForwardVector();
    UpCS=Frame.InverseTransformVectorNoScale(Up).GetSafeNormal();
    ForwardCS=Frame.InverseTransformVectorNoScale(Forward).GetSafeNormal();
    RightCS=Frame.InverseTransformVectorNoScale(M->GetActorRightVector()).GetSafeNormal();
    FlightPitch=FlightOnly ? M->LeapPitchCorrection(Anim->ActiveAction==TEXT("TraverseJump"),ActionTime) : 0.f;
    CorrectionWeight=Leap&&ActionSupport&&ActionTime>=.74f ? 1.f-Ease((ActionTime-1.04f)/.10f) : 1.f;
    if (FlightOnly)
    {
        Enabled=true;WasEnabled=false;BodyOffset=BodyVelocity=FVector::ZeroVector;Turn=Pitch=0.f;
        ResetLocomotionMotion();
        return;
    }
    const bool Reset=!WasEnabled || WasActionSupport!=ActionSupport || Dt>.25f || FVector::DistSquared(M->GetActorLocation(),LastLocation)>FMath::Square(120.f) ||
        M->GetActorQuat().AngularDistance(LastRotation)>FMath::DegreesToRadians(55.f);
    const float StepDt=FMath::Clamp(Dt,0.f,.1f);
    const float GaitRate=FMath::Max(.1f,M->ChaseSpeed/210.f);
    const float Speed=FMath::Min(240.f*GaitRate, float(FVector::VectorPlaneProject(M->GetVelocity(),Up).Size()));
    const FVector Velocity=FVector::VectorPlaneProject(M->GetVelocity(),Up).GetClampedToMaxSize(240.f*GaitRate);
    const float GaitRatio=FMath::Clamp(Speed/(210.f*GaitRate),0.f,1.f);
    const float SwingSeconds=FMath::Lerp(.28f,.09f,GaitRatio)/GaitRate;
    const float RearDelay=FMath::Lerp(.045f,.026f,GaitRatio)/GaitRate;
    const float YawRate=Reset||Dt<SMALL_NUMBER ? 0.f : FMath::Atan2(FVector::DotProduct(FVector::CrossProduct(LastForward,Forward),Up), FVector::DotProduct(LastForward,Forward))/Dt;
    Turn=FMath::FInterpTo(Turn,FMath::Clamp(YawRate,-2.5f,2.5f),StepDt,8.f);
    LastLocation=M->GetActorLocation(); LastRotation=M->GetActorQuat(); LastForward=Forward;
    if (Reset)
    {
        for (auto& F:Feet) { F.Planted=F.Swing=F.Valid=false; F.Curl=F.Load=0.f; F.ContactAge=1.f; F.Base.Reset(); }
        BodyOffset=BodyVelocity=FVector::ZeroVector; QueryAge=1.f; NextPair=0;
        ResetLocomotionMotion();
        for (auto& Plane:MouthPlanes) Plane.Valid=false;
    }
    QueryAge+=StepDt;
    // Four bounded probes at 30 Hz, no worker-thread world access.
    const bool Query=QueryAge>=1.f/30.f; if (Query) QueryAge=0.f;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(M08FootSupport),false,M);
    // Only the supported cannon adds these three bounded probes. The worker
    // consumes copied planes and skin samples; no world or mesh queries there.
    if (Query && CannonSupport && !MouthSamples.IsEmpty())
    {
        for (int32 I=0;I<3;++I)
        {
            auto& Plane=MouthPlanes[I];
            const FVector Probe=Frame.TransformPosition(MouthProbeCS+RightCS*((I-1)*18.f));
            FHitResult Hit;
            Plane.Valid=M->GetWorld()->LineTraceSingleByChannel(Hit,Probe+Up*60.f,Probe-Up*100.f,ECC_Pawn,Params)
                && Hit.bBlockingHit && !Cast<APawn>(Hit.GetActor()) && FVector::DotProduct(Hit.ImpactNormal,Up)>.2f;
            if (Plane.Valid)
            {
                Plane.Point=Frame.InverseTransformPosition(Hit.ImpactPoint);
                Plane.Normal=Frame.InverseTransformVectorNoScale(Hit.ImpactNormal).GetSafeNormal();
            }
        }
    }
    FVector Home[4];
    for (int32 I=0; I<4; ++I)
    {
        auto& F=Feet[I];
        F.ContactAge+=StepDt;
        F.Load=0.f;
        const float LandingReach=Leap&&ActionSupport&&ActionTime>=.74f?(I<2?16.f:-8.f):0.f;
        Home[I]=Frame.TransformPosition(F.Reference+ForwardCS*LandingReach);
        if (Leap&&ActionSupport&&ActionTime<.24f&&I<2&&ActionTime>=.19f+I*.018f)
        { F.Planted=F.Swing=F.Valid=false;continue; }
        if (Leap&&ActionSupport&&ActionTime>=.74f&&ActionTime<(I<2?.74f:.84f)+(I%2)*.028f)
        { F.Planted=F.Swing=F.Valid=false;continue; }
        if (F.Planted && F.Base.IsValid())
        {
            const FTransform BaseFrame=F.Base->GetComponentTransform();
            F.Position=BaseFrame.TransformPosition(F.BasePoint);
            F.Normal=BaseFrame.TransformVectorNoScale(F.BaseNormal).GetSafeNormal();
            F.Rotation=(BaseFrame.GetRotation()*F.BaseRotation).GetNormalized();
        }
        if (Query)
        {
            // Predict translation and yaw so outer hands take longer turns.
            // Aim beyond the body position at touchdown, not its position at
            // lift-off; otherwise fast crawling always lands behind home.
            const float Lead=SwingSeconds+(I<2?0.f:RearDelay)+(I<2?11.f:8.f)/FMath::Max(20.f,Speed);
            const FVector Offset=Home[I]-M->GetActorLocation();
            const FVector Ahead=ActionSupport?FVector::ZeroVector:(Velocity*Lead + FVector::CrossProduct(Up,Offset)*YawRate*.09f).GetClampedToMaxSize(I<2?42.f:36.f);
            const FVector Probe=Home[I]+Ahead;
            FHitResult Hit;
            F.Valid=M->GetWorld()->LineTraceSingleByChannel(Hit,Probe+Up*45.f,Probe-Up*110.f,ECC_Pawn,Params) &&
                Hit.bBlockingHit && !Cast<APawn>(Hit.GetActor()) && FVector::DotProduct(Hit.ImpactNormal,Up)>.2f;
            if (F.Valid)
            {
                F.CandidateNormal=Hit.ImpactNormal.GetSafeNormal();
                F.Candidate=Hit.ImpactPoint+F.CandidateNormal*(F.Height*Frame.GetScale3D().Z);
                F.CandidateRotation=(FQuat::FindBetweenNormals(Up,F.CandidateNormal)*Frame.GetRotation()*F.ReferenceRotation).GetNormalized();
                F.CandidateBase=Hit.GetComponent();
            }
        }
        auto Plant=[&]()
        {
            // Only an actual swing landing produces a compression pulse.
            // Initial placement and action support must not fabricate a step.
            if (F.Swing) F.ContactAge=0.f;
            F.Base=F.Swing?F.LandingBase:F.CandidateBase;
            F.Swing=false; F.Planted=true;
            if (F.Base.IsValid())
            {
                const FTransform B=F.Base->GetComponentTransform();
                F.BasePoint=B.InverseTransformPosition(F.Position); F.BaseNormal=B.InverseTransformVectorNoScale(F.Normal);
                F.BaseRotation=(B.GetRotation().Inverse()*F.Rotation).GetNormalized();
            }
        };
        if (!F.Planted && !F.Swing && F.Valid)
        { F.Position=F.Candidate; F.Normal=F.CandidateNormal; F.Rotation=F.CandidateRotation; Plant(); }
        if (F.Swing)
        {
            F.Time+=StepDt; const float T=FMath::Clamp(F.Time/F.Duration,0.f,1.f), S=Ease(T);
            const FVector ArcNormal=FMath::Lerp(F.StartNormal,F.EndNormal,S).GetSafeNormal();
            const float Arc=Ease(T/.36f)*(1.f-Ease((T-.36f)/.64f));
            F.Position=FMath::Lerp(F.Start,F.End,S)+ArcNormal*(F.Lift*Arc);
            F.Normal=ArcNormal; F.Rotation=FQuat::Slerp(F.StartRotation,F.EndRotation,S).GetNormalized();
            // Cup the hand early, then open it before contact instead of
            // keeping the wrist/fingers curled into the landing.
            F.Curl=FMath::Sin(PI*Ease(T/.84f));
            if (T>=1.f) { F.Position=F.End; F.Normal=F.EndNormal; F.Rotation=F.EndRotation; F.Curl=0.f; Plant(); }
        }
        else F.Curl=0.f;
    }
    bool Swinging=false; for (const auto& F:Feet) Swinging|=F.Swing;
    if (!Swinging && !ActionSupport)
    {
        float Urgency[2]={0.f,0.f};
        for (int32 I=0; I<4; ++I)
        {
            const auto& F=Feet[I]; if (!F.Valid || !F.Planted) continue;
            const int32 Pair=(I==0 || I==3)?0:1;
            const float Distance=FVector::Distance(F.Position,Home[I]);
            const float Twist=F.Rotation.AngularDistance((Frame.GetRotation()*F.ReferenceRotation).GetNormalized());
            Urgency[Pair]=FMath::Max(Urgency[Pair],FMath::Max(Distance/(I<2?16.f:14.f),Twist/FMath::DegreesToRadians(28.f)));
        }
        int32 Pair=NextPair;
        if (Urgency[Pair]<1.f && Urgency[1-Pair]>=1.f) Pair=1-Pair;
        if (Urgency[Pair]>=1.f)
        {
            bool Started=false;
            for (int32 I=0; I<4; ++I)
            {
                auto& F=Feet[I]; if (((I==0||I==3)?0:1)!=Pair || !F.Valid || !F.Planted) continue;
                if (FVector::DistSquared(F.Position,F.Candidate)<FMath::Square(5.f) && F.Rotation.AngularDistance(F.CandidateRotation)<.15f) continue;
                F.Start=F.Position; F.End=F.Candidate; F.StartNormal=F.Normal; F.EndNormal=F.CandidateNormal;
                F.LandingBase=F.CandidateBase;
                F.StartRotation=F.Rotation; F.EndRotation=F.CandidateRotation;
                F.Duration=SwingSeconds*(I<2?1.f:1.12f);
                // Rear push follows the leading hand, breaking rigid pair symmetry.
                F.Time=I<2?0.f:-RearDelay;
                F.Lift=I<2?FMath::Lerp(7.f,12.f,GaitRatio):FMath::Lerp(5.f,9.f,GaitRatio);
                F.Planted=false; F.Swing=true; F.Base.Reset(); Started=true;
            }
            if (Started) NextPair=1-Pair;
        }
    }
    FVector Support=FVector::ZeroVector; float Sum=0.f, FrontHeight=0.f, RearHeight=0.f;
    int32 Contacts=0;
    for (int32 I=0; I<4; ++I)
    {
        auto& F=Feet[I]; if (!F.Planted && !F.Swing) continue;
        const float Weight=F.Swing?.25f:1.f;
        const FVector Delta=Frame.InverseTransformVectorNoScale((F.Swing?F.End:F.Position)-Home[I]);
        Support+=Delta*Weight; Sum+=Weight; ++Contacts;
        if (I<2) FrontHeight+=FVector::DotProduct(Delta,UpCS)*.5f;
        else RearHeight+=FVector::DotProduct(Delta,UpCS)*.5f;
        F.GoalCS=Frame.InverseTransformPosition(F.Position);
        F.RotationCS=(Frame.GetRotation().Inverse()*F.Rotation).GetNormalized();
    }
    FVector Desired=Sum>0.f ? Support/Sum : FVector::ZeroVector;
    const float Height=FMath::Clamp(float(FVector::DotProduct(Desired,UpCS)),-14.f,14.f);
    Desired=FVector::VectorPlaneProject(Desired,UpCS).GetClampedToMaxSize(7.f)*.65f + UpCS*(Height-2.0f*GaitRatio);
    Damped(BodyOffset,BodyVelocity,Desired,StepDt);
    Pitch=FMath::FInterpTo(Pitch,FMath::Clamp((FrontHeight-RearHeight)/190.f,-.10f,.10f),StepDt,10.f);
    if (ActionSupport || Contacts==0)
    {
        ResetLocomotionMotion();
    }
    else
    {
        // These signals come from the same swing clocks as the planted-foot
        // solver, not a free-running animation cycle. Turning in place may
        // still transfer weight; a stationary, planted creature settles.
        const float Activity=FMath::Max(Speed/(70.f*GaitRate),FMath::Abs(Turn)*.35f);
        const float TargetWeight=Ease(Activity);
        MoveWeight=FMath::Lerp(MoveWeight,TargetWeight,1.f-FMath::Exp(-StepDt/ .10f));
        float Sway=0.f,Reach=0.f,Lift=0.f,Landing=0.f;
        for (int32 I=0;I<4;++I)
        {
            auto& F=Feet[I];
            const float T=F.Swing?FMath::Clamp(F.Time/F.Duration,0.f,1.f):0.f;
            const float Swing=FMath::Sin(PI*T);
            const float Side=I%2==0?1.f:-1.f;
            const float FrontRear=I<2?1.f:-.45f;
            Sway+=Side*FrontRear*Swing;
            Reach+=(I<2?1.f:.45f)*FMath::Sin(2.f*PI*T);
            Lift+=(I<2?1.f:.45f)*Swing;
            const float LandingPhase=F.ContactAge/(.14f/FMath::Sqrt(GaitRate));
            F.Load=F.Planted&&LandingPhase<1.f?FMath::Square(FMath::Sin(PI*LandingPhase)):0.f;
            Landing+=(I<2?1.f:.45f)*F.Load;
        }
        const float Strength=MoveWeight*FMath::Lerp(.65f,1.f,GaitRatio);
        const FVector Goal=FVector(Sway/1.45f,Reach/1.45f,(.8f*Lift-.9f*Landing)/1.45f)*Strength;
        // Keep enough response at V07's faster cadence while leaving neck,
        // head and the middle of the arch behind the chest by distinct amounts.
        const float Response=FMath::Lerp(38.f,72.f,GaitRatio);
        Damped(StepMotion,StepVelocity,Goal,StepDt,Response);
        Damped(NeckMotion,NeckVelocity,StepMotion,StepDt,Response*.85f);
        Damped(HeadMotion,HeadVelocity,NeckMotion,StepDt,Response*.75f);
        Damped(ArchMotion,ArchVelocity,StepMotion,StepDt,Response*.60f);
    }
    Enabled=Contacts>0; WasEnabled=true;
}

void FLurkerM08ContactNode::InitializeBoneReferences(const FBoneContainer& Bones)
{
    Indices.Reset(); Parents.SetNum(Bones.GetCompactPoseNumBones());
    for (int32 I=0; I<Parents.Num(); ++I)
    {
        const FCompactPoseBoneIndex Index(I); Parents[I]=Bones.GetParentBoneIndex(Index).GetInt();
        const int32 MeshIndex=Bones.MakeMeshPoseIndex(Index).GetInt();
        Indices.Add(Bones.GetReferenceSkeleton().GetBoneName(MeshIndex),I);
    }
}
bool FLurkerM08ContactNode::IsValidToEvaluate(const USkeleton*,const FBoneContainer&)
{
    for (int32 I=0; I<4; ++I)
        if (!Indices.Contains(UpperNames[I])||!Indices.Contains(LowerNames[I])||!Indices.Contains(FootNames[I])||!Indices.Contains(AnkleNames[I])) return false;
    return Indices.Contains(TEXT("pelvis"))&&Indices.Contains(TEXT("chest"));
}

void FLurkerM08ContactNode::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out)
{
    if (!Enabled) return;
    TArray<FTransform,TInlineAllocator<96>> Pose, Original;
    for (int32 I=0; I<Parents.Num(); ++I) Pose.Add(Output.Pose.GetComponentSpaceTransform(FCompactPoseBoneIndex(I)));
    Original=Pose;
    auto Index=[&](FName Name){const int32* I=Indices.Find(Name);return I?*I:INDEX_NONE;};
    auto Set=[&](int32 Bone,const FTransform& Value)
    {
        if (Bone==INDEX_NONE) return;
        const FTransform Before=Pose[Bone];
        for (int32 I=Bone+1; I<Pose.Num(); ++I)
        {
            int32 P=Parents[I]; while (P!=INDEX_NONE && P!=Bone) P=Parents[P];
            if (P==Bone) Pose[I]=Pose[I].GetRelativeTransform(Before)*Value;
        }
        Pose[Bone]=Value;
    };
    auto Rotate=[&](FName Name,const FVector& Axis,float Angle)
    { const int32 I=Index(Name); if (I!=INDEX_NONE) {FTransform T=Pose[I];T.SetRotation((FQuat(Axis,Angle)*T.GetRotation()).GetNormalized());Set(I,T);} };
    const int32 Pelvis=Index(TEXT("pelvis")),Chest=Index(TEXT("chest"));
    auto UpdateArch=[&]()
    {
        // Shared chest-to-pelvis field for both rails, including flight pitch.
        const FVector C=Original[Chest].GetLocation(),P=Original[Pelvis].GetLocation(),Axis=P-C;
        const double Denom=FMath::Max(1.,Axis.SizeSquared());
        for (const auto& Entry:Indices)
        {
            if (!Entry.Key.ToString().StartsWith(TEXT("arch_"))) continue;
            const int32 I=Entry.Value;
            const float T=Ease(float(FVector::DotProduct(Original[I].GetLocation()-C,Axis)/Denom));
            const FTransform Front=Original[I].GetRelativeTransform(Original[Chest])*Pose[Chest];
            const FTransform Rear=Original[I].GetRelativeTransform(Original[Pelvis])*Pose[Pelvis];
            Pose[I].Blend(Front,Rear,T);
            const float Envelope=16.f*T*T*(1.f-T)*(1.f-T);
            const FVector Lag=ArchMotion-StepMotion;
            Pose[I].AddToTranslation((RightCS*(1.1f*Lag.X)+UpCS*(.9f*Lag.Z))*Envelope);
            Pose[I].SetRotation((FQuat(UpCS,.010f*Lag.X*Envelope)*FQuat(RightCS,.012f*Lag.Y*Envelope)*Pose[I].GetRotation()).GetNormalized());
        }
    };
    if (FlightOnly)
    {
        // Spread path alignment through the axial chain; the head retains
        // some forward stabilization instead of rotating as one solid body.
        Rotate(TEXT("pelvis"),RightCS,-FlightPitch*.60f);
        Rotate(TEXT("spine_01"),RightCS,-FlightPitch*.20f);
        Rotate(TEXT("chest"),RightCS,-FlightPitch*.20f);
        Rotate(TEXT("neck"),RightCS,FlightPitch*.25f);
        UpdateArch();
        for (int32 I=0;I<Pose.Num();++I) Out.Emplace(FCompactPoseBoneIndex(I),Pose[I]);
        return;
    }
    FTransform Body=Pose[Pelvis];
    Body.AddToTranslation(BodyOffset+RightCS*(.65f*StepMotion.X)+ForwardCS*(.85f*StepMotion.Y)+UpCS*(.60f*StepMotion.Z));
    Set(Pelvis,Body);
    Rotate(TEXT("pelvis"),RightCS,-Pitch*.5f+.018f*StepMotion.Y);
    Rotate(TEXT("pelvis"),UpCS,-.015f*StepMotion.X);
    Rotate(TEXT("pelvis"),ForwardCS,.018f*StepMotion.X);
    Rotate(TEXT("spine_01"),UpCS,-Turn*.022f+.022f*StepMotion.X);
    Rotate(TEXT("spine_01"),ForwardCS,-.014f*StepMotion.X);
    Rotate(TEXT("spine_01"),RightCS,-.010f*StepMotion.Y);
    Rotate(TEXT("spine_02"),UpCS,-Turn*.018f+.024f*StepMotion.X);
    Rotate(TEXT("spine_02"),ForwardCS,-.012f*StepMotion.X);
    Rotate(TEXT("spine_02"),RightCS,-.010f*StepMotion.Y);
    Rotate(TEXT("chest"),RightCS,-Pitch*.5f+.025f*StepMotion.Y-.018f*StepMotion.Z);
    Rotate(TEXT("chest"),UpCS,.024f*StepMotion.X);
    Rotate(TEXT("chest"),ForwardCS,-.018f*StepMotion.X);
    Rotate(TEXT("neck"),UpCS,Turn*.065f+.045f*NeckMotion.X-.025f*StepMotion.X);
    Rotate(TEXT("neck"),RightCS,-.030f*NeckMotion.Y+.028f*NeckMotion.Z);
    Rotate(TEXT("neck"),ForwardCS,.014f*NeckMotion.X);
    Rotate(TEXT("head"),UpCS,Turn*.035f+.040f*HeadMotion.X-.015f*NeckMotion.X);
    Rotate(TEXT("head"),RightCS,.025f*HeadMotion.Y+.022f*HeadMotion.Z);
    Rotate(TEXT("head"),ForwardCS,.010f*HeadMotion.X);
    if (CannonSupport && !MouthSamples.IsEmpty())
    {
        const int32 Neck=Index(TEXT("neck"));
        auto Under=[&](int32 Bone,int32 Ancestor)
        {
            if (Ancestor==INDEX_NONE) return false;
            while (Bone!=INDEX_NONE) { if (Bone==Ancestor) return true; Bone=Parents[Bone]; }
            return false;
        };
        float Lift=0.f;
        for (const auto& Sample:MouthSamples)
        {
            FVector Point=FVector::ZeroVector;
            float MovedWeight=0.f;
            for (int32 J=0;J<Sample.Count;++J)
            {
                const int32 Bone=Index(Sample.Bones[J]);
                if (Bone==INDEX_NONE) continue;
                Point+=Pose[Bone].TransformPosition(Sample.Local[J])*Sample.Weights[J];
                MovedWeight+=Sample.Weights[J]*((Under(Bone,Chest)?.65f:0.f)+(Under(Bone,Neck)?.35f:0.f));
            }
            const FMouthPlane* Nearest=nullptr;
            double Distance=TNumericLimits<double>::Max();
            for (const auto& Plane:MouthPlanes)
            {
                if (!Plane.Valid) continue;
                const double D=FVector::VectorPlaneProject(Point-Plane.Point,UpCS).SizeSquared();
                if (D<Distance) { Distance=D; Nearest=&Plane; }
            }
            if (!Nearest || MovedWeight<.1f) continue;
            const float Clearance=FVector::DotProduct(Point-Nearest->Point,Nearest->Normal);
            const float Response=MovedWeight*FVector::DotProduct(UpCS,Nearest->Normal);
            Lift=FMath::Max(Lift,(3.f-Clearance)/FMath::Max(.1f,Response));
        }
        // Share the adjustment through the chest and neck, then re-solve the
        // feet below. A lower-jaw skin sample, not the head pivot, sets clearance.
        Lift=FMath::Clamp(Lift,0.f,35.f);
        FTransform T=Pose[Chest]; T.AddToTranslation(UpCS*(Lift*.65f)); Set(Chest,T);
        if (Neck!=INDEX_NONE) { T=Pose[Neck]; T.AddToTranslation(UpCS*(Lift*.35f)); Set(Neck,T); }
    }
    for (int32 I=0; I<4; ++I)
    {
        const auto& F=Feet[I]; if (!F.Planted && !F.Swing) continue;
        const int32 U=Index(UpperNames[I]),L=Index(LowerNames[I]),A=Index(AnkleNames[I]),E=Index(FootNames[I]);
        const FString Side=I%2==0?TEXT("L"):TEXT("R");
        if (I<2)
        {
            const int32 Shoulder=Index(FName(TEXT("scapula_")+Side));
            if (Shoulder!=INDEX_NONE)
            {
                FTransform T=Pose[Shoulder];
                const float Reach=FVector::DotProduct(F.GoalCS-F.Reference,ForwardCS);
                T.AddToTranslation(ForwardCS*FMath::Clamp(Reach*.13f,-4.f,4.f)
                    +UpCS*MoveWeight*(.9f*F.Curl-1.2f*F.Load)); Set(Shoulder,T);
            }
        }
        FTransform Upper=Pose[U],Lower=Pose[L],Ankle=Pose[A];
        const float L1=FVector::Distance(Upper.GetLocation(),Lower.GetLocation()),L2=FVector::Distance(Lower.GetLocation(),Ankle.GetLocation());
        const float L3=I<2?0.f:FVector::Distance(Ankle.GetLocation(),Pose[E].GetLocation());
        const FVector Root=Upper.GetLocation();
        FVector Goal=F.GoalCS;
        FVector Direction=(Goal-Root).GetSafeNormal();
        const float Distance=FMath::Clamp(float(FVector::Distance(Goal,Root)),FMath::Abs(L1-L2)+1.f,(L1+L2)*.975f+L3);
        Goal=Root+Direction*Distance;
        FVector AnkleGoal=I<2?Goal:Goal-F.Hock*L3;
        if (I>=2 && FVector::Distance(AnkleGoal,Root)>(L1+L2)*.975f)
        {
            const float R=(L1+L2)*.975f;
            const float Along=(R*R-L3*L3+Distance*Distance)/(2.f*Distance);
            const FVector Center=Root+Direction*Along;
            FVector Across=FVector::VectorPlaneProject(AnkleGoal-Center,Direction).GetSafeNormal();
            if (Across.IsNearlyZero()) Across=FVector::VectorPlaneProject(UpCS,Direction).GetSafeNormal();
            AnkleGoal=Center+Across*FMath::Sqrt(FMath::Max(0.f,R*R-Along*Along));
        }
        const FVector Axis=(AnkleGoal-Root).GetSafeNormal();
        FVector Bend=FVector::VectorPlaneProject(F.Pole,Axis).GetSafeNormal();
        if (Bend.IsNearlyZero()) Bend=FVector::VectorPlaneProject(RightCS*(I%2==0?-1.f:1.f)+UpCS,Axis).GetSafeNormal();
        AnimationCore::SolveTwoBoneIK(Upper,Lower,Ankle,Root+Bend*(L1+L2),AnkleGoal,false,1.,1.);
        Set(U,Upper);Set(L,Lower);Set(A,Ankle);
        if (I>=2)
        {
            FTransform H=Pose[A]; const FVector Before=(Pose[E].GetLocation()-H.GetLocation()).GetSafeNormal();
            H.SetRotation((FQuat::FindBetweenNormals(Before,(Goal-H.GetLocation()).GetSafeNormal())*H.GetRotation()).GetNormalized()); Set(A,H);
        }
        FTransform Foot=Pose[E]; Foot.SetRotation((FQuat(RightCS,.14f*F.Curl)*F.RotationCS).GetNormalized()); Set(E,Foot);
        if (I<2)
            for (int32 Digit=1; Digit<=5; ++Digit)
                for (int32 Joint=1; Joint<=2; ++Joint)
                    Rotate(FName(*FString::Printf(TEXT("finger%d_%02d_%s"),Digit,Joint,*Side)),RightCS,F.Curl*(Joint==1?.08f:.20f)*(1.f-.07f*(Digit-1)));
        else for (int32 Digit=1; Digit<=3; ++Digit)
            Rotate(FName(*FString::Printf(TEXT("toe%d_%s"),Digit,*Side)),RightCS,.10f*F.Curl);
        // Correct the V03 twist/support helpers after solving their parent chains.
        auto Helper=[&](const FString& Name,int32 First,int32 Second,float Position,float Rotation)
        {
            const int32 H=Index(FName(Name)); if (H==INDEX_NONE) return;
            const FQuat QA=Pose[First].GetRotation()*Original[First].GetRotation().Inverse();
            const FQuat QB=Pose[Second].GetRotation()*Original[Second].GetRotation().Inverse();
            FTransform T=Pose[H];T.SetLocation(FMath::Lerp(Pose[First].GetLocation(),Pose[Second].GetLocation(),Position));
            T.SetRotation((FQuat::Slerp(QA,QB,Rotation)*Original[H].GetRotation()).GetNormalized());Set(H,T);
        };
        if (I<2)
        {
            Helper(TEXT("upperarm_twist_")+Side,U,L,.5f,.30f);
            Helper(TEXT("forearm_twist_")+Side,L,E,.5f,.30f);
            Helper(TEXT("elbow_support_")+Side,U,L,1.f,.5f);
        }
        else Helper(TEXT("knee_support_")+Side,U,L,1.f,.5f);
    }
    UpdateArch();
    for (int32 I=0; I<Pose.Num(); ++I)
    {
        FTransform Result;Result.Blend(Original[I],Pose[I],CorrectionWeight);
        Out.Emplace(FCompactPoseBoneIndex(I),Result);
    }
}
