#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/TacticalDeviceComponent.h"
#include "../Weapons/TacticalDeviceVariants.h"

void UFPSPlayerBodyComponent::CaptureLaserPresentation()
{
    DisplayState.Lasers.Reset();
    if(DisplayState.Action==EFPSBodyAction::Dead||DisplayState.Motion==EFPSBodyMotion::Vault
        ||DisplayState.Motion==EFPSBodyMotion::Mantle)return;
    // Cached alongside the equipment manifest; at most two guns/two slots each.
    // Device ticks publish the final physical ray after the weapon pose settles.
    for(int32 Rig=0;Rig<LocalWeapons.Num()&&Rig<2;++Rig)
    {
        const auto& Weapon=LocalWeapons[Rig];
        if(Weapon.GunInstance.IsEmpty())continue;
        for(int32 Part=0;Part<Weapon.SourceTacticalDevices.Num()&&Part<64;++Part)
            if(const auto* Device=Weapon.SourceTacticalDevices[Part].Get())
            {
                FFPSBodyLaserSample Sample;
                if(!Device->ReadLaserSample(Sample))continue;
                Sample.RigIndex=Rig;Sample.PartIndex=Part;Sample.Schema=Weapon.MotionSchema;
                DisplayState.Lasers.Add(Sample);
                if(DisplayState.Lasers.Num()==4)return;
            }
    }
}

void UFPSPlayerBodyComponent::SanitizeLaserPresentation(FFPSBodyState& State) const
{
    if(State.Lasers.Num()>4){State.Lasers.Reset();return;}
    uint64 UsedParts[2]={0,0};
    State.Lasers.RemoveAll([&](const FFPSBodyLaserSample& Sample)
    {
        if(Sample.RigIndex>=2||!LocalWeapons.IsValidIndex(Sample.RigIndex)||Sample.PartIndex>=64
            ||Sample.End.ContainsNaN()||Sample.Normal.ContainsNaN()
            ||FVector::DistSquared(Sample.End,GetOwner()->GetActorLocation())>FMath::Square(8500.f)
            ||(Sample.bDot&&!FMath::IsNearlyEqual(Sample.Normal.SizeSquared(),1.,.02)))return true;
        const auto& Weapon=LocalWeapons[Sample.RigIndex];
        const FString& Instance=Weapon.AttachHand==1?State.OffhandInstance:State.WeaponInstance;
        if(Weapon.GunInstance.IsEmpty()||Weapon.GunInstance!=Instance||Weapon.MotionSchema!=Sample.Schema
            ||!Weapon.Parts.IsValidIndex(Sample.PartIndex)
            ||!TacticalDeviceVariants::IsLaser(Weapon.Parts[Sample.PartIndex].TacticalKind.ToString()))return true;
        const uint64 Bit=uint64(1)<<Sample.PartIndex;
        if(UsedParts[Sample.RigIndex]&Bit)return true;
        UsedParts[Sample.RigIndex]|=Bit;
        return false;
    });
}

bool UFPSPlayerBodyComponent::ResolveLaserSample(uint8 Rig,uint8 Part,uint32 Schema,FFPSBodyLaserSample& Out) const
{
    if(!Character.IsValid()||Character->IsLocallyControlled()||ServerClock()-DisplayState.PresentationSampledAt>.6f
        ||DisplayState.Action==EFPSBodyAction::Dead||DisplayState.Motion==EFPSBodyMotion::Vault
        ||DisplayState.Motion==EFPSBodyMotion::Mantle||!MotionBindings.IsValidIndex(Rig))return false;
    const auto& Weapon=MotionBindings[Rig].Definition;
    const FString& Instance=Weapon.AttachHand==1?DisplayState.OffhandInstance:DisplayState.WeaponInstance;
    if(Weapon.GunInstance!=Instance||Weapon.MotionSchema!=Schema)return false;
    for(const auto& Sample:DisplayState.Lasers)
        if(Sample.RigIndex==Rig&&Sample.PartIndex==Part&&Sample.Schema==Schema)
        {Out=Sample;return true;}
    return false;
}
