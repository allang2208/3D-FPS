#pragma once
#include "FireballHandPose.h"

struct FFireballArmMotion
{
    FVector Wrist=FVector::ZeroVector, Shoulder=FVector::ZeroVector, Pole=FVector::ZeroVector;
    FQuat Rotation=FQuat::Identity;
    float Palm=0.f, Fingers=1.f, Layer=1.f;
};

// Camera-space authoring clock. The editable source in FireballCast20260914
// uses these same curves; neither the weapon clip nor movement is retimed.
namespace FireballCastMotion
{
    struct FKey { float Time, Value, Slope; };
    inline constexpr FKey GatherKeys[]={
        {0,0,0},{.14f,.035f,.45f},{.38f,.30f,1.45f},
        {.68f,.78f,1.3f},{.86f,.97f,.4f},{1,1,0}};
    inline constexpr FKey PushKeys[]={
        {0,0,0},{.22f,-.07f,0},{.65f,.50f,2.3f},
        {1,.94f,.3f},{1.5f,1,0}};
    inline constexpr FKey ReturnKeys[]={
        {0,0,0},{.2f,.10f,.85f},{.55f,.65f,1.55f},{.85f,.96f,.55f},{1,1,0}};
    inline float Ease(float T)
    { T=FMath::Clamp(T,0.f,1.f);return T*T*T*(T*(T*6.f-15.f)+10.f); }
    template<SIZE_T N> float Curve(const FKey (&Keys)[N],float T)
    {
        if(T<=Keys[0].Time)return Keys[0].Value;
        for(SIZE_T I=1;I<N;++I)if(T<Keys[I].Time)
        {
            const auto& A=Keys[I-1];const auto& B=Keys[I];
            const float Span=B.Time-A.Time,U=(T-A.Time)/Span,U2=U*U,U3=U2*U;
            return (2*U3-3*U2+1)*A.Value+(U3-2*U2+U)*Span*A.Slope+
                (-2*U3+3*U2)*B.Value+(U3-U2)*Span*B.Slope;
        }
        return Keys[N-1].Value;
    }
    inline FVector Arc(const FVector& A,const FVector& B,const FVector& C,const FVector& D,float T)
    { const float V=1.f-T;return A*(V*V*V)+B*(3*V*V*T)+C*(3*V*T*T)+D*(T*T*T); }
    inline FVector GatherWrist(const FFireballHandPose& P,const FVector& Entry,float T)
    { return Arc(Entry,Entry+P.GatherDepart,P.GatherWrist+P.GatherApproach,P.GatherWrist,Curve(GatherKeys,T)); }
    inline FFireballArmMotion Gather(const FFireballHandPose& P,const FFireballArmMotion& Entry,const FQuat& Correction,float T)
    {
        FFireballArmMotion R;
        R.Wrist=GatherWrist(P,Entry.Wrist,T);
        R.Shoulder=FMath::Lerp(Entry.Shoulder,P.Shoulder,Ease(T/.84f));
        R.Pole=FMath::Lerp(Entry.Pole,P.ElbowPole,Ease((T-.025f)/.90f));
        R.Rotation=FQuat::Slerp(Entry.Rotation,P.PalmFrame(0)*Correction,Ease((T-.10f)/.80f));
        R.Fingers=Ease((T-.04f)/.72f);R.Layer=Ease(T/.16f);
        return R;
    }
    inline FFireballArmMotion Ready(const FFireballHandPose& P,const FFireballArmMotion& Entry,const FQuat& Correction,float T)
    {
        FFireballArmMotion R;const float U=Ease(T);
        R.Wrist=Arc(Entry.Wrist,Entry.Wrist+P.WindupDepart,P.WindupWrist+P.WindupApproach,P.WindupWrist,U);
        R.Shoulder=FMath::Lerp(Entry.Shoulder,P.Shoulder,Ease(T/.85f));
        R.Pole=FMath::Lerp(Entry.Pole,P.ElbowPole,Ease((T-.03f)/.92f));
        R.Palm=.48f;
        R.Rotation=FQuat::Slerp(Entry.Rotation,P.PalmFrame(R.Palm)*Correction,Ease((T-.06f)/.90f));
        R.Fingers=Ease((T-.05f)/.80f);R.Layer=Ease(T/.20f);
        return R;
    }
    inline float ReleasePalm(float ContactClock,bool Detached)
    { return FMath::Lerp(Detached?.48f:0.f,1.f,Ease((ContactClock-.10f)/.90f)); }
    inline FFireballArmMotion Release(const FFireballHandPose& P,const FQuat& Correction,float ContactClock,bool Detached)
    {
        FFireballArmMotion R;const float Push=Curve(PushKeys,ContactClock);
        R.Wrist=FMath::Lerp(Detached?P.WindupWrist:P.GatherWrist,P.ReleaseWrist,Push);
        const float U=FMath::Clamp(Push,0.f,1.f),ArcWeight=16*U*U*(1-U)*(1-U);
        R.Wrist+=FVector(0,-.8f,-1.4f)*ArcWeight;
        // The girdle and elbow support travel with the same anticipation/push
        // clock as the wrist. Most added reach comes from the complete arm.
        R.Shoulder=FMath::Lerp(P.Shoulder,P.ReleaseShoulder,Push);
        R.Pole=FMath::Lerp(P.ElbowPole,P.ReleaseElbowPole,Push);
        R.Palm=ReleasePalm(ContactClock,Detached);R.Rotation=P.PalmFrame(R.Palm)*Correction;
        return R;
    }
    inline FFireballArmMotion Recover(const FFireballHandPose& P,const FFireballArmMotion& From,
        const FFireballArmMotion& Current,float T)
    {
        FFireballArmMotion R=From;const float U=Curve(ReturnKeys,T);
        R.Wrist=Arc(From.Wrist,From.Wrist+P.RecoveryDepart,P.WithdrawWrist,Current.Wrist,U);
        R.Shoulder=FMath::Lerp(From.Shoulder,Current.Shoulder,Ease((T-.06f)/.94f));
        R.Pole=FMath::Lerp(From.Pole,Current.Pole,Ease((T-.10f)/.90f));
        R.Rotation=FQuat::Slerp(From.Rotation,Current.Rotation,Ease((T-.12f)/.88f));
        R.Layer=From.Layer*(1.f-Ease((T-.48f)/.52f));
        return R;
    }
    inline float FingerWeight(float Open,FName Digit,int32 Segment)
    {
        const float Delay=(Digit==TEXT("thumb")?0.f:Digit==TEXT("index")?.015f:
            Digit==TEXT("middle")?.025f:Digit==TEXT("ring")?.05f:.075f)+Segment*.015f;
        return FMath::Clamp((Open-Delay)/(1.f-Delay),0.f,1.f);
    }
}
