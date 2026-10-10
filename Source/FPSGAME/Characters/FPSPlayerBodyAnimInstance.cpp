#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyPoses.h"
#include "FPSBodyGrounding.h"
#include "FPSBodyMeleePose.h"
#include "FPSBodySwordMotion.h"
#include "FPSBodyHandAttackMotion.h"
#include "FPSBodyHandAttackData.h"
#include "FPSBodyStaffCastData.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/BoneReference.h"
#include "Components/SkeletalMeshComponent.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "TwoBoneIK.h"

namespace FPSBodyAnimation
{
static float Ease(float T) { T=FMath::Clamp(T,0.f,1.f); return T*T*(3.f-2.f*T); }
static constexpr float CrouchStrideScale=.72f;
static constexpr float CrouchLiftScale=.45f;

// Preserve the incoming library pose when terrain IK adjusts its end point.
// The generic arm solver remains unchanged; legs also need pelvis/reach handling.
struct FLegReference
{
    FVector Hip=FVector::ZeroVector,Knee=FVector::ZeroVector,Ankle=FVector::ZeroVector;
    float Reach=0.f;
    void Set(const FVector& H,const FVector& K,const FVector& F)
    {
        Hip=H;Knee=K;Ankle=F;
        const float Length=float(FVector::Distance(H,K)+FVector::Distance(K,F));
        // Half a centimetre of compliance, with a small extension reserve even
        // at the source's straightest contact frame (about 11 degrees of flex).
        Reach=FMath::Min(float(FVector::Distance(H,F))+.5f,Length*.995f);
    }
    FVector Pole(const FVector& NewHip,const FVector& Target) const
    {
        const FVector OldAxis=(Ankle-Hip).GetSafeNormal(),NewAxis=(Target-NewHip).GetSafeNormal();
        FVector Bend=(Knee-Hip)-OldAxis*FVector::DotProduct(Knee-Hip,OldAxis);
        Bend=FQuat::FindBetweenNormals(OldAxis,NewAxis).RotateVector(Bend);
        if(!Bend.Normalize())
            Bend=(FVector::RightVector-NewAxis*FVector::DotProduct(FVector::RightVector,NewAxis)).GetSafeNormal();
        return NewHip+Bend*80.f;
    }
    FVector Reachable(const FVector& NewHip,const FVector& Target) const
    {
        FVector D=Target-NewHip;
        // Keep the tread height first; discard excess horizontal foot-lock
        // displacement. Only an unreachable vertical step needs a height clamp.
        D.Z=FMath::Clamp(D.Z,-double(Reach)*.999,double(Reach)*.999);
        const double Radius=FMath::Sqrt(FMath::Max(0.,FMath::Square(double(Reach))-D.Z*D.Z));
        const double Horizontal=D.Size2D();
        if(Horizontal>Radius&&Horizontal>UE_SMALL_NUMBER){D.X*=Radius/Horizontal;D.Y*=Radius/Horizontal;}
        return NewHip+D;
    }
};

// Template clips contain different numbers of strides and start on different feet.
// Phase 0 is a left-foot contact, .5 a right-foot contact, for every blended clip.
struct FStrideTiming
{
    float Length=1.f;
    float RootSpeed=0.f;
    TArray<float> Left,Right;
    explicit FStrideTiming(const UAnimSequence* Clip,const UAnimSequence* PhaseReference=nullptr)
    {
        if(!Clip)return;
        Length=FMath::Max(Clip->GetPlayLength(),SMALL_NUMBER);
        // Read the baked root displacement only to match cadence. The capsule
        // still owns movement; this does not enable or apply root motion.
        const FVector Start=Clip->ExtractRootTrackTransform(FAnimExtractContext(0.,false),nullptr).GetTranslation();
        const FVector End=Clip->ExtractRootTrackTransform(FAnimExtractContext(double(Length),false),nullptr).GetTranslation();
        RootSpeed=float((End-Start).Size2D())/Length;
        // Four derived rifle diagonals omit markers but retain their forward/back
        // source foot trajectories and duration. Use that source's contact timing.
        const UAnimSequence* MarkerSource=Clip->AuthoredSyncMarkers.IsEmpty()&&PhaseReference?PhaseReference:Clip;
        const float TimeScale=Length/FMath::Max(MarkerSource->GetPlayLength(),SMALL_NUMBER);
        for(const auto& Marker:MarkerSource->AuthoredSyncMarkers)
        {
            if(Marker.MarkerName==TEXT("L"))Left.Add(Marker.Time*TimeScale);
            else if(Marker.MarkerName==TEXT("R"))Right.Add(Marker.Time*TimeScale);
        }
        Left.Sort();Right.Sort();
    }
    float Duration() const {return Length/FMath::Max(Left.Num(),1);}
    float Speed(float Fallback) const {return RootSpeed>1.f?RootSpeed:Fallback;}
    float Sample(float Cycles) const
    {
        if(Left.IsEmpty()||Right.IsEmpty())return FMath::Fmod(Cycles,1.f)*Length;
        const int32 Cycle=FMath::FloorToInt(Cycles)%Left.Num();
        const float Start=Left[Cycle];
        const float End=Cycle+1<Left.Num()?Left[Cycle+1]:Left[0]+Length;
        float Middle=(Start+End)*.5f;
        for(const float Contact:Right)
        {
            const float Time=Contact>Start?Contact:Contact+Length;
            if(Time>Start&&Time<End){Middle=Time;break;}
        }
        const float Phase=FMath::Frac(Cycles);
        const float Time=Phase<.5f?FMath::Lerp(Start,Middle,Phase*2.f):FMath::Lerp(Middle,End,(Phase-.5f)*2.f);
        return FMath::Fmod(Time,Length);
    }
};

// Blend upper-body local transforms only; feet keep the independent movement cycle.
struct FUpperLayer : FAnimNode_Base
{
    FPoseLink Base, Upper;
    float Weight = 0.f;
    TArray<FCompactPoseBoneIndex> UpperBones;
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& C) override { Base.Initialize(C); Upper.Initialize(C); }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {
        Base.CacheBones(C); Upper.CacheBones(C); UpperBones.Reset();
        const auto& Bones=C.AnimInstanceProxy->GetRequiredBones();
        const auto& Ref=Bones.GetReferenceSkeleton();
        const int32 Spine=Ref.FindBoneIndex(TEXT("spine_01"));
        for(int32 I=0;I<Bones.GetCompactPoseNumBones();++I)
        {
            const FCompactPoseBoneIndex Compact(I);
            for(int32 Parent=Bones.GetSkeletonIndex(Compact);Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))
                if(Parent==Spine){UpperBones.Add(Compact);break;}
        }
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& C) override { Base.Update(C); Upper.Update(C); }
    virtual void Evaluate_AnyThread(FPoseContext& Out) override
    {
        Base.Evaluate(Out);
        if(Weight<=ZERO_ANIMWEIGHT_THRESH)return;
        FPoseContext Overlay(Out); Upper.Evaluate(Overlay);
        for(const auto Bone:UpperBones)
        {
            FTransform Blended; Blended.Blend(Out.Pose[Bone],Overlay.Pose[Bone],Weight);
            Out.Pose[Bone]=Blended;
        }
    }
};

// Small world-body corrections. Bone transforms are derived locally, never replicated.
struct FControls : FAnimNode_Base
{
    FPoseLink Source,Neutral,Grip,Sword,StaffCast,StaffCarry,BookCarry,BookPush,Consume;
    bool bStaffCarryActive=false,bStaffNativeCast=false,bStaffNativeArmApplied=false;
    bool bStaffNativeStrike=false,bStaffQuickCarry=false;
    TArray<uint8> StaffMotionBones;
    TArray<uint8> BookMotionBones;
    bool bBookCarryActive=false,bHadBookCarry=false;
    float BookCarryAge=0.f;
    TArray<FTransform> LastBookCarryPose,BookCarryEntryPose;
    bool bBookPushActive=false,bHadBookPush=false;
    float BookPushProgress=0.f,LastBookPushProgress=0.f,BookPushEntryProgress=0.f;
    TArray<FTransform> BookPushEntryDelta;
    bool bStaffCastActive=false,bHadStaffCast=false;
    FName StaffCastPhase,LastStaffCastPhase;
    float StaffCastProgress=0.f,LastStaffCastProgress=0.f,StaffCastEntryProgress=0.f;
    TArray<FTransform> LastStaffCastPose,StaffCastEntryPose;
    FTransform LastStaffCastChest=FTransform::Identity,StaffCastEntryChest=FTransform::Identity;
    float ConsumeWeight=0.f,ConsumeContactWeight=0.f;
    bool bHasConsumeProp=false,bConsumeNativeArm=false;
    FVector ConsumeMouthInHead=FVector::ZeroVector,ConsumePropContact=FVector::ZeroVector;
    TArray<uint8> ConsumeBones;
    float SwordWeight=0.f,SwordLegWeight=0.f,SwordTransitionAge=1.f,SwordAttackLegOwnership=0.f;
    float LastSwordGripRoll=0.f,SwordEntryGripRoll=0.f;
    float LastSwordGripSlide=0.f,SwordEntryGripSlide=0.f;
    float SwordSupportThumbWeight=0.f;
    bool bSwordChanged=false,bSwordNativeGrip=false;
    TArray<uint8> SwordUpperBones;
    // The existing grounded library mixer also hosts single-hand combat.
    TArray<uint8> LibraryArmBones;
    uint8 LibraryPreserveHands=0;
    bool bHandAttackLibrary=false,bStaffAttackLibrary=false;
    TArray<FTransform> LastSwordPose,SwordEntryPose;
    TArray<FCompactPoseBoneIndex> GripBones[2];
    TArray<uint8> SwordSupportThumbBones;
    TArray<FCompactPoseBoneIndex> StaffArmHelpers;
    float GripWeights[2]={0.f,0.f};
    bool bSwordGrip=false;
    TArray<FTransform> EquipmentFingers;
    uint8 EquipmentGripHands=0;
    bool bBowPose=false;
    FTransform BowHands[2];
    FQuat StaffHandRotation=FQuat::Identity;
    TArray<FTransform> ActionFingers;
    FTransform ActionHands[2];
    uint8 ActionFingerMask=0,ActionWristMask=0;
    bool bCoupledActionWrists=false;
    FBoneReference Pelvis, Spine, ChestBase, Head, Hands[2], Feet[2],Toes[2];
    FFPSBodyGroundPose Ground;
    FFPSBodyFootSeed RawFeet[2];
    FQuat ToeRest[2]={FQuat::Identity,FQuat::Identity};
    float GaitPhase=0.f;
    FFPSBodyReactionState Reactions;
    FVector HitDirection=FVector(0,-1,0),PushDirection=FVector(0,-1,0);
    float StunBlend=0.f;
    bool bFalling=false;
    FFPSBodyState State;
    FFPSBodyState MotionState;
    float Clock=0.f,Crouch=0.f,MotionWeight=0.f,Aim=0.f,Sprint=0.f,Delta=0.f;
    FVector Handholds[2];
    FVector PoseScale=FVector::OneVector;
    FTransform LastHands[2],EntryHands[2];
    FTransform LastSwordTorso=FTransform::Identity;
    FTransform SwordRestTorso=FTransform::Identity;
    bool bHadSwordPair=false,bHasSwordRestTorso=false;
    FTransform CastRecoveryEntry=FTransform::Identity;
    float CastRecoveryStartProgress=0.f;
    EFPSBodyAction LastAction=EFPSBodyAction::None;
    FName LastVariant;
    bool bHasHandHistory=false;
    float HandBlendAge=1.f;
    uint8 LastActionWristMask=0;
    FTransform LeftGrip=FTransform::Identity;
    bool bLeftGrip=false;
    FControls()
    {
        Pelvis.BoneName=TEXT("pelvis");Spine.BoneName=TEXT("spine_03");
        ChestBase.BoneName=TEXT("spine_01");Head.BoneName=TEXT("head");
        Hands[0].BoneName=TEXT("hand_r");Hands[1].BoneName=TEXT("hand_l");
        Feet[0].BoneName=TEXT("foot_r");Feet[1].BoneName=TEXT("foot_l");
        Toes[0].BoneName=TEXT("ball_r");Toes[1].BoneName=TEXT("ball_l");
    }
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& C) override { Source.Initialize(C);Neutral.Initialize(C);Grip.Initialize(C);Sword.Initialize(C);StaffCast.Initialize(C);StaffCarry.Initialize(C);BookCarry.Initialize(C);BookPush.Initialize(C);Consume.Initialize(C); }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& C) override
    {
        Source.CacheBones(C);Neutral.CacheBones(C);Grip.CacheBones(C);Sword.CacheBones(C);StaffCast.CacheBones(C);StaffCarry.CacheBones(C);BookCarry.CacheBones(C);BookPush.CacheBones(C);Consume.CacheBones(C);bHasHandHistory=false;bHadSwordPair=false;bHasSwordRestTorso=false;const auto& Bones=C.AnimInstanceProxy->GetRequiredBones();
        bHadBookCarry=false;BookCarryAge=0.f;LastBookCarryPose.Reset();BookCarryEntryPose.Reset();
        bHadBookPush=false;BookPushEntryDelta.Reset();
        bHadStaffCast=false;LastStaffCastPose.Reset();StaffCastEntryPose.Reset();
        Pelvis.Initialize(Bones);Spine.Initialize(Bones);ChestBase.Initialize(Bones);Head.Initialize(Bones);
        for(auto& B:Hands)B.Initialize(Bones);for(auto& B:Feet)B.Initialize(Bones);for(auto& B:Toes)B.Initialize(Bones);
        const auto& Ref=Bones.GetReferenceSkeleton();
        StaffArmHelpers.Reset();
        const int32 StaffUpper=Ref.FindBoneIndex(TEXT("upperarm_r"));
        const int32 StaffLower=Ref.FindBoneIndex(TEXT("lowerarm_r"));
        const int32 StaffHand=Ref.FindBoneIndex(TEXT("hand_r"));
        if(StaffUpper!=INDEX_NONE&&StaffHand!=INDEX_NONE)
            for(int32 I=0;I<Bones.GetCompactPoseNumBones();++I)
            {
                const FCompactPoseBoneIndex Bone(I);
                const int32 MeshBone=Bones.MakeMeshPoseIndex(Bone).GetInt();
                if(MeshBone!=StaffLower&&MeshBone!=StaffHand&&Ref.BoneIsChildOf(MeshBone,StaffUpper)
                    &&!Ref.BoneIsChildOf(MeshBone,StaffHand))StaffArmHelpers.Add(Bone);
            }
        LastSwordPose.Reset();SwordEntryPose.Reset();LastSwordGripRoll=0.f;SwordEntryGripRoll=0.f;
        LastSwordGripSlide=0.f;SwordEntryGripSlide=0.f;
        SwordUpperBones.Init(0,Bones.GetCompactPoseNumBones());
        LibraryArmBones.Init(0,Bones.GetCompactPoseNumBones());
        const int32 UpperRoot=Ref.FindBoneIndex(TEXT("spine_01"));
        const int32 ArmRoots[2]={Ref.FindBoneIndex(TEXT("clavicle_r")),Ref.FindBoneIndex(TEXT("clavicle_l"))};
        for(int32 I=0;I<LibraryArmBones.Num();++I)
            for(int32 Parent=Bones.MakeMeshPoseIndex(FCompactPoseBoneIndex(I)).GetInt();Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))
                for(int32 Side=0;Side<2;++Side)if(Parent==ArmRoots[Side])LibraryArmBones[I]|=1<<Side;
        StaffMotionBones.Init(0,Bones.GetCompactPoseNumBones());
        BookMotionBones.Init(0,Bones.GetCompactPoseNumBones());
        const int32 BookHand=Ref.FindBoneIndex(TEXT("hand_l"));
        for(int32 I=0;I<StaffMotionBones.Num();++I)
        {
            const int32 MeshBone=Bones.MakeMeshPoseIndex(FCompactPoseBoneIndex(I)).GetInt();
            StaffMotionBones[I]=(LibraryArmBones[I]&1)&&StaffHand!=INDEX_NONE&&
                (MeshBone==StaffHand||!Ref.BoneIsChildOf(MeshBone,StaffHand));
            BookMotionBones[I]=(LibraryArmBones[I]&2)&&BookHand!=INDEX_NONE&&
                (MeshBone==BookHand||!Ref.BoneIsChildOf(MeshBone,BookHand));
        }
        for(int32 I=0;I<SwordUpperBones.Num();++I)
            for(int32 Parent=Bones.MakeMeshPoseIndex(FCompactPoseBoneIndex(I)).GetInt();Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))
                if(Parent==UpperRoot){SwordUpperBones[I]=1;break;}
        ConsumeBones=SwordUpperBones;
        const int32 RightClavicle=Ref.FindBoneIndex(TEXT("clavicle_r"));
        for(int32 I=0;I<ConsumeBones.Num();++I)
            for(int32 Parent=Bones.MakeMeshPoseIndex(FCompactPoseBoneIndex(I)).GetInt();Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))
                if(Parent==RightClavicle){ConsumeBones[I]=0;break;}
        for(int32 I=0;I<2;++I)
        {
            RawFeet[I]=FFPSBodyFootSeed();
            FTransform Reference=FTransform::Identity;
            for(int32 B=Ref.FindBoneIndex(Feet[I].BoneName);B!=INDEX_NONE;B=Ref.GetParentIndex(B))Reference=Reference*Ref.GetRefBonePose()[B];
            RawFeet[I].SoleHeight=FMath::Clamp(float(Reference.GetLocation().Z),3.f,18.f);
            RawFeet[I].SoleUpLocal=Reference.GetRotation().UnrotateVector(FVector::UpVector);
            const int32 ToeIndex=Ref.FindBoneIndex(Toes[I].BoneName);
            ToeRest[I]=ToeIndex!=INDEX_NONE?Ref.GetRefBonePose()[ToeIndex].GetRotation():FQuat::Identity;
        }
        SwordSupportThumbBones.Init(0,Bones.GetCompactPoseNumBones());
        for(int32 Side=0;Side<2;++Side)
        {
            GripBones[Side].Reset();
            const int32 Hand=Ref.FindBoneIndex(Hands[Side].BoneName);
            if(Hand==INDEX_NONE)continue;
            for(int32 I=0;I<Bones.GetCompactPoseNumBones();++I)
            {
                const FCompactPoseBoneIndex Bone(I);
                // Include MetaHuman metacarpals and weighted finger helpers,
                // excluding the wrist whose contact remains owned by body IK.
                for(int32 Parent=Ref.GetParentIndex(Bones.MakeMeshPoseIndex(Bone).GetInt());Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))
                    if(Parent==Hand)
                    {
                        GripBones[Side].Add(Bone);
                        if(Side==1&&Ref.GetBoneName(Bones.MakeMeshPoseIndex(Bone).GetInt()).ToString().StartsWith(TEXT("thumb_")))
                            SwordSupportThumbBones[I]=1;
                        break;
                    }
            }
        }
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& C) override { Source.Update(C);Neutral.Update(C);Grip.Update(C);if(SwordWeight>ZERO_ANIMWEIGHT_THRESH)Sword.Update(C);if(bStaffCastActive)StaffCast.Update(C);if(bStaffCarryActive)StaffCarry.Update(C);if(bBookCarryActive)BookCarry.Update(C);if(bBookPushActive)BookPush.Update(C);if(ConsumeWeight>ZERO_ANIMWEIGHT_THRESH)Consume.Update(C); }
    void BlendStaffCarry(FPoseContext& Out,FCSPose<FCompactPose>& Pose);
    void BlendStaffStrike(FPoseContext& Out,FCSPose<FCompactPose>& Pose);
    void AnchorStaffArm(FPoseContext& Authored,FCSPose<FCompactPose>& Pose,int32 Side=0);
    void BlendBookCarry(FPoseContext& Out,FCSPose<FCompactPose>& Pose);
    void BlendStaffCast(FPoseContext& Out,FCSPose<FCompactPose>& Pose);
    void FitStaffArm(FCSPose<FCompactPose>& Pose);
    void BlendSword(FPoseContext& Out,FCSPose<FCompactPose>& Pose);
    void BlendConsume(FPoseContext& Out,FCSPose<FCompactPose>& Pose);
    static void Solve(FCSPose<FCompactPose>& Pose,const FBoneReference& End,const FTransform& Target,const FVector& Pole,float Weight)
    {
        const auto& Bones=Pose.GetPose().GetBoneContainer();if(!End.IsValidToEvaluate(Bones)||Weight<=0.f)return;
        const auto E=End.GetCompactPoseIndex(Bones), J=Bones.GetParentBoneIndex(E);
        if(J==INDEX_NONE)return;
        const auto R=Bones.GetParentBoneIndex(J);if(R==INDEX_NONE)return;
        FTransform Root=Pose.GetComponentSpaceTransform(R), Joint=Pose.GetComponentSpaceTransform(J), Tip=Pose.GetComponentSpaceTransform(E);
        const double Upper=FVector::Distance(Root.GetLocation(),Joint.GetLocation()),Lower=FVector::Distance(Joint.GetLocation(),Tip.GetLocation());
        AnimationCore::SolveTwoBoneIK(Root,Joint,Tip,Pole,Target.GetLocation(),Upper,Lower,false,1.,1.);
        Tip.SetRotation(Target.GetRotation());
        TArray<FBoneTransform,TInlineAllocator<3>> Changes;
        Changes.Emplace(R,Root);Changes.Emplace(J,Joint);Changes.Emplace(E,Tip);
        Pose.LocalBlendCSBoneTransforms(Changes,Weight);
    }
    void FitHandPair(FCSPose<FCompactPose>& Pose,FTransform (&Targets)[2]) const
    {
        const auto& Bones=Pose.GetPose().GetBoneContainer();
        FVector Center[2];double Radius[2];
        for(int32 I=0;I<2;++I)
        {
            const auto Wrist=Hands[I].GetCompactPoseIndex(Bones),Elbow=Bones.GetParentBoneIndex(Wrist),Shoulder=Bones.GetParentBoneIndex(Elbow);
            const FVector H=Pose.GetComponentSpaceTransform(Shoulder).GetLocation();
            const FVector E=Pose.GetComponentSpaceTransform(Elbow).GetLocation();
            const FVector W=Pose.GetComponentSpaceTransform(Wrist).GetLocation();
            // Reserve elbow bend; do not stretch native arm bones. A shared
            // translation preserves the donor's palms, finger poses and spacing.
            Radius[I]=(FVector::Distance(H,E)+FVector::Distance(E,W))*.965;
            Center[I]=H-Targets[I].GetLocation();
        }
        const auto Inside=[&](const FVector& Shift,int32 I)
        {return FVector::DistSquared(Shift,Center[I])<=FMath::Square(Radius[I])+.0001;};
        if(Inside(FVector::ZeroVector,0)&&Inside(FVector::ZeroVector,1))return;
        const FVector A=Center[0]+(-Center[0]).GetClampedToMaxSize(Radius[0]);
        const FVector B=Center[1]+(-Center[1]).GetClampedToMaxSize(Radius[1]);
        FVector Shift;
        const bool FitsA=Inside(A,1),FitsB=Inside(B,0);
        if(FitsA||FitsB)Shift=FitsA&&(!FitsB||A.SizeSquared()<=B.SizeSquared())?A:B;
        else
        {
            // Nearest point on the intersection circle of the two arm-reach
            // spheres. Unlike separate wrist clamping, this keeps both contacts.
            const FVector Between=Center[1]-Center[0];const double Distance=Between.Size();
            if(Distance<=UE_SMALL_NUMBER||Distance>Radius[0]+Radius[1])return;
            const FVector Axis=Between/Distance;
            const double Along=(FMath::Square(Radius[0])-FMath::Square(Radius[1])+Distance*Distance)/(2.*Distance);
            const FVector Circle=Center[0]+Axis*Along;
            const double CircleRadius=FMath::Sqrt(FMath::Max(0.,FMath::Square(Radius[0])-Along*Along));
            FVector Toward=-Circle+Axis*FVector::DotProduct(Circle,Axis);
            if(!Toward.Normalize())
            {FVector Other;Axis.FindBestAxisVectors(Toward,Other);}
            Shift=Circle+Toward*CircleRadius;
        }
        for(auto& Target:Targets)Target.AddToTranslation(Shift);
    }
    virtual void Evaluate_AnyThread(FPoseContext& Out) override
    {
        Source.Evaluate(Out);const auto& Bones=Out.Pose.GetBoneContainer();
        if(!Pelvis.IsValidToEvaluate(Bones)||!Spine.IsValidToEvaluate(Bones))return;
        FTransform FootTargets[2];FVector KneePoles[2];
        if(Crouch>ZERO_ANIMWEIGHT_THRESH)
        {
            FCSPose<FCompactPose> Before;Before.InitPose(Out.Pose);
            FPoseContext NeutralPose(Out);Neutral.Evaluate(NeutralPose);
            FCSPose<FCompactPose> NeutralCS;NeutralCS.InitPose(NeutralPose.Pose);
            for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
            {
                const auto Foot=Feet[I].GetCompactPoseIndex(Bones);
                const auto Knee=Bones.GetParentBoneIndex(Foot),Hip=Bones.GetParentBoneIndex(Knee);
                FootTargets[I]=Before.GetComponentSpaceTransform(Foot);
                const FTransform& Rest=NeutralCS.GetComponentSpaceTransform(Foot);
                const FVector Offset=FootTargets[I].GetLocation()-Rest.GetLocation();
                // Keep the source left/right contact timing, but use short, low
                // crouch steps around this weapon family's actual idle footprint.
                const FVector ShortStep=Rest.GetLocation()+Offset*FVector(CrouchStrideScale,CrouchStrideScale,CrouchLiftScale);
                FootTargets[I].SetLocation(FMath::Lerp(FootTargets[I].GetLocation(),ShortStep,Crouch));
                FootTargets[I].SetRotation(FQuat::Slerp(FootTargets[I].GetRotation(),Rest.GetRotation(),.75f*Crouch).GetNormalized());
                if(Toes[I].IsValidToEvaluate(Bones))
                {
                    const auto Toe=Toes[I].GetCompactPoseIndex(Bones);
                    Out.Pose[Toe].SetRotation(FQuat::Slerp(Out.Pose[Toe].GetRotation(),NeutralPose.Pose[Toe].GetRotation(),.75f*Crouch).GetNormalized());
                }
                // A foot-relative pole swings across the hip when strafing/backing
                // up. Keep each knee forward and slightly outside its own hip.
                const FVector HipPosition=Before.GetComponentSpaceTransform(Hip).GetLocation()+FVector(0,-6,-40)*PoseScale*Crouch;
                const FVector ForwardPole=HipPosition+FVector(FMath::Sign(Rest.GetLocation().X)*18.f,85.f,-25.f)*PoseScale;
                KneePoles[I]=FMath::Lerp(Before.GetComponentSpaceTransform(Knee).GetLocation(),ForwardPole,Crouch);
            }
        }
        Out.Pose[Pelvis.GetCompactPoseIndex(Bones)].AddToTranslation(FVector(0,-6.f,-40.f)*PoseScale*Crouch);
        FCSPose<FCompactPose> Pose;Pose.InitPose(Out.Pose);
        // Targets and pelvis already contain the crouch blend. Blending IK again
        // leaves the feet partway below their targets during crouch/stand changes.
        if(Crouch>ZERO_ANIMWEIGHT_THRESH)for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
            Solve(Pose,Feet[I],FootTargets[I],KneePoles[I],1.f);

        const auto Motion=MotionState.Motion;
        const float MT=MotionState.MotionProgress;
        const bool Traversing=FPSBodyPoses::Traversing(Motion);
        if(MotionWeight>ZERO_ANIMWEIGHT_THRESH)
        {
            FPoseContext RestPose(Out);Neutral.Evaluate(RestPose);
            FCSPose<FCompactPose> RestCS;RestCS.InitPose(RestPose.Pose);
            FVector Offset=FVector::ZeroVector;
            if(Motion==EFPSBodyMotion::Slide)Offset=FVector(0,-18,-22);
            else if(Motion==EFPSBodyMotion::Dodge)Offset=(MotionState.MotionDirection*10.f+FVector(0,0,-15))*FMath::Sin(PI*MT);
            else if(Traversing)Offset=FVector(0,-7,-14)*FMath::Sin(PI*MT);
            auto Hip=Pose.GetComponentSpaceTransform(Pelvis.GetCompactPoseIndex(Bones));
            Hip.AddToTranslation(Offset*PoseScale*MotionWeight);
            TArray<FBoneTransform,TInlineAllocator<1>> HipChange;HipChange.Emplace(Pelvis.GetCompactPoseIndex(Bones),Hip);
            Pose.LocalBlendCSBoneTransforms(HipChange,1.f);
            for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
            {
                auto Target=RestCS.GetComponentSpaceTransform(Feet[I].GetCompactPoseIndex(Bones));
                FVector FootOffset=FVector::ZeroVector;
                if(Motion==EFPSBodyMotion::Slide)
                    FootOffset=MotionState.MotionDirection*(I==0?66.f:18.f)+FVector(I==0?-6:6,0,I==0?4:9);
                else if(Motion==EFPSBodyMotion::Dodge)
                {
                    const int32 Lead=MotionState.MotionDirection.X<=0.f?0:1;
                    const float Step=FMath::Sin(PI*MT);
                    FootOffset=MotionState.MotionDirection*(I==Lead?34.f:-12.f)*Step+FVector(0,0,I==Lead?12.f:3.f)*Step;
                }
                else if(Traversing)
                {
                    const float Phase=FMath::Clamp((MT-(I==0?.1f:.3f))/(I==0?.7f:.65f),0.f,1.f);
                    const float Lift=FMath::Sin(PI*Phase);
                    FootOffset=FVector(I==0?-5:5,28*Lift,(Motion==EFPSBodyMotion::Vault?48.f:38.f)*Lift);
                }
                Target.AddToTranslation(FootOffset*PoseScale);
                FTransform Blended;Blended.Blend(Pose.GetComponentSpaceTransform(Feet[I].GetCompactPoseIndex(Bones)),Target,MotionWeight);
                Solve(Pose,Feet[I],Blended,FVector(I==0?-30:30,95,Hip.GetLocation().Z-20),1.f);
            }
        }
        const float T=FPSBodyPoses::Progress(State,Clock);
        const auto MeleePose=FPSBodyMelee::Sample(State,T);
        const bool MeleeActive=FPSBodyMelee::Active(State);
        const bool Dash=FPSBodyPoses::Dash(State);
        const float DashP=FPSBodyPoses::DashProgress(State,T),DashContact=FPSBodyPoses::DashContact(State);
        const float DashLoad=Dash?FPSBodyPoses::Pulse(DashP,DashContact):0.f;
        const float PushP=FMath::Clamp((Clock-Reactions.PushAt)/FMath::Max(.01f,Reactions.PushSeconds),0.f,1.f);
        const float Push=FPSBodyPoses::Pulse(PushP,.17f)*Reactions.PushStrength;
        const float Stun=State.Action==EFPSBodyAction::Dead?0.f:StunBlend;
        const bool Plantable=!bFalling&&State.Motion==EFPSBodyMotion::Ground&&State.Action!=EFPSBodyAction::Dead;
        // Keep the actor/capsule authoritative. Only the pelvis and leg pose
        // change; no root-motion extraction or synthetic travel is introduced.
        if(Plantable&&(MeleeActive||Push>0.f||Stun>0.f||Ground.TurnAlpha>0.f))
        {
            FTransform Targets[2];
            for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))Targets[I]=Pose.GetComponentSpaceTransform(Feet[I].GetCompactPoseIndex(Bones));
            const auto HipIndex=Pelvis.GetCompactPoseIndex(Bones);
            auto Hip=Pose.GetComponentSpaceTransform(HipIndex);const FVector Origin=Hip.GetLocation();
            const FVector Shift=(FVector(0,8,-9)*DashLoad+MeleePose.Pelvis+PushDirection*(4.f*Push)+FVector(0,0,-5)*Stun)*PoseScale;
            const FQuat Yaw(FVector::UpVector,FMath::DegreesToRadians(Ground.LowerYaw+MeleePose.HipYaw));
            Hip.SetRotation(Yaw*Hip.GetRotation());Hip.AddToTranslation(Shift);
            TArray<FBoneTransform,TInlineAllocator<1>> H;H.Emplace(HipIndex,Hip);Pose.LocalBlendCSBoneTransforms(H,1.f);
            if(ChestBase.IsValidToEvaluate(Bones))
            {
                const auto C=ChestBase.GetCompactPoseIndex(Bones);auto Chest=Pose.GetComponentSpaceTransform(C);
                const FQuat AimCounter(FVector::UpVector,FMath::DegreesToRadians(-Ground.LowerYaw));
                Chest.SetRotation(AimCounter*Chest.GetRotation());H.Reset();H.Emplace(C,Chest);Pose.LocalBlendCSBoneTransforms(H,1.f);
            }
            for(int32 I=0;I<2;++I)if(Feet[I].IsValidToEvaluate(Bones))
            {
                auto& Foot=Targets[I];Foot.SetLocation(Origin+Yaw.RotateVector(Foot.GetLocation()-Origin));
                Foot.SetRotation(Yaw*Foot.GetRotation());
                const float Step=I==0?FMath::Sin(PI*FMath::Clamp(DashP/FMath::Max(.1f,DashContact),0.f,1.f)):
                    FMath::Sin(PI*FMath::Clamp((DashP-DashContact)/(1.f-DashContact),0.f,1.f));
                FVector Offset(0,Dash?(I==0?24.f:-12.f)*DashLoad:0.f,Ground.TurnLift[I]+(Dash?FMath::Max(0.f,Step)*9.f:0.f));
                const float Stagger=FMath::Sin(PI*FMath::Clamp((PushP-(I==0?0.f:.3f))/(I==0?.65f:.7f),0.f,1.f));
                Offset+=PushDirection*(I==0?20.f:10.f)*Push+FVector(0,0,FMath::Max(0.f,Stagger)*8.f*Reactions.PushStrength*(Push>0.f?1.f:0.f));
                Foot.AddToTranslation((Offset+MeleePose.Feet[I])*PoseScale);
                Solve(Pose,Feet[I],Foot,Hip.GetLocation()+FVector(I==0?-24:24,75,-25)*PoseScale,1.f);
            }
        }
        // Capture pre-grounding feet. Tracing already corrected sockets creates
        // cumulative ankle/pelvis drift; the game thread uses only these seeds.
        FTransform GroundTargets[2];FLegReference GroundLegs[2];
        for(int32 I=0;I<2;++I)
        {
            RawFeet[I].bValid=Feet[I].IsValidToEvaluate(Bones);
            if(!RawFeet[I].bValid)continue;
            GroundTargets[I]=RawFeet[I].Ankle=Pose.GetComponentSpaceTransform(Feet[I].GetCompactPoseIndex(Bones));
            RawFeet[I].Toe=Toes[I].IsValidToEvaluate(Bones)?Pose.GetComponentSpaceTransform(Toes[I].GetCompactPoseIndex(Bones)).GetLocation():RawFeet[I].Ankle.GetLocation()+FVector(0,12,0);
            RawFeet[I].GaitPhase=GaitPhase;
            const auto Foot=Feet[I].GetCompactPoseIndex(Bones),Knee=Bones.GetParentBoneIndex(Foot),Hip=Bones.GetParentBoneIndex(Knee);
            GroundLegs[I].Set(Pose.GetComponentSpaceTransform(Hip).GetLocation(),
                Pose.GetComponentSpaceTransform(Knee).GetLocation(),RawFeet[I].Ankle.GetLocation());
            RawFeet[I].Hip=GroundLegs[I].Hip;RawFeet[I].ReachLimit=GroundLegs[I].Reach;
        }
        if(Plantable)
        {
            const bool PreserveGait=!MeleeActive&&Push<=ZERO_ANIMWEIGHT_THRESH&&Stun<=ZERO_ANIMWEIGHT_THRESH;
            float ExtraDrop=0.f;
            for(int32 I=0;I<2;++I)if(RawFeet[I].bValid)
            {
                GroundTargets[I].AddToTranslation(Ground.FootOffset[I]*Ground.Weight[I]);
                if(!PreserveGait||Ground.Weight[I]<=.001f)continue;
                const FVector H=GroundLegs[I].Hip+FVector(0,0,Ground.PelvisZ),F=GroundTargets[I].GetLocation();
                const double HeightSquared=FMath::Square(double(GroundLegs[I].Reach))-FVector::DistSquared2D(H,F);
                if(HeightSquared>0.)ExtraDrop=FMath::Max(ExtraDrop,float(H.Z-F.Z-FMath::Sqrt(HeightSquared)));
            }
            const auto HipIndex=Pelvis.GetCompactPoseIndex(Bones);auto Hip=Pose.GetComponentSpaceTransform(HipIndex);
            const float PelvisZ=Ground.PelvisZ-FMath::Clamp(ExtraDrop,0.f,12.f*float(PoseScale.Z));
            Hip.AddToTranslation(FVector(0,0,PelvisZ));
            TArray<FBoneTransform,TInlineAllocator<1>> H;H.Emplace(HipIndex,Hip);Pose.LocalBlendCSBoneTransforms(H,1.f);
            for(int32 I=0;I<2;++I)if(RawFeet[I].bValid&&Ground.Weight[I]>.001f)
            {
                auto Target=GroundTargets[I];
                const FVector LegHip=GroundLegs[I].Hip+FVector(0,0,PelvisZ);
                if(PreserveGait)Target.SetLocation(GroundLegs[I].Reachable(LegHip,Target.GetLocation()));
                const FVector SoleUp=Target.GetRotation().RotateVector(RawFeet[I].SoleUpLocal);
                const FVector SurfaceUp=Ground.FootTilt[I].RotateVector(FVector::UpVector);
                const FQuat Flat=FQuat::FindBetweenNormals(SoleUp,SurfaceUp);
                const FQuat Tilt=FQuat::Slerp(Ground.FootTilt[I],Flat,Ground.SolePlant[I]).GetNormalized();
                Target.SetRotation((FQuat::Slerp(FQuat::Identity,Tilt,Ground.Weight[I])*Target.GetRotation()).GetNormalized());
                const FVector Pole=PreserveGait?GroundLegs[I].Pole(LegHip,Target.GetLocation()):
                    Hip.GetLocation()+FVector(I==0?-24:24,80,-25)*PoseScale;
                Solve(Pose,Feet[I],Target,Pole,1.f);
                if(Toes[I].IsValidToEvaluate(Bones)&&Ground.SolePlant[I]>.001f)
                {
                    const auto Toe=Toes[I].GetCompactPoseIndex(Bones);
                    const auto Parent=Bones.GetParentBoneIndex(Toe);
                    const FTransform ParentCS=Pose.GetComponentSpaceTransform(Parent);
                    auto Local=Pose.GetComponentSpaceTransform(Toe).GetRelativeTransform(ParentCS);
                    Local.SetRotation(FQuat::Slerp(Local.GetRotation(),ToeRest[I],Ground.SolePlant[I]*Ground.Weight[I]).GetNormalized());
                    TArray<FBoneTransform,TInlineAllocator<1>> ToeChange;ToeChange.Emplace(Toe,Local*ParentCS);
                    Pose.LocalBlendCSBoneTransforms(ToeChange,1.f);
                }
            }
        }
        if(MeleeActive&&ChestBase.IsValidToEvaluate(Bones))
        {
            const auto C=ChestBase.GetCompactPoseIndex(Bones);auto Chest=Pose.GetComponentSpaceTransform(C);
            const FQuat Effort=FQuat(FVector::UpVector,FMath::DegreesToRadians(MeleePose.ChestYaw))*
                FQuat(FVector::ForwardVector,FMath::DegreesToRadians(MeleePose.ChestPitch))*
                FQuat(FVector::RightVector,FMath::DegreesToRadians(MeleePose.ChestRoll));
            Chest.SetRotation((Effort*Chest.GetRotation()).GetNormalized());
            TArray<FBoneTransform,TInlineAllocator<1>> Changes;Changes.Emplace(C,Chest);Pose.LocalBlendCSBoneTransforms(Changes,1.f);
        }
        const float Shot=FMath::Clamp(1.f-(Clock-State.LastShotAt)/.14f,0.f,1.f);
        auto SpinePose=Pose.GetComponentSpaceTransform(Spine.GetCompactPoseIndex(Bones));
        // Manny's mesh faces +Y; mesh-X is the pitch axis.
        const float MotionPitch=Motion==EFPSBodyMotion::Slide?18.f:Motion==EFPSBodyMotion::Dodge?-12.f*MotionState.MotionDirection.Y*FMath::Sin(PI*MT):Traversing?-12.f*FMath::Sin(PI*MT):0.f;
        const float Pitch=FMath::Clamp(State.AimPitch,-70.f,70.f)*.65f-4.f*Shot-6.f*Crouch+MotionPitch*MotionWeight;
        SpinePose.SetRotation(FQuat(FVector::ForwardVector,FMath::DegreesToRadians(Pitch))*SpinePose.GetRotation());
        if(Motion==EFPSBodyMotion::Dodge)
            SpinePose.SetRotation(FQuat(FVector::RightVector,.16f*MotionState.MotionDirection.X*FMath::Sin(PI*MT)*MotionWeight)*SpinePose.GetRotation());
        TArray<FBoneTransform,TInlineAllocator<1>> SpineChange;SpineChange.Emplace(Spine.GetCompactPoseIndex(Bones),SpinePose);
        Pose.LocalBlendCSBoneTransforms(SpineChange,1.f);
        if(Hands[0].IsValidToEvaluate(Bones)&&Hands[1].IsValidToEvaluate(Bones))
        {
            FTransform Targets[2]={Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones)),Pose.GetComponentSpaceTransform(Hands[1].GetCompactPoseIndex(Bones))};
            const bool Melee=State.Family==TEXT("Melee")||State.Family==TEXT("Tool");
            const bool Gun=State.Family==TEXT("Rifle")||State.Family==TEXT("Pistol");
            if(!State.bDual)Targets[0]=FPSBodyPoses::RightHand(State,T,Crouch,Aim,Sprint,Targets[0],PoseScale);
            const bool FreeLeft=!Melee&&(State.Action==EFPSBodyAction::Reload||State.Action==EFPSBodyAction::ReloadEmpty||State.Action==EFPSBodyAction::Equip);
            const bool PistolBash=State.Action==EFPSBodyAction::GunBash&&State.Family==TEXT("Pistol");
            const bool OffhandPistol=State.bDual||State.bOffhandPistol;
            bool AdjustHand[2]={Melee||(Gun&&!FreeLeft)||State.bDual,OffhandPistol||(bLeftGrip&&!FreeLeft)||PistolBash};
            if(State.Family==TEXT("Staff"))
            {
                // Carry the shaft ahead of the shoulder with room to open the
                // elbow. Follow the live shoulder through gait/crouch instead
                // of folding the arm into a fixed high point beside the chest.
                const auto Wrist=Hands[0].GetCompactPoseIndex(Bones);
                const auto Shoulder=Bones.GetParentBoneIndex(Bones.GetParentBoneIndex(Wrist));
                Targets[0].SetLocation(Pose.GetComponentSpaceTransform(Shoulder).GetLocation()
                    +FVector(-18,32,-16)*PoseScale);
                Targets[0].SetRotation(StaffHandRotation);
                // Preserve the authored wrist/shaft relationship while the arm
                // supports the staff; primary swings share the action clock.
                if(State.Action==EFPSBodyAction::Strike||State.Action==EFPSBodyAction::HeavyStrike)
                    Targets[0].AddToTranslation(FVector(0,22,32)*FPSBodyPoses::Pulse(T,State.ContactFraction));
                AdjustHand[0]=true;
            }
            if(OffhandPistol)
            {
                for(int32 I=State.bDual?0:1;I<2;++I)
                {
                    const auto& Hand=I==0?State.RightHand:State.LeftHand;const float Side=I==0?-1.f:1.f;
                    const float HandSprint=Hand.bEquipping||Hand.bReloading?0.f:Sprint;
                    // Both weapons retain independent forward holds; the support hand
                    // no longer remains at the single-pistol two-hand grip.
                    const float Kick=FMath::Clamp(1.f-(Clock-Hand.LastShotAt)/.13f,0.f,1.f);
                    FVector Target(Side*25.f,47.f-8.f*HandSprint-5.f*Kick,128.f-40.f*Crouch-15.f*HandSprint+3.f*Kick);
                    FQuat Rotation=FQuat(FVector::ForwardVector,.12f*(1.f-Aim)+.2f*HandSprint)
                        *FQuat(FVector::UpVector,Side*.35f*HandSprint)*Targets[I].GetRotation();
                    if(PistolBash)
                    {
                        const bool Striking=(State.ActionVariant==TEXT("PistolBashLeft"))==(I==1);
                        Target+=(Striking?FVector(-Side*9,18,16):FVector(Side*7,-14,3))*FPSBodyPoses::Pulse(T,State.ContactFraction);
                        // Both translation and impact rotation belong to the selected hand.
                        if(Striking)Rotation=FQuat(FVector::ForwardVector,.8f*FPSBodyPoses::PistolBashLift(T,State.ContactFraction))*Rotation;
                    }
                    if(Hand.bReloading)
                    {
                        const float Dip=Ease(Hand.Progress/.15f)*(1.f-Ease((Hand.Progress-.72f)/.28f));
                        Target+=FVector(Side*8,-18,-32)*Dip;
                        Rotation=FQuat(FVector::ForwardVector,.7f*Dip)*Rotation;
                    }
                    else if(Hand.bEquipping)
                    {
                        // Each hand draws from the hip using its own source equip clock.
                        const float Lowered=1.f-Ease(Hand.Progress/.85f);
                        Target+=FVector(Side*8,-18,-42)*Lowered;
                        Rotation=FQuat(FVector::ForwardVector,.55f*Lowered)*Rotation;
                    }
                    Targets[I].SetRotation(Rotation.GetNormalized());
                    Targets[I].SetLocation(Target*PoseScale);
                }
            }
            else if(bLeftGrip&&!FreeLeft&&!PistolBash)Targets[1]=LeftGrip*Targets[0];
            if(PistolBash&&!State.bDual)
                Targets[1].SetLocation(FVector(30,18,110-40*Crouch)*PoseScale);
            const bool BowActive=bBowPose&&State.Family==TEXT("Bow")&&State.Action!=EFPSBodyAction::Cast&&State.Action!=EFPSBodyAction::Consume&&!ActionWristMask&&!FPSBodyPoses::Traversing(State.Motion);
            if(BowActive)
            {
                const FQuat PitchRotation(FVector::ForwardVector,FMath::DegreesToRadians(FMath::Clamp(State.AimPitch,-65.f,65.f)));
                const FTransform Frame(PitchRotation*FRotator(0,90,0).Quaternion(),FVector(0,-8,145-40*Crouch)*PoseScale);
                for(int32 I=0;I<2;++I){Targets[I]=BowHands[I]*Frame;AdjustHand[I]=false;}
            }
            if(State.Family==TEXT("Unarmed")&&State.Action==EFPSBodyAction::GunBash)
            {
                for(int32 I=0;I<2;++I)
                {
                    const float Side=I==0?-1.f:1.f;
                    const bool Striking=(State.ActionVariant==TEXT("PunchLeft"))==(I==1);
                    const float Drive=Striking?FPSBodyPoses::Pulse(T,State.ContactFraction):0.f;
                    Targets[I].SetLocation(FVector(Side*(24.f-12.f*Drive),32.f+36.f*Drive,118.f-40.f*Crouch+12.f*Drive)*PoseScale);
                    AdjustHand[I]=true;
                }
            }
            const bool RecoveringCast=State.Action==EFPSBodyAction::Cast&&State.Contacts.Channel!=TEXT("StaffCast")&&State.ActionVariant==TEXT("Recover");
            if(RecoveringCast)
            {
                if(!bHasHandHistory||LastAction!=EFPSBodyAction::Cast||LastVariant!=TEXT("Recover"))
                {
                    CastRecoveryEntry=bHasHandHistory?LastHands[1]:Targets[1];
                    CastRecoveryStartProgress=State.ActionProgress;
                }
                const float Return=Ease((State.ActionProgress-CastRecoveryStartProgress)/FMath::Max(.001f,1.f-CastRecoveryStartProgress));
                FTransform Recovered;Recovered.Blend(CastRecoveryEntry,Targets[1],Return);
                Targets[1]=Recovered;AdjustHand[1]=true;
            }
            else if(State.Action==EFPSBodyAction::Cast&&State.Contacts.Channel!=TEXT("StaffCast"))
            {Targets[1]=FPSBodyPoses::CastHand(State,Crouch,Targets[1],PoseScale);AdjustHand[1]=true;}
            for(int32 I=0;I<2;++I)if(ActionWristMask&(1<<I)){Targets[I]=ActionHands[I];AdjustHand[I]=true;}
            // A cancelled traversal must blend from LastHands, not keep chasing stale world contacts.
            if(FPSBodyPoses::Traversing(State.Motion)&&MotionWeight>ZERO_ANIMWEIGHT_THRESH)
            {
                const float Plant=State.MotionHandContact;
                for(int32 I=0;I<2;++I)
                {Targets[I].SetLocation(FMath::Lerp(Targets[I].GetLocation(),Handholds[I],Plant*MotionWeight));AdjustHand[I]=true;}
            }
            if(bHasHandHistory&&(LastAction!=State.Action||LastVariant!=State.ActionVariant||LastActionWristMask!=ActionWristMask))
            {
                EntryHands[0]=LastHands[0];EntryHands[1]=LastHands[1];HandBlendAge=0.f;
            }
            LastAction=State.Action;LastVariant=State.ActionVariant;HandBlendAge+=Delta;
            LastActionWristMask=ActionWristMask;
            const float Blend=Ease(HandBlendAge/(State.Action==EFPSBodyAction::GunBash?.065f:.1f));
            const FTransform DynamicLeftFromRight=ActionHands[1].GetRelativeTransform(ActionHands[0]);
            // Blend first, then fit the complete grip group. Re-solving/clamping
            // each arm independently after a transition makes the left hand miss.
            for(int32 I=0;I<2;++I)
                if(!BowActive&&bHasHandHistory&&Blend<1.f&&!(I==1&&RecoveringCast))
                {FTransform Mixed;Mixed.Blend(EntryHands[I],Targets[I],Blend);Targets[I]=Mixed;}
            const bool SwordPair=State.Family==TEXT("Melee")&&bLeftGrip&&!Traversing&&
                State.Action!=EFPSBodyAction::Cast&&State.Action!=EFPSBodyAction::Consume&&
                ((bCoupledActionWrists&&ActionWristMask==3)||ActionWristMask==0);
            if(SwordPair)
            {
                Targets[1]=(ActionWristMask==3?DynamicLeftFromRight:LeftGrip)*Targets[0];
                FitHandPair(Pose,Targets);
            }
            for(int32 I=0;I<2;++I)
            {
                if(I==1&&!(ActionWristMask&2)&&bLeftGrip&&!FreeLeft&&!OffhandPistol&&!PistolBash&&State.Action!=EFPSBodyAction::Cast&&!(Traversing&&MotionWeight>ZERO_ANIMWEIGHT_THRESH))
                    Targets[1]=LeftGrip*Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones));
                if(I==1&&bCoupledActionWrists&&ActionWristMask==3&&!Traversing)
                    Targets[1]=DynamicLeftFromRight*Pose.GetComponentSpaceTransform(Hands[0].GetCompactPoseIndex(Bones));
                if(!BowActive&&(AdjustHand[I]||(bHasHandHistory&&Blend<1.f)))Solve(Pose,Hands[I],Targets[I],FVector(I==0?-65:65,10,105-40*Crouch)*PoseScale,1.f);
                LastHands[I]=Pose.GetComponentSpaceTransform(Hands[I].GetCompactPoseIndex(Bones));
            }
            if(BowActive)
            {
                // Left wrist owns the bow. Solve it first, then derive the right
                // contact from its achieved position, including reach clamping.
                Solve(Pose,Hands[1],Targets[1],FVector(65,10,105-40*Crouch)*PoseScale,1.f);
                const FTransform RightFromLeft=BowHands[0].GetRelativeTransform(BowHands[1]);
                Targets[0]=RightFromLeft*Pose.GetComponentSpaceTransform(Hands[1].GetCompactPoseIndex(Bones));
                Solve(Pose,Hands[0],Targets[0],FVector(-65,0,110-40*Crouch)*PoseScale,1.f);
                for(int32 I=0;I<2;++I)LastHands[I]=Pose.GetComponentSpaceTransform(Hands[I].GetCompactPoseIndex(Bones));
            }
            bHasHandHistory=true;bHadSwordPair=SwordPair;
        }
        bStaffNativeArmApplied=false;
        BlendStaffCarry(Out,Pose);
        BlendSword(Out,Pose);
        // A left jab's torso layer can otherwise drag the preserved right wrist
        // and re-solve its elbow. Restore the complete current support chain.
        if(bStaffQuickCarry&&SwordWeight>ZERO_ANIMWEIGHT_THRESH)BlendStaffCarry(Out,Pose);
        BlendStaffCast(Out,Pose);
        BlendBookCarry(Out,Pose);
        BlendConsume(Out,Pose);
        if(State.Action!=EFPSBodyAction::Dead&&ChestBase.IsValidToEvaluate(Bones))
        {
            const float Age=FMath::Clamp((Clock-Reactions.HitAt)/.42f,0.f,1.f);
            const float Hit=FPSBodyPoses::Pulse(Age,.18f)*Reactions.HitStrength;
            const float SafeContact=Traversing?.2f:1.f;
            const float HitPitch=HitDirection.Y*Hit*11.f+PushDirection.Y*Push*17.f-12.f*Stun;
            const float HitRoll=-HitDirection.X*Hit*9.f-PushDirection.X*Push*12.f+FMath::Sin((Clock-Reactions.StunAt)*3.8f)*3.f*Stun;
            const auto C=ChestBase.GetCompactPoseIndex(Bones);auto Chest=Pose.GetComponentSpaceTransform(C);
            const FQuat React=FQuat(FVector::ForwardVector,FMath::DegreesToRadians(HitPitch*SafeContact))*
                FQuat(FVector::RightVector,FMath::DegreesToRadians(HitRoll*SafeContact));
            Chest.SetRotation((React*Chest.GetRotation()).GetNormalized());
            Chest.AddToTranslation((HitDirection*(Hit*2.5f)+PushDirection*(Push*3.f))*SafeContact*PoseScale);
            TArray<FBoneTransform,TInlineAllocator<1>> R;R.Emplace(C,Chest);Pose.LocalBlendCSBoneTransforms(R,1.f);
            if(Head.IsValidToEvaluate(Bones)&&Stun>0.f)
            {
                const auto B=Head.GetCompactPoseIndex(Bones);auto Nod=Pose.GetComponentSpaceTransform(B);
                Nod.SetRotation(FQuat(FVector::ForwardVector,FMath::DegreesToRadians((-7.f+FMath::Sin(Clock*2.7f)*2.f)*Stun))*Nod.GetRotation());
                R.Reset();R.Emplace(B,Nod);Pose.LocalBlendCSBoneTransforms(R,1.f);
            }
        }
        FitStaffArm(Pose);
        // Safe conversion only writes bones still marked as component space.
        // Ancestor corrections (including an identity chest reaction) can have
        // already converted solved arms/legs back to local space in this pose.
        // Preserve those locals instead of retaining the original idle animation.
        Out.Pose=Pose.GetPose();
        FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Out.Pose);
        if(bStaffCastActive)
        {
            LastStaffCastPose.SetNum(Bones.GetCompactPoseNumBones());
            for(int32 I=0;I<LastStaffCastPose.Num();++I)LastStaffCastPose[I]=Out.Pose[FCompactPoseBoneIndex(I)];
            LastStaffCastChest=Pose.GetComponentSpaceTransform(ChestBase.GetCompactPoseIndex(Bones));
            LastStaffCastChest.AddToTranslation(-Pose.GetComponentSpaceTransform(Pelvis.GetCompactPoseIndex(Bones)).GetLocation());
        }
        if(bBookCarryActive)
        {
            LastBookCarryPose.SetNum(Bones.GetCompactPoseNumBones());
            for(int32 I=0;I<BookMotionBones.Num();++I)if(BookMotionBones[I])LastBookCarryPose[I]=Out.Pose[FCompactPoseBoneIndex(I)];
        }
        else LastBookCarryPose.Reset();
        // Melee uses unarmed locomotion. Wrist IK alone leaves its fingers open;
        // layer the native grip after IK, retaining all wrist/weapon transforms.
        if(bSwordGrip||EquipmentGripHands||ActionFingerMask)
        {
            FPoseContext Hold(Out);if(bSwordGrip)Grip.Evaluate(Hold);
            const bool Released=FPSBodyPoses::Traversing(State.Motion)||State.Action==EFPSBodyAction::Traverse;
            for(int32 Side=0;Side<2;++Side)
            {
                float Contact=Released?0.f:1.f;
                const bool EquipmentHand=(EquipmentGripHands&(1<<Side))!=0;
                if(!bSwordGrip&&!EquipmentHand)Contact=0.f;
                if(State.Family==TEXT("Bow")&&State.Action==EFPSBodyAction::Cast)Contact=0.f;
                const bool Gun=State.Family==TEXT("Rifle")||State.Family==TEXT("Pistol");
                if(Gun&&Side==1&&!State.bDual&&(State.Action==EFPSBodyAction::Reload||State.Action==EFPSBodyAction::ReloadEmpty||State.Action==EFPSBodyAction::Equip||State.Action==EFPSBodyAction::GunBash))Contact=0.f;
                if((State.bDual||(Side==1&&State.bOffhandPistol))&&(Side==0?State.RightHand:State.LeftHand).bReloading)Contact=0.f;
                if(Side==1&&State.Action==EFPSBodyAction::Cast&&State.Contacts.Channel!=TEXT("StaffCast"))
                {
                    const float Return=(State.ActionProgress-CastRecoveryStartProgress)/FMath::Max(.001f,1.f-CastRecoveryStartProgress);
                    Contact*=State.ActionVariant==TEXT("Recover")?Ease((Return-.55f)/.45f):0.f;
                }
                if((ActionFingerMask&(1<<Side))&&!Released)Contact=1.f;
                GripWeights[Side]=FMath::FInterpConstantTo(GripWeights[Side],Contact,Delta,12.5f);
                for(const auto Bone:GripBones[Side])
                {
                    const int32 MeshBone=Bones.MakeMeshPoseIndex(Bone).GetInt();
                    FTransform Target=(ActionFingerMask&(1<<Side))&&ActionFingers.IsValidIndex(MeshBone)?ActionFingers[MeshBone]
                        :EquipmentHand&&EquipmentFingers.IsValidIndex(MeshBone)?EquipmentFingers[MeshBone]
                        :(bSwordGrip?Hold.Pose[Bone]:Out.Pose[Bone]);
                    // Only the two fitted overhead takes opt in. Keep their
                    // support thumb below the upper hand instead of restoring
                    // the equipment's extended thumb after the body blend.
                    if(SwordSupportThumbWeight>ZERO_ANIMWEIGHT_THRESH&&SwordSupportThumbBones[Bone.GetInt()])
                    {
                        FTransform Fitted;Fitted.Blend(Target,LastSwordPose[Bone.GetInt()],SwordSupportThumbWeight);
                        Target=Fitted;
                    }
                    FTransform Blended;Blended.Blend(Out.Pose[Bone],Target,GripWeights[Side]);
                    Out.Pose[Bone]=Blended;
                }
            }
        }
        else GripWeights[0]=GripWeights[1]=0.f;
    }
};

#include "FPSBodySwordPose.inl"
#include "FPSBodyStaffCastPose.inl"
#include "FPSBodyStaffCarryPose.inl"
#include "FPSBodyStaffStrikePose.inl"
#include "FPSBodyBookCarryPose.inl"
#include "FPSBodyStaffArmPose.inl"
#include "FPSBodyConsumePose.inl"
struct FProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle,Neutral,WalkA,WalkB,JogA,JogB,Air,Action,Death,Grip,Sword,StaffCast,StaffCarry,BookCarry,BookPush,Consume;
    FAnimNode_TwoWayBlend Walk,Jog,Pace,Movement,AirBlend,DeathBlend;
    FUpperLayer Upper,AirHold;
    FControls Controls;
    UAnimSequence* SwordAsset=nullptr;
    FName SwordKey;
    float SwordContact=.4f,SwordRelease=.65f;
    UAnimSequence* ConsumeAsset=nullptr;
    float ConsumeContact=.3f,ConsumeRelease=.7f;
    TMap<const UAnimSequence*,FStrideTiming> Strides;
    float SmoothedSpeed=0.f,SmoothedHeading=0.f,GaitCycles=0.f;
    bool bHasHeading=false;
    FFPSBodyGrounding Grounding;
    float StunBlend=0.f;
    const FStrideTiming& Timing(const UAnimSequence* Clip,const UAnimSequence* PhaseReference=nullptr)
    {
        if(const auto* Existing=Strides.Find(Clip))return *Existing;
        return Strides.Add(Clip,FStrideTiming(Clip,PhaseReference));
    }
    explicit FProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance)
    {
        Walk.A.SetLinkNode(&WalkA);Walk.B.SetLinkNode(&WalkB);
        Jog.A.SetLinkNode(&JogA);Jog.B.SetLinkNode(&JogB);
        Pace.A.SetLinkNode(&Walk);Pace.B.SetLinkNode(&Jog);
        Movement.A.SetLinkNode(&Idle);Movement.B.SetLinkNode(&Pace);
        AirBlend.A.SetLinkNode(&Movement);AirBlend.B.SetLinkNode(&Air);
        AirHold.Base.SetLinkNode(&AirBlend);AirHold.Upper.SetLinkNode(&Idle);
        Upper.Base.SetLinkNode(&AirHold);Upper.Upper.SetLinkNode(&Action);
        Controls.Source.SetLinkNode(&Upper);Controls.Neutral.SetLinkNode(&Neutral);Controls.Grip.SetLinkNode(&Grip);
        Controls.Sword.SetLinkNode(&Sword);
        Controls.StaffCast.SetLinkNode(&StaffCast);
        Controls.StaffCarry.SetLinkNode(&StaffCarry);
        Controls.BookCarry.SetLinkNode(&BookCarry);
        Controls.BookPush.SetLinkNode(&BookPush);
        Controls.Consume.SetLinkNode(&Consume);
        DeathBlend.A.SetLinkNode(&Controls);DeathBlend.B.SetLinkNode(&Death);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override {return &DeathBlend;}
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {Nodes.Append({&Idle,&Neutral,&WalkA,&WalkB,&JogA,&JogB,&Walk,&Jog,&Pace,&Movement,
        &Air,&AirBlend,&AirHold,&Action,&Upper,&Grip,&Sword,&StaffCast,&StaffCarry,&BookCarry,&BookPush,&Consume,&Controls,&Death,&DeathBlend});}
    virtual void PreUpdate(UAnimInstance* Instance,float Delta) override
    {
        FAnimInstanceProxy::PreUpdate(Instance,Delta);
        const auto* D=CastChecked<UFPSPlayerBodyAnimInstance>(Instance);
        const FString Family=(D->BodyState.Family==TEXT("Rifle")||D->BodyState.Family==TEXT("Pistol"))?D->BodyState.Family.ToString():TEXT("Unarmed");
        const auto Clip=[&](const FString& Key){return D->Clips.FindRef(FName(*Key)).Get();};
        const auto Set=[](FAnimNode_SequenceEvaluator_Standalone& Node,UAnimSequence* Asset,float Time,bool Loop)
        {
            Node.SetSequence(Asset);Node.SetShouldLoop(Loop);Node.SetTeleportToExplicitTime(true);
            const float Length=Asset?Asset->GetPlayLength():0.f;
            Node.SetExplicitTime(Loop&&Length>0.f?FMath::Fmod(FMath::Max(Time,0.f),Length):FMath::Clamp(Time,0.f,Length));
        };
        UAnimSequence* IdleClip=Clip(Family+TEXT(".Idle"));Set(Idle,IdleClip,D->Clock,true);
        UAnimSequence* SwordGrip=Clip(TEXT("Melee.Grip"));
        Set(Grip,SwordGrip,0.f,false);
        Controls.bSwordGrip=SwordGrip&&IdleClip&&SwordGrip->GetSkeleton()==IdleClip->GetSkeleton()
            &&D->BodyState.Family==TEXT("Melee")&&D->bHasLeftGrip;
        Set(Neutral,IdleClip,0.f,false);
        static const TCHAR* Directions[]={TEXT("Fwd"),TEXT("Fwd_Right"),TEXT("Right"),TEXT("Bwd_Right"),TEXT("Bwd"),TEXT("Bwd_Left"),TEXT("Left"),TEXT("Fwd_Left")};
        const float Dt=FMath::Max(Delta,0.f);
        SmoothedSpeed=FMath::FInterpTo(SmoothedSpeed,D->Speed,Dt,10.f);
        if(D->Speed>5.f)
        {
            if(!bHasHeading){SmoothedHeading=D->Direction;bHasHeading=true;}
            else SmoothedHeading=FMath::UnwindDegrees(SmoothedHeading+
                FMath::FindDeltaAngleDegrees(SmoothedHeading,D->Direction)*FMath::Clamp(Dt*10.f,0.f,1.f));
        }
        const float Heading=FMath::Fmod(SmoothedHeading+360.f,360.f)/45.f;
        const int32 A=FMath::FloorToInt(Heading)%8,B=(A+1)%8;
        Walk.Alpha=Jog.Alpha=Heading-FMath::FloorToFloat(Heading);
        auto* WA=Clip(Family+TEXT(".Walk.")+Directions[A]);auto* WB=Clip(Family+TEXT(".Walk.")+Directions[B]);
        auto* JA=Clip(Family+TEXT(".Jog.")+Directions[A]);auto* JB=Clip(Family+TEXT(".Jog.")+Directions[B]);
        Timing(JA,Clip(Family+(A>=3&&A<=5?TEXT(".Jog.Bwd"):TEXT(".Jog.Fwd"))));
        Timing(JB,Clip(Family+(B>=3&&B<=5?TEXT(".Jog.Bwd"):TEXT(".Jog.Fwd"))));
        // Normal travel (including backward/ADS) uses the existing walk library.
        // 450 cm/s is this game's normal speed, not an instruction to play 100%
        // jogging. Sprint intent is replicated with the body state on observers.
        const float JogTarget=D->BodyState.bSprinting&&!D->BodyState.bAiming?
            FMath::Clamp((SmoothedSpeed-250.f)/250.f,0.f,1.f)*(1.f-D->CrouchAlpha):0.f;
        Pace.Alpha=FMath::FInterpTo(Pace.Alpha,JogTarget,Dt,12.f);
        Movement.Alpha=FMath::Clamp(SmoothedSpeed/80.f,0.f,1.f)*(1.f-D->MotionAlpha);
        const float WalkDuration=FMath::Lerp(Timing(WA).Duration(),Timing(WB).Duration(),Walk.Alpha);
        const float JogDuration=FMath::Lerp(Timing(JA).Duration(),Timing(JB).Duration(),Jog.Alpha);
        const float StrideDuration=FMath::Lerp(WalkDuration,JogDuration,Pace.Alpha);
        // Retargeting changes stride length (Jason's walks are about 270-290
        // cm/s). Use each reused clip's displacement instead of Manny's constants.
        const float WalkSpeed=FMath::Lerp(Timing(WA).Speed(300.f),Timing(WB).Speed(300.f),Walk.Alpha);
        const float JogSpeed=FMath::Lerp(Timing(JA).Speed(600.f),Timing(JB).Speed(600.f),Jog.Alpha);
        const float SourceSpeed=FMath::Lerp(WalkSpeed,JogSpeed,Pace.Alpha)*FMath::Lerp(1.f,CrouchStrideScale,D->CrouchAlpha);
        const float PlayRate=FMath::Clamp(SmoothedSpeed/SourceSpeed,0.f,FMath::Lerp(1.8f,1.35f,Pace.Alpha));
        // Twelve is a common multiple of the template's one-to-four-stride clips.
        GaitCycles=FMath::Fmod(GaitCycles+Dt*PlayRate*(1.f-D->MotionAlpha)/FMath::Max(StrideDuration,.1f),12.f);
        Controls.GaitPhase=GaitCycles;
        Set(WalkA,WA,Timing(WA).Sample(GaitCycles),true);Set(WalkB,WB,Timing(WB).Sample(GaitCycles),true);
        Set(JogA,JA,Timing(JA).Sample(GaitCycles),true);Set(JogB,JB,Timing(JB).Sample(GaitCycles),true);
        const bool Landing=!D->bFalling&&D->LandTime<.22f;
        Set(Air,Clip(Landing?TEXT("Land"):(D->VerticalSpeed>0.f?TEXT("Jump"):TEXT("Fall"))),Landing?D->LandTime:D->AirTime,!Landing&&D->VerticalSpeed<=0.f);
        AirBlend.Alpha=D->AirAlpha*(1.f-D->MotionAlpha);
        AirHold.Weight=(Family!=TEXT("Unarmed"))?AirBlend.Alpha:0.f;
        const bool Reload=D->UpperState.Action==EFPSBodyAction::Reload||D->UpperState.Action==EFPSBodyAction::ReloadEmpty;
        UAnimSequence* ActionClip=Clip(Family+(Reload?TEXT(".Reload"):TEXT(".Equip")));
        const float Elapsed=FMath::Max(0.f,D->Clock-D->BodyState.ActionStartedAt);
        const float Fraction=FPSBodyPoses::Progress(D->UpperState,D->Clock);
        Set(Action,ActionClip?ActionClip:IdleClip,Fraction*(ActionClip?ActionClip->GetPlayLength():0.f),false);
        Upper.Weight=ActionClip?D->UpperAlpha:0.f;
        Controls.State=D->BodyState;Controls.Clock=D->Clock;Controls.Crouch=D->CrouchAlpha;
        Controls.PoseScale=D->PoseScale;
        Controls.MotionState=D->MotionState;Controls.MotionWeight=D->MotionAlpha;
        Controls.Reactions=D->Reactions;Controls.bFalling=D->bFalling;
        StunBlend=FMath::FInterpTo(StunBlend,D->Reactions.bStunned?1.f:0.f,Delta,D->Reactions.bStunned?12.f:7.f);
        Controls.StunBlend=StunBlend;
        if(auto* Mesh=Instance->GetSkelMeshComponent())
        {
            Grounding.Update(*Mesh,*D,Controls.RawFeet,1.f-Pace.Alpha,Delta);Controls.Ground=Grounding.Pose;
            Controls.HitDirection=Mesh->GetComponentTransform().InverseTransformVectorNoScale(D->Reactions.HitDirection).GetSafeNormal2D();
            Controls.PushDirection=Mesh->GetComponentTransform().InverseTransformVectorNoScale(D->Reactions.PushDirection).GetSafeNormal2D();
        }
        Controls.Aim=D->AimAlpha;Controls.Sprint=D->SprintAlpha;Controls.Delta=Dt;
        if(const auto* Mesh=Instance->GetSkelMeshComponent();Mesh&&D->MotionState.bHasHandholds)
        {
            Controls.Handholds[0]=Mesh->GetComponentTransform().InverseTransformPosition(D->MotionState.RightHandhold);
            Controls.Handholds[1]=Mesh->GetComponentTransform().InverseTransformPosition(D->MotionState.LeftHandhold);
        }
        else {Controls.Handholds[0]=FVector(-25,45,160);Controls.Handholds[1]=FVector(25,45,160);}
        Controls.LeftGrip=D->LeftGripFromRight;Controls.bLeftGrip=D->bHasLeftGrip;
        Controls.EquipmentFingers=D->EquipmentFingers;Controls.EquipmentGripHands=D->EquipmentGripHands;
        if(D->BodyState.Family!=TEXT("Rifle")&&D->BodyState.Family!=TEXT("Pistol")&&D->BodyState.Family!=TEXT("Staff")&&D->BodyState.Family!=TEXT("Bow")&&D->BodyState.Family!=TEXT("Tool")&&D->BodyState.Family!=TEXT("Melee"))Controls.EquipmentGripHands=0;
        Controls.ActionFingers=D->ActionFingers;Controls.ActionFingerMask=D->ActionFingerMask;
        Controls.ActionWristMask=D->ActionWristMask;Controls.ActionHands[0]=D->ActionHands[0];Controls.ActionHands[1]=D->ActionHands[1];
        Controls.bCoupledActionWrists=D->bCoupledActionWrists;
        const FName HandAttackKey=FPSBodyHandAttackMotion::Clip(D->BodyState);
        const FName NextSwordKey=HandAttackKey.IsNone()?FPSBodySwordMotion::Clip(D->BodyState):HandAttackKey;
        auto* NextSwordAsset=D->Clips.FindRef(NextSwordKey).Get();
        const bool HasSwordAction=NextSwordAsset&&IdleClip&&NextSwordAsset->GetSkeleton()==IdleClip->GetSkeleton();
        // Whirlwind phase endpoints are authored to match; a second temporal
        // crossfade would drag the wrists and planted foot behind actor yaw.
        const bool WhirlwindPhaseChange=D->BodyState.Action==EFPSBodyAction::Whirlwind&&
            (SwordKey==TEXT("Melee.FullBody.Whirlwind.Start")||SwordKey==TEXT("Melee.FullBody.Whirlwind.Loop")||
             SwordKey==TEXT("Melee.FullBody.TangDao.Whirlwind.Start")||SwordKey==TEXT("Melee.FullBody.TangDao.Whirlwind.Loop"));
        Controls.bSwordChanged=HasSwordAction&&NextSwordKey!=SwordKey&&!WhirlwindPhaseChange;
        if(HasSwordAction)
        {
            Controls.bHandAttackLibrary=!HandAttackKey.IsNone();
            Controls.bStaffAttackLibrary=HandAttackKey==TEXT("Staff.FullBody.Strike");
            Controls.LibraryPreserveHands=Controls.bHandAttackLibrary?FPSBodyHandAttackMotion::PreserveHands(D->BodyState):0;
            if(NextSwordAsset!=SwordAsset)
            {
                SwordAsset=NextSwordAsset;SwordContact=.4f;SwordRelease=.65f;Controls.bSwordNativeGrip=false;
                Controls.bStaffNativeStrike=false;
                for(const auto& Marker:SwordAsset->AuthoredSyncMarkers)
                {
                    if(Marker.MarkerName==TEXT("Contact"))SwordContact=Marker.Time/SwordAsset->GetPlayLength();
                    if(Marker.MarkerName==TEXT("Release"))SwordRelease=Marker.Time/SwordAsset->GetPlayLength();
                    if(Marker.MarkerName==TEXT("NativeSwordGrip"))Controls.bSwordNativeGrip=true;
                    if(Marker.MarkerName==TEXT("NativeStaffArm"))Controls.bStaffNativeStrike=true;
                }
            }
            SwordKey=NextSwordKey;
            const auto& S=D->BodyState;
            const float P=FPSBodyPoses::Progress(S,D->Clock);
            float Sample=P;
            if(S.Action==EFPSBodyAction::Whirlwind)Sample=FPSBodySwordMotion::WhirlwindSample(S,P);
            else if(S.Action==EFPSBodyAction::Charge)Sample=Ease(P)*SwordContact*.7f;
            else if(S.Action==EFPSBodyAction::Guard)Sample=P*.35f;
            else if(S.Action!=EFPSBodyAction::GuardHit&&S.Action!=EFPSBodyAction::GuardBreak)
            {
                const float Hit=FMath::Clamp(S.ContactFraction,.01f,.98f);
                const float Release=FMath::Clamp(S.ReleaseFraction,Hit+.001f,.99f);
                const float Entry=FMath::Clamp(S.ActionEntryFraction,0.f,Hit-.001f);
                const float ContactPose=SwordContact;
                const float ReleasePose=SwordRelease;
                Sample=P<=Hit?FMath::Lerp(0.f,ContactPose,FMath::Clamp((P-Entry)/(Hit-Entry),0.f,1.f)):
                    P<=Release?FMath::Lerp(ContactPose,ReleasePose,(P-Hit)/(Release-Hit)):
                    FMath::Lerp(ReleasePose,1.f,(P-Release)/(1.f-Release));
            }
            Set(Sword,SwordAsset,Sample*SwordAsset->GetPlayLength(),false);
            // The fading base is an ordinary carry. No procedural FPS attack
            // effort or wrist trajectory is added underneath the authored body.
            Controls.State.Action=EFPSBodyAction::None;Controls.State.ActionVariant=NAME_None;
            Controls.ActionWristMask&=Controls.LibraryPreserveHands;Controls.bCoupledActionWrists=false;
        }
        else if(!SwordAsset)Set(Sword,IdleClip,0.f,false);
        const float SwordTarget=HasSwordAction?FMath::Clamp(D->BodyState.ActionWeight,0.f,1.f):0.f;
        Controls.SwordWeight=FMath::FInterpConstantTo(Controls.SwordWeight,SwordTarget,Dt,HasSwordAction?12.5f:10.f);
        // Committed Kwang skills retain their authored weight shift and step.
        // Dash travel keeps locomotion until the executor starts its windup;
        // capsule translation is still owned by the existing sword gameplay.
        const bool CommittedSword=HasSwordAction&&(D->BodyState.Action==EFPSBodyAction::Whirlwind||
            (D->BodyState.Action==EFPSBodyAction::HeavyStrike&&D->BodyState.ActionVariant!=TEXT("HeavyRelease")));
        float AttackLegs=CommittedSword?1.f:0.f;
        if(CommittedSword&&D->BodyState.ActionVariant==TEXT("DashOverhead"))
        {
            const auto& S=D->BodyState;
            const float Windup=FMath::Max(.001f,S.ContactFraction-S.ActionEntryFraction);
            AttackLegs=Ease((FPSBodyPoses::Progress(S,D->Clock)-S.ActionEntryFraction)/(Windup*.45f));
        }
        Controls.SwordAttackLegOwnership=FMath::FInterpConstantTo(Controls.SwordAttackLegOwnership,AttackLegs,Dt,12.5f);
        const float CarryLegs=1.f-FMath::Clamp(SmoothedSpeed/120.f,0.f,1.f);
        Controls.SwordLegWeight=FMath::Lerp(CarryLegs,1.f,Controls.SwordAttackLegOwnership)*
            (1.f-D->CrouchAlpha)*(1.f-D->MotionAlpha)*(1.f-D->AirAlpha);
        // KayKit's exaggerated lunge/step is removed in the Jason adaptation.
        // Grounding, crouch and locomotion continue to own the lower body.
        if(Controls.bHandAttackLibrary)Controls.SwordLegWeight=0.f;
        if(Controls.SwordWeight<=ZERO_ANIMWEIGHT_THRESH)SwordKey=NAME_None;
        const auto& Casting=D->BodyState;
        const bool StaffGesture=Casting.Family==TEXT("Staff")&&Casting.Action==EFPSBodyAction::Cast&&
            Casting.Contacts.Channel==TEXT("StaffCast")&&!FPSBodyPoses::Traversing(Casting.Motion);
        auto* Carry=Clip(TEXT("Staff.NativeArm.Carry"));
        Controls.bStaffCarryActive=Casting.Family==TEXT("Staff")&&Carry&&IdleClip&&Carry->GetSkeleton()==IdleClip->GetSkeleton()&&
            !FPSBodyPoses::Traversing(Casting.Motion)&&Casting.Action!=EFPSBodyAction::Dead;
        Controls.bStaffQuickCarry=Controls.bStaffCarryActive&&Casting.Action==EFPSBodyAction::GunBash;
        // Quick melee owns the left hand. The FPS staff rig also publishes a
        // right wrist during that action, but it must not replace world carry.
        if(Controls.bStaffQuickCarry)Controls.ActionWristMask&=~uint8(1);
        // The selected source opening is slowed into a quiet carry cycle. The
        // live gait still owns the chest and legs; the book keeps its left arm.
        Set(StaffCarry,Controls.bStaffCarryActive?Carry:IdleClip,D->Clock*.35f,true);
        auto* BookHold=Clip(TEXT("Staff.BookCarry"));
        const int32 BookIndex=D->SpellbookEquipmentIndex;
        const bool BookVisible=BookIndex!=INDEX_NONE&&(!Casting.Contacts.Rigs.IsValidIndex(BookIndex)||
            !Casting.Contacts.Rigs[BookIndex].Valid||Casting.Contacts.Rigs[BookIndex].Visible);
        Controls.bBookCarryActive=Casting.Family==TEXT("Staff")&&BookVisible&&BookHold&&IdleClip&&
            BookHold->GetSkeleton()==IdleClip->GetSkeleton()&&Casting.Action!=EFPSBodyAction::Dead;
        Set(BookCarry,Controls.bBookCarryActive?BookHold:IdleClip,0.f,false);
        auto* BookStrike=Clip(TEXT("Staff.BookPush"));
        Controls.bBookPushActive=Controls.bBookCarryActive&&BookStrike&&
            BookStrike->GetSkeleton()==IdleClip->GetSkeleton()&&!FPSBodyPoses::Traversing(Casting.Motion)&&
            Casting.Action==EFPSBodyAction::GunBash&&Casting.ActionVariant==TEXT("SpellbookPush");
        Controls.BookPushProgress=Controls.bBookPushActive?FPSBodyPoses::Progress(Casting,D->Clock):0.f;
        Set(BookPush,Controls.bBookPushActive?BookStrike:IdleClip,
            Controls.bBookPushActive?Controls.BookPushProgress*BookStrike->GetPlayLength():0.f,false);
        if(Controls.bBookPushActive)
        {
            // The full native support arm owns the shove. Do not first force
            // its wrist to the camera-space hand or add generic pistol effort.
            Controls.ActionWristMask&=~uint8(2);Controls.bCoupledActionWrists=false;
            Controls.State.Action=EFPSBodyAction::None;Controls.State.ActionVariant=NAME_None;
        }
        auto* CastGather=Clip(TEXT("Staff.NativeArm.CastGather"));
        auto* CastRelease=Clip(TEXT("Staff.NativeArm.CastRelease"));
        Controls.bStaffNativeCast=CastGather&&CastRelease&&IdleClip&&
            CastGather->GetSkeleton()==IdleClip->GetSkeleton()&&CastRelease->GetSkeleton()==IdleClip->GetSkeleton();
        if(!Controls.bStaffNativeCast)
        {CastGather=Clip(TEXT("Staff.FullBody.CastGather"));CastRelease=Clip(TEXT("Staff.FullBody.CastRelease"));}
        Controls.bStaffCastActive=StaffGesture&&CastGather&&CastRelease&&IdleClip&&
            CastGather->GetSkeleton()==IdleClip->GetSkeleton()&&CastRelease->GetSkeleton()==IdleClip->GetSkeleton();
        if(Controls.bStaffCastActive)
        {
            Controls.StaffCastPhase=Casting.ActionVariant;
            Controls.StaffCastProgress=FPSBodyPoses::Progress(Casting,D->Clock);
            auto* CastAsset=CastGather;
            float Sample=Casting.ActionVariant==TEXT("Gather")?Controls.StaffCastProgress:1.f;
            if(Casting.ActionVariant==TEXT("Release"))
            {
                CastAsset=CastRelease;
                float Contact=.65f;
                for(const auto& Marker:CastAsset->AuthoredSyncMarkers)
                    if(Marker.MarkerName==TEXT("Contact"))Contact=Marker.Time/CastAsset->GetPlayLength();
                const float Hit=FMath::Clamp(Casting.ContactFraction,.01f,.99f),P=Controls.StaffCastProgress;
                Sample=P<=Hit?Contact*P/Hit:FMath::Lerp(Contact,1.f,(P-Hit)/(1.f-Hit));
            }
            Set(StaffCast,CastAsset,Sample*CastAsset->GetPlayLength(),false);
            // The full native chain owns casting. Keep the base as a live carry
            // for recovery and leave an offhand pistol's independent wrist intact.
            Controls.State.Action=EFPSBodyAction::None;Controls.State.ActionVariant=NAME_None;
            Controls.ActionWristMask&=~uint8(1);Controls.bCoupledActionWrists=false;
        }
        else Set(StaffCast,IdleClip,0.f,false);
        const auto& Use=D->BodyState;
        FName ConsumeKey;
        if(Use.Action==EFPSBodyAction::Consume&&!FPSBodyPoses::Traversing(Use.Motion))
            ConsumeKey=Use.Contacts.Consumable==TEXT("baguette_bread")?TEXT("Consume.EatBaguette"):
                Use.Contacts.Consumable==TEXT("bread")?TEXT("Consume.EatBread"):TEXT("Consume.Drink");
        auto* NextConsume=D->Clips.FindRef(ConsumeKey).Get();
        const bool HasConsume=NextConsume&&IdleClip&&NextConsume->GetSkeleton()==IdleClip->GetSkeleton();
        Controls.ConsumeContactWeight=0.f;
        if(HasConsume)
        {
            if(NextConsume!=ConsumeAsset)
            {
                ConsumeAsset=NextConsume;ConsumeContact=.3f;ConsumeRelease=.7f;Controls.bConsumeNativeArm=false;
                for(const auto& Marker:ConsumeAsset->AuthoredSyncMarkers)
                {
                    if(Marker.MarkerName==TEXT("Contact"))ConsumeContact=Marker.Time/ConsumeAsset->GetPlayLength();
                    if(Marker.MarkerName==TEXT("Release"))ConsumeRelease=Marker.Time/ConsumeAsset->GetPlayLength();
                    if(Marker.MarkerName==TEXT("NativeConsumeArm"))Controls.bConsumeNativeArm=true;
                }
            }
            const float P=FPSBodyPoses::Progress(Use,D->Clock);
            const float Contact=FMath::Clamp(Use.ContactFraction,.01f,.98f);
            const float Release=FMath::Clamp(Use.ReleaseFraction,Contact+.001f,.99f);
            const float Entry=FMath::Clamp(Use.ActionEntryFraction,0.f,Contact-.001f);
            const bool NativeFood=Controls.bConsumeNativeArm&&ConsumeKey!=TEXT("Consume.Drink");
            // The native food clips are authored on the actual item-use clock,
            // including the grab lead-in and the late bite. Keep drink retiming.
            const float Sample=NativeFood?P:P<=Contact?FMath::Lerp(0.f,ConsumeContact,FMath::Clamp((P-Entry)/(Contact-Entry),0.f,1.f)):
                P<=Release?FMath::Lerp(ConsumeContact,ConsumeRelease,(P-Contact)/(Release-Contact)):
                FMath::Lerp(ConsumeRelease,1.f,(P-Release)/(1.f-Release));
            Set(Consume,ConsumeAsset,Sample*ConsumeAsset->GetPlayLength(),false);
            // Only correct the food's final bite with the rigid arm/prop lever;
            // do not pull the whole slow approach onto the lips prematurely.
            if(NativeFood)
                Controls.ConsumeContactWeight=Ease((Sample-ConsumeContact+.06f)/.06f)*
                    (1.f-Ease((Sample-ConsumeRelease)/.08f));
            else if(ConsumeKey==TEXT("Consume.Drink"))
                Controls.ConsumeContactWeight=Ease((Sample-.075f)/FMath::Max(.001f,ConsumeContact-.075f))*
                    (1.f-Ease((Sample-ConsumeRelease)/FMath::Max(.001f,1.f-ConsumeRelease)));
            Controls.ActionWristMask&=~uint8(2);Controls.bCoupledActionWrists=false;
        }
        else if(!ConsumeAsset)Set(Consume,IdleClip,0.f,false);
        const float ConsumeTarget=HasConsume?FMath::Clamp(Use.ActionWeight,0.f,1.f):0.f;
        Controls.ConsumeWeight=FMath::FInterpConstantTo(Controls.ConsumeWeight,ConsumeTarget,Dt,HasConsume?12.5f:10.f);
        Controls.ConsumeMouthInHead=D->ConsumeMouthInHead;
        Controls.ConsumePropContact=D->ConsumePropContact;
        Controls.bHasConsumeProp=D->bHasConsumeProp;
        // The anatomical grip table owns palm facing. Carry and library clips
        // share it without an extra global wrist yaw correction.
        Controls.StaffHandRotation=D->StaffHandRotation;
        Controls.bBowPose=D->bBowPose;Controls.BowHands[0]=D->BowHands[0];Controls.BowHands[1]=D->BowHands[1];
        Set(Death,Clip(TEXT("Dead")),Elapsed,false);DeathBlend.Alpha=D->BodyState.Action==EFPSBodyAction::Dead?Ease(Elapsed/.12f):0.f;
    }
};
}

void UFPSPlayerBodyAnimInstance::NativeUpdateAnimation(float Delta)
{
    Super::NativeUpdateAnimation(Delta);
    const float Dt=FMath::Max(Delta,0.f);
    CrouchAlpha=FMath::FInterpTo(CrouchAlpha,BodyState.bCrouched||BodyState.bSliding?1.f:0.f,Dt,10.f);
    const bool SpecialMove=BodyState.Motion!=EFPSBodyMotion::Ground;
    if(SpecialMove)MotionState=BodyState;
    MotionAlpha=FMath::FInterpTo(MotionAlpha,SpecialMove?1.f:0.f,Dt,16.f);
    AimAlpha=FMath::FInterpTo(AimAlpha,BodyState.bAiming?1.f:0.f,Dt,12.f);
    const bool Sprint=BodyState.bSprinting&&BodyState.Action==EFPSBodyAction::None&&!BodyState.bCrouched&&!SpecialMove;
    SprintAlpha=FMath::FInterpTo(SprintAlpha,Sprint?1.f:0.f,Dt,10.f);
    if(bFalling){AirTime+=Dt;LandTime=1.f;}else{if(bPreviouslyFalling)LandTime=0.f;else LandTime+=Dt;AirTime=0.f;}
    bPreviouslyFalling=bFalling;
    AirAlpha=FMath::FInterpTo(AirAlpha,bFalling||LandTime<.16f?1.f:0.f,Dt,14.f);
    const bool Gun=BodyState.Family==TEXT("Rifle")||BodyState.Family==TEXT("Pistol");
    const bool HasUpper=Gun&&!BodyState.bDual&&(BodyState.Action==EFPSBodyAction::Reload||BodyState.Action==EFPSBodyAction::ReloadEmpty||BodyState.Action==EFPSBodyAction::Equip);
    if(HasUpper)UpperState=BodyState;
    UpperAlpha=FMath::FInterpTo(UpperAlpha,HasUpper?1.f:0.f,Dt,15.f);
}
FAnimInstanceProxy* UFPSPlayerBodyAnimInstance::CreateAnimInstanceProxy(){return new FPSBodyAnimation::FProxy(this);}
void UFPSPlayerBodyAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy){delete Proxy;}
