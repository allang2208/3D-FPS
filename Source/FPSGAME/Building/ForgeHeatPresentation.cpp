#include "ForgeInteraction.h"
#include "Camera/CameraComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

void AForgeInteraction::EmitHotImpact(const FVector& Surface)
{
    LastHotImpact=FPlatformTime::Seconds();SparkOrigin=Surface;
    const FVector LocalHit=Blank->GetRelativeTransform().InverseTransformPosition(Surface);
    BlankMaterial->SetVectorParameterValue(TEXT("ImpactPoint"),FLinearColor(LocalHit.X,LocalHit.Y,LocalHit.Z));
    for(int32 I=0;I<SparkPool.Num();++I)
    {
        // Three bounded layers: quick bright chips, longer streaks and cooler oxide scale.
        auto& P=SparkPool[I];P.bScale=I%6==0;P.bBounced=false;P.Age=0;
        const bool bLongStreak=I%3==1;
        P.Lifetime=VisualRandom.FRandRange(P.bScale?.5f:(bLongStreak?.6f:.28f),P.bScale?.85f:(bLongStreak?.95f:.55f));
        const float Angle=VisualRandom.FRandRange(0.f,2.f*PI);
        const float Speed=VisualRandom.FRandRange(P.bScale?50.f:(bLongStreak?135.f:75.f),P.bScale?100.f:(bLongStreak?205.f:155.f));
        P.Position=Surface+FVector(VisualRandom.FRandRange(-.5f,.5f),VisualRandom.FRandRange(-.4f,.4f),.2);
        P.Velocity=FVector(FMath::Cos(Angle)*Speed,FMath::Sin(Angle)*Speed,VisualRandom.FRandRange(P.bScale?45.f:75.f,P.bScale?100.f:155.f));
        P.Size=VisualRandom.FRandRange(P.bScale?.7f:1.f,P.bScale?1.2f:1.5f);P.Roll=VisualRandom.FRandRange(-PI,PI);P.Spin=VisualRandom.FRandRange(-12.f,12.f);
        ScaleSparks->SetCustomDataValue(I,1,P.bScale?1.f:0.f,false);
    }
}

void AForgeInteraction::Sparks(float DeltaTime)
{
    bool bChanged=false;
    for(int32 I=0;I<SparkPool.Num();++I)
    {
        auto& P=SparkPool[I];if(P.Age>=P.Lifetime)continue;
        bChanged=true;P.Age+=DeltaTime;
        P.Velocity.Z-=440*DeltaTime;P.Velocity*=FMath::Exp(-1.1f*DeltaTime);P.Position+=P.Velocity*DeltaTime;
        // One damped bounce on the actual anvil footprint; never an infinite plane.
        if(P.Position.Z<91.1&&P.Velocity.Z<0&&FMath::Abs(P.Position.X-29)<31&&FMath::Abs(P.Position.Y-22)<12)
        {
            if(P.bBounced)P.Age=P.Lifetime;
            else {P.Position.Z=91.12;P.Velocity*=.5;P.Velocity.Z=FMath::Abs(P.Velocity.Z)*.45;P.bBounced=true;}
        }
        const float Life=FMath::Clamp(1-P.Age/P.Lifetime,0.f,1.f);
        const float End=FMath::Clamp(Life*5,0.f,1.f);
        P.Roll+=P.Spin*DeltaTime;
        const FQuat Facing=P.Velocity.Rotation().Quaternion()*FQuat(FVector::XAxisVector,P.Roll);
        const float Length=P.bScale?.45f:FMath::Clamp(float(P.Velocity.Size())*.022f,.5f,4.5f);
        const FVector Scale=P.bScale?FVector(Length/.6,.20/.075,.035/.075):FVector(Length/.6,1.05,1.05);
        ScaleSparks->UpdateInstanceTransform(I,FTransform(Facing,P.Position,Scale*P.Size*End),false,false,true);
        ScaleSparks->SetCustomDataValue(I,0,P.bScale?Life*Life:Life,false);
    }
    if(bChanged)ScaleSparks->MarkRenderStateDirty();
}

void AForgeInteraction::UpdateThermalEffects(float DeltaTime,float Heat,const FTransform& Work,double Now)
{
    const float HitAge=float(Now-LastHotImpact),Pulse=FMath::Exp(-HitAge*9.f);
    BlankMaterial->SetScalarParameterValue(TEXT("ImpactAge"),HitAge);
    VeilMaterial->SetScalarParameterValue(TEXT("Heat"),Heat);
    VeilMaterial->SetScalarParameterValue(TEXT("ImpactPulse"),Pulse);
    const FVector Center=Work.TransformPosition(FVector(0,0,8));
    FVector Along=Work.GetRotation().RotateVector(FVector::XAxisVector);
    if(((Along^FVector::UpVector)|(Camera->GetRelativeLocation()-Center))<0)Along*=-1;
    const FQuat VeilFacing=FRotationMatrix::MakeFromXY(Along,FVector::UpVector).ToQuat();
    HeatVeil->SetRelativeTransform(FTransform(VeilFacing,Center,FVector(.65,.22,1)));
    HeatVeil->SetVisibility(Heat>.05f&&QuenchImmersion<=0);
    HotLight->SetRelativeLocation(Work.TransformPosition(FVector(0,0,4)));
    HotLight->SetIntensity(Heat*25.f+Pulse*95.f);

    const float FinishAge=FinishAt>=0?float(Now-FinishAt):-1.f;
    const float SteamAge=QuenchContactAt>=0?float(Now-QuenchContactAt):-1.f;
    const bool bSteam=SteamAge>=0&&SteamAge<2.65f&&QuenchImmersion>0;
    const float SteamStrength=FMath::SmoothStep(0.f,.15f,QuenchImmersion)*FMath::Exp(-FMath::Max(0.f,SteamAge)*.42f);
    FumeMaterial->SetScalarParameterValue(TEXT("Steam"),QuenchContactAt>=0?1.f:0.f);
    FumeSpawnClock+=DeltaTime;
    const float Interval=bSteam?.035f:.16f;
    if(FumeSpawnClock>=Interval&&((Heat>.25f&&QuenchContactAt<0)||bSteam))
    {
        FumeSpawnClock=0; // Cosmetic: do not catch up a burst after a hitch.
        int32 Remaining=bSteam?(SteamAge<.28f?5:2):1;
        const int32 Limit=bSteam?FumePool.Num():FMath::Min(18,FumePool.Num());
        for(int32 I=0;I<Limit&&Remaining>0;++I)
        {
            auto& P=FumePool[I];if(P.Age<P.Lifetime)continue;
            --Remaining;P.bSteam=bSteam;
            P.Age=0;P.Lifetime=VisualRandom.FRandRange(bSteam?1.6f:1.15f,bSteam?2.4f:1.7f);P.Seed=VisualRandom.FRand();
            P.Opacity=bSteam?.72f*SteamStrength:.085f;P.Size=bSteam?VisualRandom.FRandRange(13.f,19.f):9.f;
            const float Angle=VisualRandom.FRandRange(0.f,2*PI),Radius=VisualRandom.FRandRange(0.f,4.f);
            P.Position=bSteam?SteamOrigin+FVector(FMath::Cos(Angle)*Radius,FMath::Sin(Angle)*Radius,1):Work.TransformPosition(FVector(VisualRandom.FRandRange(-19.f,25.f),0,2));
            if(!bSteam&&HitAge<.2f){P.Position=SparkOrigin+FVector(0,0,1);P.Opacity=.16f;}
            P.Velocity=FVector(VisualRandom.FRandRange(-5.f,5.f),VisualRandom.FRandRange(-4.f,4.f),bSteam?VisualRandom.FRandRange(24.f,39.f):9.f);
        }
    }
    bool bChanged=false;
    for(int32 I=0;I<FumePool.Num();++I)
    {
        auto& P=FumePool[I];if(P.Age>=P.Lifetime)continue;
        bChanged=true;P.Age+=DeltaTime;
        if(P.bSteam)
        {
            P.Velocity.Z+=6.f*DeltaTime;
            P.Position+=FVector(FMath::Sin(P.Seed*21+P.Age*3)*3,FMath::Cos(P.Seed*17+P.Age*2.6f)*3,0)*DeltaTime;
        }
        P.Position+=P.Velocity*DeltaTime;
        const float Age=FMath::Clamp(P.Age/P.Lifetime,0.f,1.f);
        const float EndFade=P.bSteam?1-FMath::SmoothStep(4.8f,5.65f,FinishAge):1;
        const float CameraFade=FMath::SmoothStep(8.f,25.f,float(FVector::Distance(Camera->GetRelativeLocation(),P.Position)));
        const float Alpha=FMath::SmoothStep(0.f,P.bSteam?.07f:.15f,Age)*(1-FMath::SmoothStep(.5f,1.f,Age))*P.Opacity*EndFade*CameraFade;
        const FVector Face=(Camera->GetRelativeLocation()-P.Position).GetSafeNormal();
        const FQuat Facing=FRotationMatrix::MakeFromZY(Face,FVector::UpVector).ToQuat();
        const float Size=P.Size*(1+Age*(P.bSteam?1.4f:.8f))/100.f;
        HeatFumes->UpdateInstanceTransform(I,FTransform(Facing,P.Position,FVector(Size,Size,1)),false,false,true);
        HeatFumes->SetCustomDataValue(I,0,Alpha,false);
        HeatFumes->SetCustomDataValue(I,1,P.Seed,false);
        HeatFumes->SetCustomDataValue(I,2,Age,false);
    }
    if(bChanged)HeatFumes->MarkRenderStateDirty();
}
