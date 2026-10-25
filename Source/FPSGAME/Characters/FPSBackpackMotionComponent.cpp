#include "FPSBackpackMotionComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include <cmath>

namespace FPSBackpackMotion
{
TAutoConsoleVariable<float> Strength(TEXT("fps.Backpack.Sway"),1.f,
    TEXT("Backpack cosmetic inertia strength, 0..1. Does not affect inventory or collision."),ECVF_Default);
FVector Vector(const TSharedPtr<FJsonObject>& Json,const TCHAR* Key,const FVector& Fallback)
{
    const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
    if(!Json->TryGetArrayField(Key,Values)||Values->Num()!=3)return Fallback;
    return FVector((*Values)[0]->AsNumber(),(*Values)[1]->AsNumber(),(*Values)[2]->AsNumber());
}
float Number(const TSharedPtr<FJsonObject>& Json,const TCHAR* Key,float Fallback)
{
    double Value=Fallback;Json->TryGetNumberField(Key,Value);return float(Value);
}
void Spring(FVector& X,FVector& V,const FVector& Target,float W,float D,float Step)
{
    V+=(W*W*(Target-X)-2.f*D*W*V)*Step;X+=V*Step;
}
void Limit(FVector& X,FVector& V,const FVector& Limits)
{
    for(int32 I=0;I<3;++I)
        if(FMath::Abs(X[I])>Limits[I])
        {X[I]=FMath::Clamp(X[I],-Limits[I],Limits[I]);if(X[I]*V[I]>0)V[I]=0;}
}
}

UFPSBackpackMotionComponent::UFPSBackpackMotionComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

void UFPSBackpackMotionComponent::Clear()
{
    if(auto* Source=Body.Get())RemoveTickPrerequisiteComponent(Source);
    if(auto* Target=Pack.Get())
    {const float Zero[30]={};Target->SetCustomPrimitiveDataFloatArray(0,MakeArrayView(Zero));}
    if(auto* Rigid=RigidBody.Get())Rigid->SetRelativeTransform(RigidReference*InverseBind);
    Body.Reset();Pack.Reset();RigidBody.Reset();Spine=INDEX_NONE;bSent=false;Hanging=FFPSHangingPack();
    SetComponentTickEnabled(false);ResetMotion();
}

void UFPSBackpackMotionComponent::Configure(USkeletalMeshComponent* InBody,USkeletalMeshComponent* InPack,const TSharedPtr<FJsonObject>& Settings,FName Shirt)
{
    Clear();if(!InBody||!InPack||!Settings||GetNetMode()==NM_DedicatedServer)return;
    const TSharedPtr<FJsonObject>* Json=nullptr;
    if(!Settings->TryGetObjectField(TEXT("backpack_motion"),Json))return;
    const auto* Mesh=InBody->GetSkeletalMeshAsset();if(!Mesh)return;
    const FReferenceSkeleton& Ref=Mesh->GetRefSkeleton();Spine=Ref.FindBoneIndex(TEXT("spine_03"));if(Spine==INDEX_NONE)return;
    FTransform Bind=Ref.GetRefBonePose()[Spine];
    for(int32 Parent=Ref.GetParentIndex(Spine);Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))Bind=Bind*Ref.GetRefBonePose()[Parent];
    InverseBind=Bind.Inverse();Body=InBody;Pack=InPack;
    using namespace FPSBackpackMotion;
    Pivot=Vector(*Json,TEXT("pivot"),Pivot);BoundsMin=Vector(*Json,TEXT("bounds_min"),BoundsMin);BoundsMax=Vector(*Json,TEXT("bounds_max"),BoundsMax);
    Frequency=FMath::Clamp(Number(*Json,TEXT("frequency_hz"),3.5f),2.f,6.f);
    Damping=FMath::Clamp(Number(*Json,TEXT("damping"),.85f),.7f,1.2f);
    MaxAngle=FMath::Clamp(Number(*Json,TEXT("max_angle_degrees"),2.5f),0.f,3.5f);
    MaxBounce=FMath::Clamp(Number(*Json,TEXT("max_bounce_cm"),.35f),0.f,.6f);
    ResponseScale=FMath::Clamp(Number(*Json,TEXT("response_scale"),1.f),.25f,6.f);
    MaxDisplacement=FMath::Clamp(Number(*Json,TEXT("max_displacement_cm"),0.f),0.f,6.f);
    GravitySag=FMath::Clamp(Number(*Json,TEXT("gravity_sag_cm"),.45f),0.f,.8f);
    MaxSeparation=FMath::Clamp(Number(*Json,TEXT("max_separation_cm"),.8f),.1f,1.5f);
    const TSharedPtr<FJsonObject>* Support=nullptr;const TSharedPtr<FJsonObject>* Supports=nullptr;
    if(!Shirt.IsNone()&&(*Json)->TryGetObjectField(TEXT("support_by_shirt"),Supports))
        (*Supports)->TryGetObjectField(Shirt.ToString(),Support);
    if(!Support)(*Json)->TryGetObjectField(TEXT("support"),Support);
    if(Support)
    {
        Pivot=Vector(*Support,TEXT("pivot"),Pivot);
        BoundsMin=Vector(*Support,TEXT("bounds_min"),BoundsMin);BoundsMax=Vector(*Support,TEXT("bounds_max"),BoundsMax);
    }
    ConfigureHanging(Settings,Shirt);
    AddTickPrerequisiteActor(GetOwner());AddTickPrerequisiteComponent(InBody);
    SetComponentTickEnabled(true);
}

void UFPSBackpackMotionComponent::ResetMotion()
{
    Angles=AngularVelocity=Offset=OffsetVelocity=LastVelocity=FVector::ZeroVector;
    AnchorVelocity=FrameAngularVelocity=FVector::ZeroVector;bInitialized=false;
    FMemory::Memzero(PreviousField);
    Hanging.Initialized=false;
}

void UFPSBackpackMotionComponent::AttachRigidBody(UStaticMeshComponent* InRigid,const FTransform& ReferencePose)
{
    if(!Body.IsValid()||Spine==INDEX_NONE||!InRigid)return;
    RigidBody=InRigid;RigidReference=ReferencePose;
    InRigid->SetRelativeTransform(RigidReference*InverseBind);
}

void UFPSBackpackMotionComponent::Push(const FTransform& Frame,const FQuat& Rotation,const FVector& Translation,bool bResetPrevious)
{
    auto* Target=Pack.Get();if(!Target)return;
    // High-detail packs can share one Nanite body while only their fitted
    // strap is skinned. Both receive the same pivot/rotation/translation.
    if(auto* Rigid=RigidBody.Get())
    {
        const FTransform Motion(Rotation,Pivot-Rotation.RotateVector(Pivot)+Translation);
        Rigid->SetRelativeTransform(RigidReference*Motion*InverseBind);
    }
    const FQuat Q=Frame.GetRotation()*Rotation*Frame.GetRotation().Inverse();
    const FVector X=Q.RotateVector(FVector::ForwardVector)-FVector::ForwardVector;
    const FVector Y=Q.RotateVector(FVector::RightVector)-FVector::RightVector;
    const FVector Z=Q.RotateVector(FVector::UpVector)-FVector::UpVector;
    const FVector P=Frame.TransformPosition(Pivot),T=Frame.TransformVectorNoScale(Translation);
    // Store R-I so zero custom primitive data is an exact stationary mesh.
    const FVector Values[]={P,FVector(X.X,Y.X,Z.X),FVector(X.Y,Y.Y,Z.Y),FVector(X.Z,Y.Z,Z.Z),T};
    float Data[30];for(int32 I=0;I<5;++I)for(int32 J=0;J<3;++J)Data[I*3+J]=float(Values[I][J]);
    FMemory::Memcpy(Data+15,bResetPrevious?Data:PreviousField,sizeof(PreviousField));
    bool bChanged=!bSent;
    for(int32 I=0;I<30&&!bChanged;++I)bChanged=!FMath::IsNearlyEqual(Data[I],LastSent[I],.00001f);
    if(bChanged){Target->SetCustomPrimitiveDataFloatArray(0,MakeArrayView(Data));FMemory::Memcpy(LastSent,Data,sizeof(Data));bSent=true;}
    FMemory::Memcpy(PreviousField,Data,sizeof(PreviousField));
}

void UFPSBackpackMotionComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    auto* Leader=Body.Get();auto* Target=Pack.Get();auto* Character=Cast<ACharacter>(GetOwner());
    if(!Leader||!Target||!Character){Clear();return;}
    const FTransform Frame=InverseBind*Leader->GetBoneTransform(Spine);
    // Simulated proxies can correct the capsule immediately while CMC keeps
    // the visible mesh smooth. Reset from that rendered carrier, otherwise a
    // network correction can snap the bag to rest on an unmoved torso.
    const FVector Position=Leader->GetComponentLocation(),Velocity=Character->GetVelocity();
    const FVector Anchor=Frame.TransformPosition(Pivot);
    const float Gain=FMath::Clamp(FPSBackpackMotion::Strength.GetValueOnGameThread(),0.f,1.f);
    if(Delta<=UE_SMALL_NUMBER)return;
    // A 100 ms cutoff erased every spring step below 10 FPS and on ordinary
    // hitches. Keep integrating low-rate frames; reset only a true long gap.
    const float MaxTravel=FMath::Max(150.f,float(Velocity.Size())*Delta*1.5f);
    if(!bInitialized||Delta>.35f||FVector::DistSquared(Position,LastPosition)>MaxTravel*MaxTravel
       ||!Target->IsVisible()||Target->bHiddenInGame||Gain<=0||Leader->IsSimulatingPhysics())
    {
        ResetMotion();LastPosition=Position;LastVelocity=Velocity;LastAnchor=Anchor;LastFrame=Frame.GetRotation();bInitialized=true;
        Push(Frame,FQuat::Identity,FVector::ZeroVector,true);
        if(Hanging.Enabled&&RigidBody.IsValid())UpdateHanging(Frame,0.f,Gain,true);
        return;
    }
    if(Hanging.Enabled&&RigidBody.IsValid())
    {
        LastPosition=Position;LastVelocity=Velocity;LastAnchor=Anchor;LastFrame=Frame.GetRotation();
        UpdateHanging(Frame,Delta,Gain,false);return;
    }
    // Sample the evaluated torso: walking/running cadence comes from the
    // actual native animation, rather than an independent sine-wave clock.
    const FVector RelativeVelocity=((Anchor-LastAnchor)/Delta-(LastVelocity+Velocity)*.5).GetClampedToMaxSize(300.f);
    const FVector Filtered=FMath::Lerp(AnchorVelocity,RelativeVelocity,1.f-FMath::Exp(-24.f*Delta));
    const float Moving=FMath::Clamp(Velocity.Size2D()/90.f,0.f,1.f);
    const FVector Acceleration=Frame.InverseTransformVectorNoScale((Velocity-LastVelocity)/Delta
        +(Filtered-AnchorVelocity)/Delta*Moving).GetClampedToMaxSize(2200.f);
    FVector Axis;double Angle;
    (LastFrame.Inverse()*Frame.GetRotation()).ToAxisAndAngle(Axis,Angle);
    Angle=FMath::UnwindRadians(Angle);
    FrameAngularVelocity=FMath::Lerp(FrameAngularVelocity,(Axis*FMath::RadiansToDegrees(Angle)/Delta).GetClampedToMaxSize(360.f),1.f-FMath::Exp(-18.f*Delta));
    AnchorVelocity=Filtered;LastPosition=Position;LastVelocity=Velocity;LastAnchor=Anchor;LastFrame=Frame.GetRotation();
    const float Response=Gain*MaxAngle/2.4f*ResponseScale;
    const FVector AngleTarget=(FVector(-Acceleration.Y*.0012f,Acceleration.X*.0012f,0.)-FrameAngularVelocity*.02f)*Response;
    // The shoulder straps support a loaded pack. Gravity takes up their small
    // elastic slack; its normal component is reacted by the torso/harness.
    // Express world gravity in the evaluated torso frame, not a global bob.
    const FVector Gravity=Frame.InverseTransformVectorNoScale(FVector(0,0,GetWorld()->GetGravityZ()))*(GravitySag/980.f);
    const FVector GravityTarget=FVector(Gravity.X,0.,Gravity.Z)*Gain;
    const FVector OffsetTarget=FVector(-Acceleration.X*.00015f,0.,-Acceleration.Z*.00045f)*Response+GravityTarget;
    const int32 Steps=FMath::Clamp(FMath::CeilToInt(Delta*120.f),1,42);const float Step=Delta/Steps,W=2.f*UE_PI*Frequency;
    for(int32 I=0;I<Steps;++I)
    {
        FPSBackpackMotion::Spring(Angles,AngularVelocity,AngleTarget,W,Damping,Step);
        FPSBackpackMotion::Spring(Offset,OffsetVelocity,OffsetTarget,W,Damping,Step);
        FPSBackpackMotion::Limit(Angles,AngularVelocity,FVector(MaxAngle,MaxAngle*.8f,MaxAngle*.7f)*Gain);
        const FVector ElasticLimit=FVector(.3f,0.f,MaxBounce)*Gain;
        for(int32 AxisIndex=0;AxisIndex<3;++AxisIndex)
        {
            const double Low=FMath::Min(0.,GravityTarget[AxisIndex])-ElasticLimit[AxisIndex];
            const double High=FMath::Max(0.,GravityTarget[AxisIndex])+ElasticLimit[AxisIndex];
            if(Offset[AxisIndex]<Low||Offset[AxisIndex]>High)
            {Offset[AxisIndex]=FMath::Clamp(Offset[AxisIndex],Low,High);OffsetVelocity[AxisIndex]=0.;}
        }
    }
    FQuat Rotation=FQuat(FVector::UpVector,FMath::DegreesToRadians(Angles.Z))
        *FQuat(FVector::RightVector,FMath::DegreesToRadians(Angles.Y))*FQuat(FVector::ForwardVector,FMath::DegreesToRadians(Angles.X));
    // The support box is measured on the rigid pack, excluding fitted straps.
    // Shift rearward by the worst forward advance: rotation cannot reduce the
    // calibrated body clearance, even for tall packs and quick direction changes.
    float ForwardAdvance=0.f;
    for(int32 I=0;I<8;++I)
    {
        const FVector P((I&1)?BoundsMax.X:BoundsMin.X,(I&2)?BoundsMax.Y:BoundsMin.Y,(I&4)?BoundsMax.Z:BoundsMin.Z);
        ForwardAdvance=FMath::Max(ForwardAdvance,float((Rotation.RotateVector(P-Pivot)-(P-Pivot)).Y));
    }
    // A conservative support-box correction must not leave the pack hovering
    // behind the wearer. Reduce rotation before applying an excessive retreat.
    if(ForwardAdvance>MaxSeparation)
    {
        Rotation=FQuat::Slerp(FQuat::Identity,Rotation,MaxSeparation/ForwardAdvance).GetNormalized();
        ForwardAdvance=0.f;
        for(int32 I=0;I<8;++I)
        {
            const FVector P((I&1)?BoundsMax.X:BoundsMin.X,(I&2)?BoundsMax.Y:BoundsMin.Y,(I&4)?BoundsMax.Z:BoundsMin.Z);
            ForwardAdvance=FMath::Max(ForwardAdvance,float((Rotation.RotateVector(P-Pivot)-(P-Pivot)).Y));
        }
    }
    FVector Translation=Offset;Translation.Y=-ForwardAdvance;
    // Taut sewn straps limit the total travel, including simultaneous yaw,
    // roll and bounce. Axis limits alone allow their diagonal sum to stretch
    // the short rear strap spans. Ease into the last 30% of available travel.
    float PeakTravel=0.f;
    for(int32 I=0;MaxDisplacement>0.f&&I<8;++I)
    {
        const FVector P((I&1)?BoundsMax.X:BoundsMin.X,(I&2)?BoundsMax.Y:BoundsMin.Y,(I&4)?BoundsMax.Z:BoundsMin.Z);
        PeakTravel=FMath::Max(PeakTravel,float((Rotation.RotateVector(P-Pivot)-(P-Pivot)+Translation).Size()));
    }
    const float SoftStart=MaxDisplacement*.7f;
    if(MaxDisplacement>0.f&&PeakTravel>SoftStart)
    {
        const float LimitedTravel=SoftStart+(MaxDisplacement-SoftStart)*std::tanh((PeakTravel-SoftStart)/(MaxDisplacement-SoftStart));
        const float Ratio=LimitedTravel/PeakTravel;
        Rotation=FQuat::Slerp(FQuat::Identity,Rotation,Ratio).GetNormalized();Translation*=Ratio;
        // Re-evaluate support after limiting rotation; the outward correction
        // must correspond to the final rigid pose, not a scaled old estimate.
        ForwardAdvance=0.f;
        for(int32 I=0;I<8;++I)
        {
            const FVector P((I&1)?BoundsMax.X:BoundsMin.X,(I&2)?BoundsMax.Y:BoundsMin.Y,(I&4)?BoundsMax.Z:BoundsMin.Z);
            ForwardAdvance=FMath::Max(ForwardAdvance,float((Rotation.RotateVector(P-Pivot)-(P-Pivot)).Y));
        }
        Translation.Y=-ForwardAdvance;
    }
    Push(Frame,Rotation,Translation);
}
