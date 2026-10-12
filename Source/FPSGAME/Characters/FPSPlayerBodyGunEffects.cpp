#include "FPSPlayerBodyComponent.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/FPSWeaponFXComponent.h"
#include "../Weapons/Super90WeaponAssets.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundConcurrency.h"
#include "Components/AudioComponent.h"

void UFPSPlayerBodyComponent::PresentSuper90Shot(bool bAiming,bool bSuppressed)
{
    if(!Character.IsValid()||Character->IsLocallyControlled()||!RemoteGunFX)return;
    for(const auto& Binding:MotionBindings)
    {
        auto* Weapon=Binding.Mesh.Get();
        if(!Weapon||Binding.Definition.Mesh.ToSoftObjectPath().ToString()!=Super90WeaponAssets::MeshPath)continue;
        if(!Weapon->IsVisible()||Weapon->bHiddenInGame||IsWorldWeaponStowed(Weapon))return;
        RemoteGunFX->SetWorldGunSuppressed(bSuppressed);
        RemoteGunFX->OnShot(bAiming);
        auto* Sound=bSuppressed&&RemoteSuppressedGunSound?RemoteSuppressedGunSound.Get():RemoteGunSound.Get();
        if(Sound)
        {
            if(!RemoteGunConcurrency)
            {
                RemoteGunConcurrency=NewObject<USoundConcurrency>(this);
                RemoteGunConcurrency->Concurrency.MaxCount=4;
                RemoteGunConcurrency->Concurrency.bLimitToOwner=true;
                RemoteGunConcurrency->Concurrency.ResolutionRule=EMaxConcurrentResolutionRule::StopOldest;
                RemoteGunConcurrency->Concurrency.VoiceStealReleaseTime=.02f;
            }
            // World audio attenuates with distance; it never uses the owner's 2D voice.
            auto* Audio=NewObject<UAudioComponent>(GetOwner());
            if(Audio)
            {
                FSoundAttenuationSettings Settings;Settings.bAttenuate=true;
                Settings.AttenuationShapeExtents=FVector(150.f);Settings.FalloffDistance=bSuppressed?3000.f:12000.f;
                Audio->bAutoDestroy=true;Audio->bIsUISound=false;Audio->SetSound(Sound);
                Audio->ConcurrencySet.Add(RemoteGunConcurrency);
                Audio->SetVolumeMultiplier(bSuppressed?.65f:1.f);Audio->RegisterComponent();
                Audio->bAllowSpatialization=true;Audio->SetWorldLocation(RemoteGunFX->ShotOrigin());
                Audio->AdjustAttenuation(Settings);Audio->Play();
            }
        }
        return;
    }
}
