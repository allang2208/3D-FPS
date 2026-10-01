#include "GripPoseLayer.h"
#include "LMG201WeaponAssets.h"
#include "PKMLowpolyWeaponAssets.h"
#include "../FPSGAMECharacter.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "HAL/IConsoleManager.h"

namespace
{
TAutoConsoleVariable<int32> CVarGripLayer(TEXT("fps.Weapon.GripLayer"),1,
    TEXT("PKM / 201 grip families. 0 = authored family clips; 1 = idle, aim, fire, aim_fire through the runtime grip layer ")
    TEXT("(GripLayer56); 2 = also sprint, equip and reloads (preview, known transition issues)."));

// Same constants as ArmHinge55 author.py (the base clips are solved with them).
const double ForearmCap=FMath::DegreesToRadians(110.0);
const double CreaseRoll=FMath::DegreesToRadians(20.0);
const double PronationShare[]={0.0,0.0,0.0,0.0,0.0,1.0/3.0,2.0/3.0,0.0};
// Base hand to base grip (gun space): full layer inside the first value, none beyond the
// second; the weight then changes at most WeightRate per second and is eased (study_rate.json).
const FVector2d WeightDistanceCm(3.5,5.5),WeightAngleDeg(32.0,48.0);
const float WeightRate=4.f;
const TCHAR* ArmNames[]={TEXT("clavicle_l"),TEXT("upperarm_l"),TEXT("upperarm_twist_01_l"),TEXT("upperarm_twist_02_l"),
    TEXT("lowerarm_l"),TEXT("lowerarm_twist_02_l"),TEXT("lowerarm_twist_01_l"),TEXT("hand_l")};

FQuat Frame(const FVector& X,const FVector& Z){return FRotationMatrix::MakeFromXZ(X,Z).ToQuat();}
double Twist(const FQuat& Q,const FVector& Axis){return FMath::UnwindRadians(2.0*FMath::Atan2(FVector(Q.X,Q.Y,Q.Z)|Axis.GetSafeNormal(),Q.W));}
double Bend(const FVector& U,const FVector& F){return FMath::RadiansToDegrees(FMath::Atan2((U^F).Size(),U|F));}
double CreaseWeight(double BendDeg){return FMath::SmoothStep(30.0,70.0,BendDeg);}
double CapForearm(double X){return FMath::Clamp(X,-ForearmCap,ForearmCap);}

double Swivel(const FVector& E,const FVector& A,const FVector& H,const FVector& Reference)
{
    const FVector Axis=(H-A).GetSafeNormal();
    const FVector V=(E-A)-Axis*((E-A)|Axis);
    const FVector R=Reference-Axis*(Reference|Axis);
    return FMath::Atan2(Axis|(R^V),R|V);
}

// Elbow on the shoulder-wrist circle at the given swivel; bone lengths exact.
void ElbowAt(const FVector& A,const FVector& Goal,double L1,double L2,double Psi,const FVector& Reference,FVector& E,FVector& H)
{
    const double Reach=FMath::Clamp(FVector::Dist(A,Goal),FMath::Abs(L1-L2)+1e-3,L1+L2-1e-3);
    const FVector Axis=(Goal-A).GetSafeNormal();
    const double Along=(L1*L1-L2*L2+Reach*Reach)/(2.0*Reach);
    const FVector Side=(Reference-Axis*(Reference|Axis)).GetSafeNormal();
    E=A+Axis*Along+FQuat(Axis,Psi).RotateVector(Side)*FMath::Sqrt(FMath::Max(L1*L1-Along*Along,0.0));
    H=A+Axis*Reach;
}

bool SampleComponent(const UAnimSequence& Anim,FName Bone,FTransform& Out)
{
    const USkeleton* Skeleton=Anim.GetSkeleton();
    if(!Skeleton)return false;
    const FReferenceSkeleton& Ref=Skeleton->GetReferenceSkeleton();
    int32 Index=Ref.FindBoneIndex(Bone);
    if(Index==INDEX_NONE)return false;
    Out=FTransform::Identity;
    for(;Index!=INDEX_NONE;Index=Ref.GetParentIndex(Index))
    {
        FTransform Local;
        Anim.GetBoneTransform(Local,FSkeletonPoseBoneIndex(Index),FAnimExtractContext(0.0,false),false);
        Out=Out*Local;
    }
    return true;
}

struct FGripReferencePose
{
    FTransform Gun,Clavicle,Shoulder,Elbow,HandPose;
    bool Sample(const UAnimSequence& Anim)
    {
        return SampleComponent(Anim,TEXT("WPN_root"),Gun)&&SampleComponent(Anim,TEXT("clavicle_l"),Clavicle)
            &&SampleComponent(Anim,TEXT("upperarm_l"),Shoulder)&&SampleComponent(Anim,TEXT("lowerarm_l"),Elbow)
            &&SampleComponent(Anim,TEXT("hand_l"),HandPose);
    }
    FQuat GripRotation() const{return (Gun.GetRotation().Inverse()*HandPose.GetRotation()).GetNormalized();}
    FVector GripLocation() const{return Gun.GetRotation().UnrotateVector(HandPose.GetLocation()-Gun.GetLocation());}
};
}

int32 FGripPoseLayer::Mode()
{
    return CVarGripLayer.GetValueOnAnyThread();
}

bool FGripPoseLayer::CacheRig(const FReferenceSkeleton& Ref)
{
    Root=Ref.FindBoneIndex(TEXT("WPN_root"));
    if(Root==INDEX_NONE)return false;
    for(int32 I=0;I<ArmCount;++I)if((Arm[I]=Ref.FindBoneIndex(ArmNames[I]))==INDEX_NONE)return false;
    TArray<FTransform> Rest=Ref.GetRefBonePose();
    for(int32 I=0;I<Rest.Num();++I)if(const int32 Parent=Ref.GetParentIndex(I);Parent>=0)Rest[I]=Rest[I]*Rest[Parent];
    FVector P[ArmCount];
    for(int32 I=0;I<ArmCount;++I){BindRotation[I]=Rest[Arm[I]].GetRotation();P[I]=Rest[Arm[I]].GetLocation();Offset[I]=FVector::ZeroVector;Station[I]=0.0;}
    U0=P[Lower]-P[Upper];
    F0=P[Hand]-P[Lower];
    BindForearmFrame=Frame(F0,U0^F0);
    const auto Place=[&](int32 I,const FVector& Origin,const FVector& Axis)
    {
        Station[I]=((P[I]-Origin)|Axis)/(Axis|Axis);
        Offset[I]=P[I]-Origin-Station[I]*Axis;
    };
    Place(UpperTwist1,P[Upper],U0);Place(UpperTwist2,P[Upper],U0);
    Place(LowerTwist2,P[Lower],F0);Place(LowerTwist1,P[Lower],F0);
    Fingers.Reset();
    for(int32 I=Arm[Hand]+1;I<Ref.GetNum();++I)
    {
        const FString Name=Ref.GetBoneName(I).ToString();
        if(Ref.BoneIsChildOf(I,Arm[Hand])&&Name.EndsWith(TEXT("_l"))&&(Name.StartsWith(TEXT("thumb_"))||Name.StartsWith(TEXT("index_"))
            ||Name.StartsWith(TEXT("middle_"))||Name.StartsWith(TEXT("ring_"))||Name.StartsWith(TEXT("pinky_"))))Fingers.Add(I);
    }
    return true;
}

FQuat FGripPoseLayer::Anatomical(const FVector& U,const FVector& F) const
{
    return FQuat(F.GetSafeNormal(),CreaseRoll*CreaseWeight(Bend(U,F)))*Frame(F,U^F)*BindForearmFrame.Inverse();
}

double FGripPoseLayer::PalmTotal(const FQuat& HandRotation,const FVector& A,const FVector& E,const FVector& H) const
{
    return Twist(Anatomical(E-A,H-E).Inverse()*(HandRotation*BindRotation[Hand].Inverse()),F0);
}

bool FGripPoseLayer::CacheGrips(const FReferenceSkeleton& Ref)
{
    FGripReferencePose B,F;
    if(!GripBase||!GripFamily||!GripFamily->GetSkeleton()||!B.Sample(*GripBase)||!F.Sample(*GripFamily))return false;
    BaseGripRotation=B.GripRotation();BaseGripLocation=B.GripLocation();
    GripOffsetRotation=(BaseGripRotation.Inverse()*F.GripRotation()).GetNormalized();
    GripOffsetLocation=BaseGripRotation.UnrotateVector(F.GripLocation()-BaseGripLocation);
    ClavicleDelta=(F.Clavicle.GetRotation()*B.Clavicle.GetRotation().Inverse()).GetNormalized();
    ClavicleShift=F.Clavicle.GetLocation()-B.Clavicle.GetLocation();
    const FVector A=B.Shoulder.GetLocation(),E=B.Elbow.GetLocation(),H=B.HandPose.GetLocation();
    // Family elbow swivel measured from the base elbow carried by the full clavicle delta; at
    // runtime the carried base elbow is the reference, so no fixed direction can degenerate.
    const auto Carry=[&](const FVector& Point){return F.Clavicle.GetLocation()+ClavicleDelta.RotateVector(Point-B.Clavicle.GetLocation());};
    SwivelShift=Swivel(F.Elbow.GetLocation(),F.Shoulder.GetLocation(),F.HandPose.GetLocation(),Carry(E)-Carry(A));
    TotalShift=FMath::UnwindRadians(PalmTotal(F.HandPose.GetRotation(),F.Shoulder.GetLocation(),F.Elbow.GetLocation(),F.HandPose.GetLocation())
        -PalmTotal(B.HandPose.GetRotation(),A,E,H));
    const FReferenceSkeleton& SkeletonRef=GripFamily->GetSkeleton()->GetReferenceSkeleton();
    FamilyFingers.Reset();
    for(const int32 Bone:Fingers)
    {
        const int32 Index=SkeletonRef.FindBoneIndex(Ref.GetBoneName(Bone));
        if(Index==INDEX_NONE)return false;
        FTransform Local;
        GripFamily->GetBoneTransform(Local,FSkeletonPoseBoneIndex(Index),FAnimExtractContext(0.0,false),false);
        FamilyFingers.Add(Local.GetRotation().GetNormalized());
    }
    return true;
}

float FGripPoseLayer::Apply(const FReferenceSkeleton& Ref,const USkeletalMesh* Mesh,const UAnimSequence* BaseRef,
    const UAnimSequence* FamilyRef,TArray<FTransform>& Local,float DeltaSeconds)
{
    if(Mesh!=RigMesh){RigMesh=Mesh;bRig=CacheRig(Ref);GripBase=GripFamily=nullptr;}
    if(!bRig||Local.Num()!=Ref.GetNum())return 0.f;
    if(BaseRef!=GripBase||FamilyRef!=GripFamily){GripBase=BaseRef;GripFamily=FamilyRef;bGrips=CacheGrips(Ref);ResetState();}
    if(!bGrips)return 0.f;
    Space.SetNum(Local.Num());
    for(int32 I=0;I<Local.Num();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        Space[I]=Parent==INDEX_NONE?Local[I]:Local[I]*Space[Parent];
    }
    const FQuat GunRotation=Space[Root].GetRotation();
    const FVector GunLocation=Space[Root].GetLocation();
    const FQuat HandRotation=(GunRotation.Inverse()*Space[Arm[Hand]].GetRotation()).GetNormalized();
    const FVector HandLocation=GunRotation.UnrotateVector(Space[Arm[Hand]].GetLocation()-GunLocation);
    const float Target=static_cast<float>((1.0-FMath::SmoothStep(WeightDistanceCm.X,WeightDistanceCm.Y,FVector::Dist(HandLocation,BaseGripLocation)))
        *(1.0-FMath::SmoothStep(WeightAngleDeg.X,WeightAngleDeg.Y,FMath::RadiansToDegrees(BaseGripRotation.AngularDistance(HandRotation)))));
    State=bHasState?State+FMath::Clamp(Target-State,-WeightRate*DeltaSeconds,WeightRate*DeltaSeconds):Target;
    bHasState=true;
    const float Weight=FMath::SmoothStep(0.f,1.f,State);
    if(Weight<=0.f)return 0.f;
    // Shoulder girdle: component-space delta of the reference pair, arm carried rigidly.
    FQuat R[ArmCount];FVector P[ArmCount];
    const FQuat Girdle=FQuat::Slerp(FQuat::Identity,ClavicleDelta,Weight);
    const FVector Pivot=Space[Arm[Clavicle]].GetLocation();
    for(int32 I=0;I<ArmCount;++I)
    {
        R[I]=(Girdle*Space[Arm[I]].GetRotation()).GetNormalized();
        P[I]=Pivot+ClavicleShift*Weight+Girdle.RotateVector(Space[Arm[I]].GetLocation()-Pivot);
    }
    const FQuat TargetRotation=(GunRotation*HandRotation*FQuat::Slerp(FQuat::Identity,GripOffsetRotation,Weight)).GetNormalized();
    const FVector TargetLocation=GunLocation+GunRotation.RotateVector(HandLocation+HandRotation.RotateVector(GripOffsetLocation*Weight));
    SolveArm(R,P,TargetRotation,TargetLocation,Weight*SwivelShift,P[Lower]-P[Upper],Weight*TotalShift);
    for(int32 I=0;I<ArmCount;++I)
    {
        FTransform& Bone=Space[Arm[I]];
        Bone.SetRotation(R[I]);Bone.SetLocation(P[I]);
        const int32 Parent=Ref.GetParentIndex(Arm[I]);
        Local[Arm[I]]=Parent==INDEX_NONE?Bone:Bone.GetRelativeTransform(Space[Parent]);
    }
    for(int32 I=0;I<Fingers.Num();++I)
        Local[Fingers[I]].SetRotation(FQuat::Slerp(Local[Fingers[I]].GetRotation(),FamilyFingers[I],Weight).GetNormalized());
    return Weight;
}

void FGripPoseLayer::SolveArm(FQuat* R,FVector* P,const FQuat& HandTarget,const FVector& HandGoal,double Psi,
    const FVector& SwivelAxisRef,double Shift) const
{
    const FVector A=P[Upper],E0=P[Lower],H0=P[Hand];
    FVector E1,H1;
    ElbowAt(A,HandGoal,FVector::Dist(A,E0),FVector::Dist(E0,H0),Psi,SwivelAxisRef,E1,H1);
    const FVector U0Now=E0-A,F0Now=H0-E0,U1=E1-A,F1=H1-E1,Fa=F1.GetSafeNormal();
    const FQuat Dl0=Anatomical(U0Now,F0Now),Dl1=Anatomical(U1,F1);
    const FQuat ElbowBase=R[Lower]*BindRotation[Lower].Inverse();
    const double UpperBase=Twist(ElbowBase*Dl0.Inverse(),F0Now);
    const double ForearmBase=1.5*Twist(R[LowerTwist1]*BindRotation[LowerTwist1].Inverse()*ElbowBase.Inverse(),F0Now);
    // Total palm roll of the new arm, taken on the branch nearest the base total shifted by the
    // reference pair's difference (never flips). The change of its capped forearm share goes to
    // the forearm stations, the rest to the upper-arm roll (ArmHinge55 split); the base arm's
    // own (smoothed) split is kept, so weight 0 returns it unchanged.
    const FQuat HandBind=BindRotation[Hand].Inverse();
    const double Total0=Twist(Dl0.Inverse()*(R[Hand]*HandBind),F0);
    const double Branch=Total0+Shift;
    const double Total1=Branch+FMath::UnwindRadians(Twist(Dl1.Inverse()*(HandTarget*HandBind),F0)-Branch);
    const double Forearm=ForearmBase+CapForearm(Total1)-CapForearm(Total0);
    const double UpperRoll=UpperBase+(Total1-CapForearm(Total1))-(Total0-CapForearm(Total0));
    const FQuat Elbow=(FQuat(Fa,UpperRoll)*Dl1).GetNormalized();
    const FQuat UpperFrame=FQuat::FindBetweenNormals(Elbow.RotateVector(U0).GetSafeNormal(),U1.GetSafeNormal())*Elbow;
    R[Upper]=(FQuat::FindBetweenNormals(U0Now.GetSafeNormal(),U1.GetSafeNormal())*R[Upper]).GetNormalized();
    for(const int32 I:{UpperTwist1,UpperTwist2})
    {
        R[I]=(UpperFrame*BindRotation[I]).GetNormalized();
        P[I]=A+Station[I]*U1+UpperFrame.RotateVector(Offset[I]);
    }
    R[Lower]=(Elbow*BindRotation[Lower]).GetNormalized();
    P[Lower]=E1;
    for(const int32 I:{LowerTwist2,LowerTwist1})
    {
        const FQuat Segment=FQuat(Fa,Forearm*PronationShare[I])*Elbow;
        R[I]=(Segment*BindRotation[I]).GetNormalized();
        P[I]=E1+Station[I]*F1+Segment.RotateVector(Offset[I]);
    }
    R[Hand]=HandTarget;
    P[Hand]=H1;
}

void FGripPoseLayerNode::Update_AnyThread(const FAnimationUpdateContext& Context)
{
    Source.Update(Context);
    DeltaSeconds=Context.GetDeltaTime();
}

void FGripPoseLayerNode::Evaluate_AnyThread(FPoseContext& Output)
{
    Source.Evaluate(Output);
    const FBoneContainer& Bones=Output.Pose.GetBoneContainer();
    // A stale configuration (weapon switched without an action-pose update) never applies.
    if(!bEnabled||!BaseRef||!FamilyRef||FGripPoseLayer::Mode()==0||BaseRef->GetSkeleton()!=Bones.GetSkeletonAsset()
        ||FamilyRef->GetSkeleton()!=Bones.GetSkeletonAsset()){Layer.ResetState();LastClip=nullptr;return;}
    if(Clip!=LastClip){LastClip=Clip;Layer.ResetState();}
    const FReferenceSkeleton& Ref=Bones.GetReferenceSkeleton();
    Local=Ref.GetRefBonePose();
    for(const FCompactPoseBoneIndex Index:Output.Pose.ForEachBoneIndex())Local[Bones.MakeMeshPoseIndex(Index).GetInt()]=Output.Pose[Index];
    if(Layer.Apply(Ref,Bones.GetSkeletalMeshAsset(),BaseRef,FamilyRef,Local,DeltaSeconds)<=0.f)return;
    for(const FCompactPoseBoneIndex Index:Output.Pose.ForEachBoneIndex())Output.Pose[Index]=Local[Bones.MakeMeshPoseIndex(Index).GetInt()];
}

int32 AFPSGAMECharacter::GripLayerMode() const
{
    if(WeaponGripProfileFor(ResolveRifleGripProfile()))return 0; // Authored differences replace the older IK layer.
    if(!PKMLowpolyWeaponAssets::Matches(AKMViewmodel)&&!LMG201WeaponAssets::Matches(AKMViewmodel))return 0;
    return GripFamilyClip(IdleAnimation)?FMath::Clamp(FGripPoseLayer::Mode(),0,2):0;
}

UAnimSequence* AFPSGAMECharacter::GripFamilyClip(UAnimSequence* Base) const
{
    const auto* Family=HasAngledForegrip()?&ForegripAnimations:HasCantedForegrip()?&CantedGripAnimations
        :HasVerticalForegrip()?&VerticalGripAnimations:HasPrismHandstop()?&PrismGripAnimations:nullptr;
    const auto* Clip=Family&&Base?Family->Find(Base):nullptr;
    return Clip?Clip->Get():nullptr;
}
