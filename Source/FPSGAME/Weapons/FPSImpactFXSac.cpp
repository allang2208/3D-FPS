#include "FPSImpactFXSubsystem.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

namespace SacPresentation
{
    static TAutoConsoleVariable<float> AudioGain(TEXT("fps.Bellow.AudioGain"),1.25f,
        TEXT("Bellow sac presentation gain; default 1.25 (+1.94 dB), source peak -2.5 dBFS."));
}
float UFPSImpactFXSubsystem::SacAudioGain()
{ return FMath::Clamp(SacPresentation::AudioGain.GetValueOnGameThread(),0.f,2.f); }

void UFPSImpactFXSubsystem::PlaySacImpact(const FVector& Position, bool bBurst)
{
    if (!bReady || SacVoices.IsEmpty()) return;
    const double Now=GetWorld()->GetTimeSeconds();
    int32 Slot=INDEX_NONE;
    for (int32 I=0; I<SacVoices.Num(); ++I)
        if (!SacVoices[I]->IsPlaying()) { Slot=I; break; }
    if (Slot==INDEX_NONE && bBurst)
    {
        Slot=0;
        for (int32 I=1; I<SacVoices.Num(); ++I)
            if (SacVoiceUntil[I]<SacVoiceUntil[Slot]) Slot=I;
    }
    if (Slot==INDEX_NONE) return;
    auto* Voice=SacVoices[Slot].Get();
    Voice->Stop(); Voice->SetSound(bBurst?SacRuptureSound.Get():SacContactSound.Get());
    Voice->SetWorldLocation(Position);
    Voice->SetVolumeMultiplier(SacAudioGain()*(bBurst?1.f:.78f));
    Voice->SetPitchMultiplier(bBurst?1.f:FMath::FRandRange(.97f,1.03f));
    Voice->Play(); SacVoiceUntil[Slot]=Now+(bBurst?1.1:.2);
}

void UFPSImpactFXSubsystem::SpawnSacRupture(const FVector& Origin,const FVector& SurfaceNormal,
    float Radius,UCameraComponent* ViewCamera)
{
    if (!bReady || !IsValid(ViewCamera)) return;
    const float Distance=FVector::Dist(Origin,ViewCamera->GetComponentLocation());
    if (Distance>3500.f) return;
    Camera=ViewCamera;
    const FVector Normal=SurfaceNormal.GetSafeNormal(UE_SMALL_NUMBER,FVector::UpVector);
    FVector Tangent,Bitangent; Normal.FindBestAxisVectors(Tangent,Bitangent);
    const double Now=GetWorld()->GetTimeSeconds();
    auto Allocate=[&](int32 Start,int32 Count)->FParticle*
    {
        if (ActiveParticles>=MaxActiveParticles) return nullptr;
        for (int32 I=Start; I<Start+Count; ++I)
            if (Particles[I].Life<=0.f)
            { ++ActiveParticles; Particles[I]=FParticle(); Particles[I].Born=Now; return &Particles[I]; }
        return nullptr;
    };
    constexpr int32 WaveStart=SparkSlots+DustSlots+ChipSlots+BloodMistSlots+BloodDropSlots;
    // Both rings use exactly the gameplay radius; no extra damage-looking halo.
    for (int32 Kind=0; Kind<2; ++Kind)
    {
        if (!ParticleMaterials[5+Kind]) continue;
        auto* P=Allocate(WaveStart+Kind*GroundWaveSlots,Kind?PressureWaveSlots:GroundWaveSlots);
        if (!P) continue;
        P->Life=Kind?.24f:.30f; P->Position=Origin+Normal*(Kind?8.f:2.f);
        P->Rotation=FRotationMatrix::MakeFromZ(Normal).Rotator();
        P->Size=FVector(Radius*2.f,Radius*2.f,100.f);
        P->Color=FLinearColor(.62f,.52f,.47f); P->Opacity=Kind?.90f:.76f; P->Variation=-1.1f;
    }
    const bool Near=Distance<1600.f;
    for (int32 Group=1; Group<=4; ++Group)
    {
        if (Group==2) continue; // Existing membrane meshes supply the large fragments.
        const int32 Start=Group==1?SparkSlots:Group==3?SparkSlots+DustSlots+ChipSlots:WaveStart-BloodDropSlots;
        const int32 Capacity=Group==1?DustSlots:Group==3?BloodMistSlots:BloodDropSlots;
        const int32 Count=Group==1?(Near?5:2):Group==3?(Near?4:2):(Near?18:6);
        for (int32 I=0; I<Count; ++I)
        {
            auto* P=Allocate(Start,Capacity); if (!P) break;
            const float Angle=I*2.f*PI/Count+FMath::FRandRange(-.2f,.2f);
            const FVector Out=Tangent*FMath::Cos(Angle)+Bitangent*FMath::Sin(Angle);
            P->Position=Origin+Normal*8.f+Out*FMath::FRandRange(1.f,9.f);
            P->Color=Group==1?FLinearColor(.40f,.36f,.32f):FLinearColor(.32f,.16f,.13f);
            P->Variation=FMath::FRand(); P->Rotation.Roll=FMath::FRandRange(-180.f,180.f);
            P->bHasLandingPlane=true; P->LandingPoint=Origin-Normal*6.f; P->LandingNormal=Normal;
            if (Group==4)
            {
                P->Life=FMath::FRandRange(.40f,.85f); P->Opacity=.90f;
                P->Velocity=Out*FMath::FRandRange(160.f,430.f)+Normal*FMath::FRandRange(110.f,240.f);
                P->Gravity=-680.f; P->Size=FVector(FMath::FRandRange(1.2f,2.8f),FMath::FRandRange(4.f,9.f),1.f);
            }
            else
            {
                P->Life=Group==1?.62f:.72f; P->Opacity=Group==1?.48f:.62f;
                P->Velocity=Out*(Group==1?230.f:150.f)+Normal*(Group==1?28.f:95.f);
                P->Gravity=25.f; P->Size=FVector(Group==1?45.f:34.f);
            }
        }
    }
}
