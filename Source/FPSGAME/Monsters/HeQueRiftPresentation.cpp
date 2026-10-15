#include "HeQueMonster.h"
#include "HeQueRiftTiming.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"
#include "Engine/World.h"

namespace
{
constexpr float ImpactLife=.40f;
float Ramp(float A,float B,float T){return FMath::SmoothStep(A,B,T);}
float TensionAt(float T)
{
    static constexpr float Times[]={0,.35f,1.25f,1.55f,1.64f,1.96f,2.15f,2.24f,2.65f,3.7f,4.3f};
    static constexpr float Values[]={0,.2f,1,1,.42f,.98f,1.02f,.3f,.16f,0,0};
    for(int32 I=1;I<UE_ARRAY_COUNT(Times);++I)
        if(T<=Times[I])return FMath::Lerp(Values[I-1],Values[I],Ramp(Times[I-1],Times[I],T));
    return 0.f;
}
void Show(UStaticMeshComponent* Part,UMaterialInstanceDynamic* MID,const FVector& At,const FRotator& Rotation,
    const FVector& Scale,float Alpha,float Phase)
{
    const bool Visible=Alpha>.005f&&MID&&Part->GetStaticMesh();Part->SetVisibility(Visible);
    if(!Visible)return;
    Part->SetWorldLocationAndRotation(At,Rotation);Part->SetWorldScale3D(Scale);
    static const FName AlphaName(TEXT("PulseAlpha")),PhaseName(TEXT("PulsePhase"));
    MID->SetScalarParameterValue(AlphaName,Alpha);MID->SetScalarParameterValue(PhaseName,Phase);
}
}

void AHeQueMonster::OnRep_Rift()
{
    RefreshPoseTick();if(GetNetMode()==NM_DedicatedServer)return;
    if(Rift.Active)
    {
        PressureMembrane->SetStaticMesh(PressureMembraneMesh?PressureMembraneMesh.Get():PressureMesh.Get());
        if(!MembraneMID&&MembraneMaterial)MembraneMID=PressureMembrane->CreateDynamicMaterialInstance(0,MembraneMaterial);
        PressureIntake->SetStaticMesh(PressureMistMesh);
        if(!IntakeMID&&PressureMistMaterial)IntakeMID=PressureIntake->CreateDynamicMaterialInstance(0,PressureMistMaterial);
        auto Prepare=[](TArray<TObjectPtr<UStaticMeshComponent>>& Parts,TArray<TObjectPtr<UMaterialInstanceDynamic>>& MIDs,
            UStaticMesh* PartMesh,UMaterialInterface* Material)
        {
            MIDs.SetNum(2);
            for(int32 I=0;I<2;++I)
            {
                Parts[I]->SetStaticMesh(PartMesh);
                if(!MIDs[I]&&Material)MIDs[I]=Parts[I]->CreateDynamicMaterialInstance(0,Material);
            }
        };
        Prepare(PressureWaves,PressureMIDs,PressureMesh,PressureMaterial);
        Prepare(PressureMuzzles,MuzzleMIDs,PressureMistMesh,PressureMistMaterial);
        Prepare(PressureTrails,TrailMIDs,PressureMistMesh,PressureMistMaterial);
        Prepare(PressureImpacts,ImpactMIDs,PressureImpactMesh,PressureImpactMaterial);
        Prepare(PressureDust,DustMIDs,PressureImpactMesh,PressureDustMaterial);
    }
    if(PresentedRiftSerial!=Rift.Serial)
    {
        PresentedRiftSerial=Rift.Serial;RiftVoice->Stop();
        for(int32 I=0;I<2;++I)
        {
            ImpactSoundPlayed[I]=false;NextDustProbe[I]=0;DustTouchedAt[I]=-100.f;
            RiftImpactVoices[I]->Stop();
        }
        if(Rift.Active&&RiftSound&&RiftAge()<HeQueRiftTiming::End)
        {RiftVoice->SetSound(RiftSound);RiftVoice->AttenuationSettings=RiftAttenuation;RiftVoice->Play(RiftAge());}
    }
    if(!Rift.Active)
    {
        PressureMembrane->SetVisibility(false);PressureIntake->SetVisibility(false);
        for(const auto* Parts:{&PressureWaves,&PressureMuzzles,&PressureTrails,&PressureImpacts,&PressureDust})
            for(const auto& Part:*Parts)Part->SetVisibility(false);
    }
}

void AHeQueMonster::PresentRift(float Age)
{
    const float Tension=TensionAt(Age),Speed=FMath::Max(1.f,RiftSpeed);
    const FRotator Forward=Rift.Direction.Rotation(),Backward=(-Rift.Direction).Rotation();
    const FVector Mouth=RiftMouth();
    float Burst=0.f;
    for(float Release:{HeQueRiftTiming::First,HeQueRiftTiming::Second})
        if(Age>=Release)Burst+=Ramp(Release,Release+.035f,Age)*(1-Ramp(Release+.065f,Release+.17f,Age));
    Show(PressureMembrane,MembraneMID,Mouth,Forward,FVector(1.f+3.f*Burst,.42f-.16f*Tension,.68f+.15f*Tension),Tension,Age);
    const float Intake=FMath::Clamp(Tension,0.f,1.f)*(1.f-FMath::Clamp(Burst,0.f,1.f));
    Show(PressureIntake,IntakeMID,Mouth+Rift.Direction*80.f,Backward,FVector(.80f,.60f,.73f),Intake*.58f,Age);

    for(int32 I=0;I<2;++I)
    {
        const auto& Packet=I==0?Rift.PacketA:Rift.PacketB;
        const float FlightAge=Age-(I==0?HeQueRiftTiming::First:HeQueRiftTiming::Second);
        const float EndTravel=Packet.Stop>=0.f?Packet.Stop:RiftRange;
        const float EndAge=EndTravel/Speed;
        const FVector Origin=Packet.Released?Packet.Origin:
            (RiftReleasePoints.IsValidIndex(I)?GetMesh()->GetComponentTransform().TransformPosition(RiftReleasePoints[I])+Rift.Direction*12.f:Mouth);
        const FVector Position=Origin+Rift.Direction*FMath::Clamp(FlightAge*Speed,0.f,EndTravel);
        const bool Started=FlightAge>=0.f;
        const float ShotWeight=I==0?1.f:1.12f;
        const float Muzzle=Started?(1-Ramp(.025f,.22f,FlightAge))*ShotWeight:0.f;
        const float Spread=Ramp(0,.16f,FlightAge);
        Show(PressureMuzzles[I],MuzzleMIDs[I],Origin,Forward,FVector(.65f+Spread*.8f,.62f+Spread*.4f,.75f+Spread*.45f),Muzzle,FlightAge);
        const float WaveAlpha=Started?1-Ramp(EndAge,EndAge+.18f,FlightAge):0.f;
        const float Compression=Packet.Stop>=0.f?Ramp(EndAge,EndAge+.10f,FlightAge):0.f;
        Show(PressureWaves[I],PressureMIDs[I],Position,Forward,FVector(1.f-.85f*Compression,1,1),WaveAlpha,FlightAge+I*.37f);
        const float Trail=Started&&FlightAge<EndAge?Ramp(0,.07f,FlightAge)*.48f:0.f;
        const float TrailLength=FMath::Min(1.55f,FMath::Max(0.f,FlightAge)*Speed/100.f);
        Show(PressureTrails[I],TrailMIDs[I],Position-Rift.Direction*28.f,Backward,FVector(TrailLength,.66f,.66f),Trail,FlightAge);
        const float ImpactAge=FlightAge-EndAge;
        const float Impact=Packet.Stop>=0.f&&ImpactAge>=0.f?1-Ramp(.08f,ImpactLife,ImpactAge):0.f;
        const float Expansion=FMath::Lerp(.65f,1.55f,Ramp(0,ImpactLife,ImpactAge));
        Show(PressureImpacts[I],ImpactMIDs[I],Packet.ImpactPoint+Packet.ImpactNormal*6.f,Packet.ImpactNormal.Rotation(),
            FVector(.65f,Expansion,Expansion),Impact,ImpactAge);
        if(Impact>0.f&&!ImpactSoundPlayed[I]&&RiftImpactSound)
        {
            ImpactSoundPlayed[I]=true;
            auto* Voice=RiftImpactVoices[I].Get();Voice->SetWorldLocation(Packet.ImpactPoint);
            Voice->SetSound(RiftImpactSound);Voice->AttenuationSettings=RiftAttenuation;Voice->Play(FMath::Max(0.f,ImpactAge));
        }
        PresentPressureDust(I,Age,Position,Started&&FlightAge<EndAge&&Packet.Stop<0.f);
    }
}

void AHeQueMonster::PresentPressureDust(int32 Index,float Age,const FVector& Position,bool Flying)
{
    const auto& Packet=Index==0?Rift.PacketA:Rift.PacketB;
    const float Release=Index==0?HeQueRiftTiming::First:HeQueRiftTiming::Second;
    float Alpha=0.f,Phase=0.f,Radius=.65f;
    FVector At=DustPoint[Index],Normal=DustNormal[Index];
    if(Packet.Stop>=0.f)
    {
        Phase=Age-Release-Packet.Stop/FMath::Max(1.f,RiftSpeed);
        if(Packet.HitWorld&&Phase>=0.f)
        {
            At=Packet.ImpactPoint;Normal=Packet.ImpactNormal;
            Alpha=.8f*(1-Ramp(.08f,ImpactLife,Phase));Radius=FMath::Lerp(.65f,1.4f,Ramp(0,ImpactLife,Phase));
        }
    }
    else
    {
        if(Flying&&Age>=NextDustProbe[Index])
        {
            NextDustProbe[Index]=Age+.08f;
            auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
            if(Budget&&Budget->ReserveGeometryQueries(1)&&Budget->AllocateDetail(Position,1)>0)
            {
                FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
                FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQuePressureDust),true,this);FHitResult Hit;
                if(GetWorld()->LineTraceSingleByObjectType(Hit,Position,Position-FVector(0,0,135),Objects,Query)&&Hit.ImpactNormal.Z>.55f)
                {
                    DustTouchedAt[Index]=Age;At=DustPoint[Index]=Hit.ImpactPoint;Normal=DustNormal[Index]=Hit.ImpactNormal;
                }
            }
        }
        Phase=Age-DustTouchedAt[Index];Alpha=.55f*(1-Ramp(0,.20f,Phase));
    }
    Show(PressureDust[Index],DustMIDs[Index],At+Normal*8.f,Normal.Rotation(),FVector(.8f,Radius,Radius),Alpha,Phase);
}
