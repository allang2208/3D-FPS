#include "FPSBackpackHangingMotion.h"
#include "FPSBackpackMotionComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"
#include "GameFramework/Actor.h"

namespace FPSHangingPack
{
struct FWorldHull
{
    int32 SidePlanes=0;
    TArray<FPlane,TInlineAllocator<20>> Planes;
};
FWorldHull TransformHull(const FFPSHangingHull& Hull,const FTransform& Frame)
{
    FWorldHull Result;Result.SidePlanes=Hull.SidePlanes;
    for(const auto& P:Hull.Planes)
    {
        const FVector N=Frame.TransformVectorNoScale(FVector(P.X,P.Y,P.Z)/Frame.GetScale3D());
        const double Length=N.Size(),D=(P.W-FVector::DotProduct(N,Frame.GetLocation()))/Length;
        const FVector Unit=N/Length;Result.Planes.Add(FPlane(Unit.X,Unit.Y,Unit.Z,D));
    }
    return Result;
}
FVector Vector(const TArray<TSharedPtr<FJsonValue>>& A)
{
    return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());
}
void Rotate(FFPSHangingPack& S,const FVector& Delta)
{
    const double Angle=Delta.Size();
    if(Angle>UE_SMALL_NUMBER)S.Rotation=(FQuat(Delta/Angle,Angle)*S.Rotation).GetNormalized();
}
void Correct(FFPSHangingPack& S,const FVector& Lever,const FVector& Normal,double Error)
{
    const FVector AngularGradient=FVector::CrossProduct(Lever,Normal);
    const double Lambda=-Error/(1.+S.InverseInertia*AngularGradient.SizeSquared());
    S.Position+=Normal*Lambda;
    Rotate(S,AngularGradient*(S.InverseInertia*Lambda));
}
FVector Support(const FFPSHangingTether& T,USkeletalMeshComponent* Body)
{
    FVector Anchor=FVector::ZeroVector;
    for(const auto& I:T.Support)Anchor+=Body->GetBoneTransform(I.Bone).TransformPosition(I.Local)*I.Weight;
    return Anchor;
}
// Caps determine whether a torso slice overlaps a probe; side faces determine
// the separation direction. Internal slice ends must not behave like ledges.
bool Contact(FFPSHangingPack& S,const FWorldHull& Hull)
{
    bool Hit=false;
    for(const FVector& Probe:S.Probes)
    {
        const FVector Lever=S.Rotation.RotateVector(Probe);
        const FVector Point=S.Position+Lever;
        double Closest=-DBL_MAX;FVector Normal=FVector::ZeroVector;bool Inside=true;
        for(int32 I=Hull.SidePlanes;I<Hull.Planes.Num();++I)
        {
            const auto& P=Hull.Planes[I];
            if(FVector::DotProduct(FVector(P.X,P.Y,P.Z),Point)+P.W>=S.ContactRadius){Inside=false;break;}
        }
        if(!Inside)continue;
        for(int32 I=0;I<Hull.SidePlanes;++I)
        {
            const FPlane& P=Hull.Planes[I];
            const FVector N(P.X,P.Y,P.Z);
            const double Distance=FVector::DotProduct(N,Point)+P.W;
            if(Distance>=S.ContactRadius){Inside=false;break;}
            if(Distance>Closest){Closest=Distance;Normal=N;}
        }
        if(Inside&&Closest>-DBL_MAX)
        {
            Correct(S,Lever,Normal,Closest-S.ContactRadius);Hit=true;
        }
    }
    return Hit;
}
void LimitPose(FFPSHangingPack& S,const FTransform& Frame,const FVector& Center)
{
    S.Position=Center+(S.Position-Center).GetClampedToMaxSize(S.MaxTravel);
    FQuat Relative=Frame.GetRotation().Inverse()*S.Rotation;
    if(Relative.W<0)Relative=Relative*-1.;
    FVector Axis;double Angle;Relative.ToAxisAndAngle(Axis,Angle);
    const double Limit=FMath::DegreesToRadians(S.MaxAngle);
    if(Angle>Limit)S.Rotation=(Frame.GetRotation()*FQuat(Axis,Limit)).GetNormalized();
}
}

void UFPSBackpackMotionComponent::ConfigureHanging(const TSharedPtr<FJsonObject>& Settings,FName Shirt)
{
    const TSharedPtr<FJsonObject>* Json=nullptr;
    if(!Settings->TryGetObjectField(TEXT("hanging_pack"),Json))return;
    const TSharedPtr<FJsonObject>* ByShirt=nullptr;
    if(!Shirt.IsNone()&&Settings->TryGetObjectField(TEXT("hanging_pack_by_shirt"),ByShirt))
    {
        const TSharedPtr<FJsonObject>* Fitted=nullptr;
        if((*ByShirt)->TryGetObjectField(Shirt.ToString(),Fitted))Json=Fitted;
    }
    auto* Leader=Body.Get();if(!Leader)return;
    FFPSHangingPack Data;
    const auto& Source=**Json;
    const auto& Tethers=Source.GetArrayField(TEXT("tethers"));
    const auto& Hulls=Source.GetArrayField(TEXT("hulls"));
    const auto& Probes=Source.GetArrayField(TEXT("probes"));
    // Authoring contract bounds both memory and the per-frame contact budget.
    if(Tethers.Num()!=2||Hulls.IsEmpty()||Hulls.Num()>6||Probes.IsEmpty()||Probes.Num()>24)return;
    const FVector Center=FPSHangingPack::Vector(Source.GetArrayField(TEXT("center")));
    for(const auto& Value:Tethers)
    {
        const auto J=Value->AsObject();FFPSHangingTether T;
        T.Point=FPSHangingPack::Vector(J->GetArrayField(TEXT("point")))-Center;
        T.Length=J->GetNumberField(TEXT("length"));if(T.Length<=0||T.Length>30.f)return;
        const auto& Bindings=J->GetArrayField(TEXT("support"));if(Bindings.IsEmpty()||Bindings.Num()>8)return;
        float Total=0.f;
        for(const auto& Binding:Bindings)
        {
            const auto B=Binding->AsObject();FFPSHangingInfluence I;
            I.Bone=Leader->GetBoneIndex(FName(*B->GetStringField(TEXT("bone"))));if(I.Bone==INDEX_NONE)return;
            I.Local=FPSHangingPack::Vector(B->GetArrayField(TEXT("local")));I.Weight=B->GetNumberField(TEXT("weight"));
            Total+=I.Weight;T.Support.Add(I);
        }
        if(Total<=UE_SMALL_NUMBER)return;
        for(auto& I:T.Support)I.Weight/=Total;
        Data.Tethers.Add(MoveTemp(T));
    }
    for(const auto& Value:Hulls)
    {
        const auto J=Value->AsObject();FFPSHangingHull H;
        H.Bone=Leader->GetBoneIndex(FName(*J->GetStringField(TEXT("bone"))));if(H.Bone==INDEX_NONE)return;
        H.SidePlanes=J->GetIntegerField(TEXT("side_planes"));
        const auto& Planes=J->GetArrayField(TEXT("planes"));
        if(H.SidePlanes<4||Planes.Num()!=H.SidePlanes+2||Planes.Num()>20)return;
        for(const auto& Plane:Planes)
        {
            const auto& V=Plane->AsArray();H.Planes.Add(FPlane(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber(),V[3]->AsNumber()));
        }
        Data.Hulls.Add(MoveTemp(H));
    }
    for(const auto& Probe:Probes)Data.Probes.Add(FPSHangingPack::Vector(Probe->AsArray())-Center);
    Data.Enabled=true;Hanging=MoveTemp(Data);Pivot=Center;
}

void UFPSBackpackMotionComponent::UpdateHanging(const FTransform& Frame,float Delta,float Gain,bool Reset)
{
    auto* Leader=Body.Get();if(!Leader)return;
    auto& S=Hanging;
    TArray<FVector,TInlineAllocator<2>> Anchors;
    TArray<FTransform,TInlineAllocator<6>> Frames;
    for(auto& T:S.Tethers)Anchors.Add(FPSHangingPack::Support(T,Leader));
    for(auto& H:S.Hulls)Frames.Add(Leader->GetBoneTransform(H.Bone));
    const FVector Center=Frame.TransformPosition(Pivot);
    if(Reset||!S.Initialized)
    {
        S.Position=Center;S.Rotation=Frame.GetRotation();S.Velocity=GetOwner()->GetVelocity();S.AngularVelocity=FVector::ZeroVector;
        S.PreviousCarrier=Frame;
        for(int32 I=0;I<S.Tethers.Num();++I)S.Tethers[I].PreviousAnchor=Anchors[I];
        for(int32 I=0;I<S.Hulls.Num();++I)S.Hulls[I].PreviousFrame=Frames[I];
        S.Initialized=true;return;
    }
    const int32 Steps=FMath::Clamp(FMath::CeilToInt(Delta*120.f),1,24);
    const float Dt=Delta/Steps;
    const FVector Gravity(0,0,GetWorld()->GetGravityZ());
    for(int32 Step=0;Step<Steps;++Step)
    {
        const FVector OldPosition=S.Position;const FQuat OldRotation=S.Rotation;
        const FVector CarrierVelocity=GetOwner()->GetVelocity();
        S.Velocity=CarrierVelocity+(S.Velocity-CarrierVelocity)*FMath::Exp(-S.LinearDamping*Dt/FMath::Max(Gain,.1f));
        S.AngularVelocity*=FMath::Exp(-S.AngularDamping*Dt);
        S.Velocity+=Gravity*Dt;S.Position+=S.Velocity*Dt;
        FPSHangingPack::Rotate(S,S.AngularVelocity*Dt);
        const float Alpha=float(Step+1)/Steps;
        FTransform Carrier;Carrier.Blend(S.PreviousCarrier,Frame,Alpha);
        const FVector StepCenter=Carrier.TransformPosition(Pivot);
        TArray<FPSHangingPack::FWorldHull,TInlineAllocator<6>> ContactHulls;
        for(int32 I=0;I<S.Hulls.Num();++I)
        {
            FTransform F;F.Blend(S.Hulls[I].PreviousFrame,Frames[I],Alpha);
            ContactHulls.Add(FPSHangingPack::TransformHull(S.Hulls[I],F));
        }
        bool Contacted=false;
        for(int32 Iteration=0;Iteration<5;++Iteration)
        {
            FPSHangingPack::LimitPose(S,Carrier,StepCenter);
            for(int32 I=0;I<S.Tethers.Num();++I)
            {
                const auto& T=S.Tethers[I];const FVector Anchor=FMath::Lerp(T.PreviousAnchor,Anchors[I],Alpha);
                const FVector Lever=S.Rotation.RotateVector(T.Point),D=S.Position+Lever-Anchor;
                const double Length=D.Size();
                // A strap resists extension, never compression. Gravity takes
                // up slack; this does not pin the pouch to a floating rest pose.
                if(Length>T.Length)FPSHangingPack::Correct(S,Lever,D/Length,Length-T.Length);
            }
            for(const auto& H:ContactHulls)Contacted|=FPSHangingPack::Contact(S,H);
        }
        S.Velocity=(S.Position-OldPosition)/Dt;
        FQuat Turn=S.Rotation*OldRotation.Inverse();if(Turn.W<0)Turn=Turn*-1.;
        FVector Axis;double Angle;Turn.ToAxisAndAngle(Axis,Angle);
        S.AngularVelocity=(Axis*(Angle/Dt)).GetClampedToMaxSize(5.);
        FVector Relative=(S.Velocity-CarrierVelocity).GetClampedToMaxSize(180.);
        if(Contacted){Relative*=FMath::Exp(-10.f*Dt);S.AngularVelocity*=FMath::Exp(-6.f*Dt);}
        S.Velocity=CarrierVelocity+Relative;
    }
    for(int32 I=0;I<S.Tethers.Num();++I)S.Tethers[I].PreviousAnchor=Anchors[I];
    for(int32 I=0;I<S.Hulls.Num();++I)S.Hulls[I].PreviousFrame=Frames[I];
    S.PreviousCarrier=Frame;
    const FQuat Rotation=Frame.GetRotation().Inverse()*S.Rotation;
    const FVector Translation=Frame.InverseTransformPosition(S.Position)-Pivot;
    Push(Frame,Rotation,Translation);
}
