#include "FPSGAMECharacter.h"
#include "Weapons/WeaponActionCameraComponent.h"
#include "Weapons/PistolDualWieldComponent.h"
#include "Weapons/DanWesson715WeaponAssets.h"
#include "Weapons/RSH12WeaponAssets.h"
#include "Weapons/LMG201WeaponAssets.h"
#include "Weapons/PKMLowpolyWeaponAssets.h"
#include "Weapons/Super90WeaponAssets.h"
#include "Weapons/Super90SpeedloaderAssets.h"
#include "Skills/FPSCastingMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/World.h"

namespace
{
using E=EReloadCameraContact;
void Cylinder(FWeaponReloadCameraTrack& Track,bool Empty,bool Single,int32 Count,float Close,bool RSH)
{
    using namespace DanWesson715WeaponAssets;
    const float Scale=Single?1.f:(Empty?EmptyReload/NormalReload:1.f);
    Track.Add(Open*Scale,E::CylinderOpen);
    if(Empty||(!Single)||RSH)
        Track.Add(Single?(RSH?(Empty?Eject:Open+.06f):EmptyCaseClear):Eject*Scale,E::Eject);
    if(Single)
    {
        for(int32 I=0;I<Count;++I)Track.Add(SingleSeatTime(I,Empty),E::Round);
    }
    else
    {
        Track.Add(Insert*Scale,E::Insert);Track.Add(Seat*Scale,E::Seat);
    }
    Track.Add(Close,E::CylinderClose);
}
void Magazine(FWeaponReloadCameraTrack& Track,TConstArrayView<float> Cues,bool Empty)
{
    if(Cues.Num()<3)return;
    Track.Add(Cues[0],E::MagazineOut);Track.Add(Cues[1],E::Insert);Track.Add(Cues[2],E::Seat);
    if(Empty&&Cues.Num()>3)
    {
        if(Cues.Num()>4)Track.Add(Cues[3],E::Pull);
        Track.Add(Cues.Last(),E::Release);
    }
}
}

void AFPSGAMECharacter::BuildReloadCameraTracks(FWeaponReloadCameraTracks& Tracks) const
{
    Tracks.Reset();
    if(!IsLocallyControlled()||bGunsmithInspection||IsTraversing())return;
    if(bInventoryWeaponReady&&IsReloading()&&ActiveActionAnimation&&!HasOffhandPistol())
    {
        auto& Track=Tracks.AddDefaulted_GetRef();
        Track.Time=ReloadSourceTime(WeaponStateElapsed);Track.End=ReloadSourceTime(WeaponStateDuration);
        Track.Begin=bReloadCycleOnly?ReloadSourceTime(ReloadResumeElapsed):0.f;
        Track.FamilyScale=IsPistolWeapon()?WeaponReloadCamera::PistolScale:
            (IsSuper90Weapon()||bUseASH12||IsRSH12Weapon()||PKMLowpolyWeaponAssets::Matches(AKMViewmodel)||LMG201WeaponAssets::Matches(AKMViewmodel))
                ?WeaponReloadCamera::HeavyScale:WeaponReloadCamera::RifleScale;
        if(IsRSH12Weapon())Track.FamilyScale=WeaponReloadCamera::RifleScale;
        if(IsSuper90Weapon())
        {
            using namespace Super90WeaponAssets;
            if(bSuper90SpeedReload)
            {
                if(Super90ReloadCount>0)
                {
                    Track.Add(Super90SpeedloaderAssets::Dock,E::Insert);
                    // One continuous tube stroke: do not stack seven cartridge pulses.
                    Track.Add(Super90SpeedloaderAssets::LastContact(Super90ReloadCount),E::Seat);
                }
                if(bPendingEmptyReload)Track.Add(Super90SpeedloaderAssets::Release(Super90ReloadCount),E::Release);
            }
            else
            {
                // Shell loops are timed before the unused source loops are skipped.
                // The closure contact is translated onto this continuous feed clock.
                Track.Time=WeaponStateElapsed*Super90ReloadRate;
                Track.End=WeaponStateDuration*Super90ReloadRate;Track.Begin=0.f;
                for(int32 I=0;I<Super90ReloadCount;++I)Track.Add(Insert+I*LoopStep,E::Round);
                if(bPendingEmptyReload)Track.Add(bReloadCycleOnly?CycleBoltReady:
                    Super90ReloadTail+BoltRelease-TailBegin,E::Release);
            }
        }
        else if(bUseDanWesson715)
        {
            // Single RSH uses the shared 715 mechanism. Only the dual RSH has
            // its separate authored early case-drop contact below.
            Cylinder(Track,bPendingEmptyReload,bRevolverSingleReload,RevolverReloadCount,ReloadStages.Ready,false);
        }
        else if(HasLMG201ClothBox()||PKMLowpolyWeaponAssets::Matches(AKMViewmodel))
        {
            const auto& C=MechanicalCueTimes;
            const bool Cloth=HasLMG201ClothBox();
            const int32 Box=Cloth||bPendingEmptyReload?1:2;
            if(C.Num()>Box+3)
            {
                Track.Add(C[0],E::CoverOpen);
                if(!bPendingEmptyReload)Track.Add(Cloth?LMG201WeaponAssets::ClothTrayPull:C[1],E::Belt);
                Track.Add(C[Box],E::MagazineOut);Track.Add(C[Box+1],E::Seat);
                Track.Add(C[Box+2],E::Belt);Track.Add(C[Box+3],E::CoverClose);
                if(!Cloth&&bPendingEmptyReload&&C.Num()>=9)
                {Track.Add(C[6],E::Pull);Track.Add(C[8],E::Release);}
            }
        }
        else
        {
            TArray<float,TInlineAllocator<12>> Contacts;
            for(const float Cue:MechanicalCueTimes)
                Contacts.Add(bUsingM4Infima?Cue:ReloadSourceTime(Cue));
            Magazine(Track,Contacts,bPendingEmptyReload);
        }
    }
    if(!HasOffhandPistol()||!DualPistols)return;
    for(int32 Side=IsDualWieldingPistols()?0:1;Side<2;++Side)
    {
        const auto& H=DualPistols->Hand(Side);if(!H.Reloading||!H.Action)continue;
        auto& Track=Tracks.AddDefaulted_GetRef();Track.Hand=Side;
        // The hand controller advances after UpdateCamera. Sample its absolute
        // action clock now rather than introducing one frame of camera latency.
        const float ActionTime=DualPistols->SampleActionTime(Side);
        Track.Time=ActionTime/FMath::Max(.001f,H.Action->GetPlayLength())*H.SourceLength;
        Track.End=H.SourceLength;
        const bool Empty=H.ReloadStart==0||H.ReloadSpeedloader;
        const bool RSH=H.Item.Definition==RSH12WeaponAssets::Definition;
        Track.FamilyScale=RSH?WeaponReloadCamera::RifleScale:WeaponReloadCamera::PistolScale;
        Track.Begin=H.ReloadCameraBegin;
        if(H.Revolver)
        {
            const auto Stages=WeaponReloadStages::ForWeapon(H.Item.Definition,Empty,false,!H.ReloadSpeedloader,H.ReloadCount);
            Cylinder(Track,Empty,!H.ReloadSpeedloader,H.ReloadCount,Stages.Ready,RSH);
        }
        else
        {
            // The actual dual-pistol source table used by AdvanceReload.
            const float Contacts[]={.3167f,1.05f,1.0667f,1.6f};
            Magazine(Track,Contacts,Empty);
        }
    }
}
