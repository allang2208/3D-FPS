#include "../FPSGAMECharacter.h"
#include "Super90SpeedloaderAssets.h"
#include "Super90WeaponAssets.h"
#include "TubeShotgunAssets.h"
#include "Super90LoaderAudioReference.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Sound/SoundBase.h"

namespace Super90WeaponAssets
{
void SetLooseShellVisible(USkeletalMeshComponent* Mesh,bool Show)
{
    const auto* Asset=Mesh?Mesh->GetSkeletalMeshAsset():nullptr;
    const auto* Render=Asset?Asset->GetResourceForRendering():nullptr;
    if(!Render)return;
    for(int32 L=0;L<Render->LODRenderData.Num();++L)
        for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
        {
            const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            // M870 carries the same WPN_Shell cartridge under its imported slot
            // name; the loader tube reuses that bone, so it must hide there too.
            if(Asset->GetMaterials().IsValidIndex(M)
                &&(Asset->GetMaterials()[M].MaterialSlotName==LooseShellMaterial||Asset->GetMaterials()[M].MaterialSlotName==TEXT("M_S90_12gauge"))
                &&Mesh->IsMaterialSectionShown(M,L)!=Show)
                Mesh->ShowMaterialSection(M,S,Show,L);
        }
}
}

void AFPSGAMECharacter::InitializeSuper90Speedloader()
{
    Super90LoaderNormal.Reset();Super90LoaderEmpty.Reset();Super90LoaderSounds.Reset();Super90LoaderPropMesh=nullptr;
    if(!IsTubeShotgunWeapon())return;
    using namespace Super90SpeedloaderAssets;
    // Index 0 is the standalone chamber cycle (M870: its own pump cycle).
    const bool M870=IsM870Weapon();
    Super90LoaderNormal.SetNum(Capacity+1);Super90LoaderEmpty.SetNum(Capacity+1);
    for(int32 Count=0;Count<=Capacity;++Count)
    {
        if(Count)Super90LoaderNormal[Count]=LoadObject<UAnimSequence>(nullptr,*Animation(Count,false,M870));
        Super90LoaderEmpty[Count]=LoadObject<UAnimSequence>(nullptr,*Animation(Count,true,M870));
    }
    Super90LoaderPropMesh=LoadObject<USkeletalMesh>(nullptr,Props);
    // Load once with the equipped weapon, never at a mechanical contact/tick.
    for(const auto& Cue:Super90LoaderAudioReference::Cues)
        Super90LoaderSounds.Add(LoadObject<USoundBase>(nullptr,Cue.Asset));
}

void AFPSGAMECharacter::SetSuper90Speedloader(bool bEnabled)
{
    bEnabled=bEnabled&&bInventoryWeaponReady&&IsTubeShotgunWeapon();
    if(!bEnabled)
    {
        if(Super90LoaderGuide){Super90LoaderGuide->DestroyComponent();Super90LoaderGuide=nullptr;}
        if(Super90LoaderProps){Super90LoaderProps->DestroyComponent();Super90LoaderProps=nullptr;}
        return;
    }
    // Each tube shotgun has its own port adapter; a swap between two guns that
    // both carry the loader must not keep the previous gun's guide mesh.
    auto* GuideMesh=LoadObject<UStaticMesh>(nullptr,Super90SpeedloaderAssets::GuideFor(IsM870Weapon()));
    if(!GuideMesh)return;
    if(!Super90LoaderGuide)
    {
        auto* GuideMesh=LoadObject<UStaticMesh>(nullptr,Super90SpeedloaderAssets::Guide);
        if(!GuideMesh)return;
        Super90LoaderGuide=NewObject<UStaticMeshComponent>(this,TEXT("Super90LoaderGuide"));
        AddInstanceComponent(Super90LoaderGuide);Super90LoaderGuide->SetupAttachment(AKMViewmodel,TEXT("WPN_root"));
        Super90LoaderGuide->SetCollisionEnabled(ECollisionEnabled::NoCollision);Super90LoaderGuide->SetCastShadow(false);
        Super90LoaderGuide->bReceivesDecals=false;Super90LoaderGuide->SetStaticMesh(GuideMesh);
        Super90LoaderGuide->SetOnlyOwnerSee(AKMViewmodel->bOnlyOwnerSee);
        Super90LoaderGuide->SetFirstPersonPrimitiveType(AKMViewmodel->FirstPersonPrimitiveType);
        Super90LoaderGuide->RegisterComponent();
    }
    const auto& Ref=AKMViewmodel->GetSkeletalMeshAsset()->GetRefSkeleton();FTransform Root=FTransform::Identity;
    for(int32 Bone=Ref.FindBoneIndex(TEXT("WPN_root"));Bone!=INDEX_NONE;Bone=Ref.GetParentIndex(Bone))Root=Root*Ref.GetRefBonePose()[Bone];
    Super90LoaderGuide->SetRelativeTransform(FTransform::Identity.GetRelativeTransform(Root));
    Super90LoaderGuide->SetVisibility(true);
    // Presentation-only actors load only the installed guide. Transient reload
    // props never enter workbench/icon bounds and follow the complete V7 pose.
    if(!Super90LoaderProps&&Super90LoaderPropMesh)
    {
        Super90LoaderProps=NewObject<USkeletalMeshComponent>(this,TEXT("Super90LoaderProps"));
        Super90LoaderProps->ComponentTags.Add(TEXT("WeaponReloadProp"));
        AddInstanceComponent(Super90LoaderProps);Super90LoaderProps->SetupAttachment(AKMViewmodel);
        Super90LoaderProps->SetSkeletalMeshAsset(Super90LoaderPropMesh);
        Super90LoaderProps->SetCollisionEnabled(ECollisionEnabled::NoCollision);Super90LoaderProps->SetCastShadow(false);
        Super90LoaderProps->bReceivesDecals=false;Super90LoaderProps->SetOnlyOwnerSee(true);
        Super90LoaderProps->SetFirstPersonPrimitiveType(AKMViewmodel->FirstPersonPrimitiveType);
        // Like the modular arms, these rigid props follow the viewmodel pose.
        // Their imported bind bounds describe a parked tube, not its reload
        // path; culling must use the visible viewmodel's bounds instead.
        Super90LoaderProps->bUseAttachParentBound=true;
        Super90LoaderProps->SetLeaderPoseComponent(AKMViewmodel);Super90LoaderProps->RegisterComponent();
        Super90LoaderProps->SetVisibility(false);
    }
}

void AFPSGAMECharacter::UpdateSuper90SpeedloaderVisual()
{
    if(!IsTubeShotgunWeapon())return;
    const float Time=Super90ReloadSourceTime(WeaponStateElapsed);
    // Native feed clips need the cartridge; idle and loader clips retain its
    // off-screen parking pose. Keep it hidden while blending out of idle too.
    const bool bNativeFeed=IsReloading()&&!bSuper90SpeedReload&&Super90ReloadCount>0
        &&WeaponStateElapsed>=ActionBlendIn&&Time<Super90WeaponAssets::TailBegin;
    Super90WeaponAssets::SetLooseShellVisible(AKMViewmodel,bNativeFeed);
    if(!Super90LoaderProps)return;
    const bool Show=bSuper90SpeedReload&&Super90ReloadCount>0&&IsReloading()&&AKMViewmodel->IsVisible()
        &&Time>=Super90SpeedloaderAssets::PropsVisibleBegin
        &&Time<Super90SpeedloaderAssets::PropsVisibleEnd(Super90ReloadCount);
    if(Super90LoaderProps->IsVisible()!=Show)Super90LoaderProps->SetVisibility(Show);
}

void AFPSGAMECharacter::ClearSuper90SpeedloaderAction()
{
    if(Super90LoaderProps)Super90LoaderProps->SetVisibility(false);
    if(IsTubeShotgunWeapon())Super90WeaponAssets::SetLooseShellVisible(AKMViewmodel,false);
    bSuper90SpeedReload=false;
}

void AFPSGAMECharacter::SetSuper90LoaderCues()
{
    MechanicalCueTimes.Reset();MechanicalCueSounds.Reset();
    int32 Index=0;
    for(const auto& Cue:Super90LoaderAudioReference::Cues)
    {
        // Retain loader handling cues; the old overhand bolt pair is retired.
        const bool bBolt=Cue.CycleFrame>=0.f;
        if(Super90ReloadCount>0&&!bBolt)
        {
            MechanicalCueTimes.Add(Cue.Frame/60.f);
            MechanicalCueSounds.Add(Super90LoaderSounds.IsValidIndex(Index)?Super90LoaderSounds[Index].Get():nullptr);
        }
        ++Index;
    }
    const bool M870=IsM870Weapon();
    const float Ready=Super90SpeedloaderAssets::Release(Super90ReloadCount,M870);
    if(bPendingEmptyReload&&M870)
    {
        // Pump pull and forward stroke of the appended (or standalone) cycle.
        const float Start=Super90ReloadCount>0?M870LoaderTiming::CycleStart:0.f;
        MechanicalCueTimes.Append({Start+.12f,Start+M870WeaponAssets::PumpPush});
        MechanicalCueSounds.Append({ChargePullSound,ChargeReleaseSound});
    }
    else if(bPendingEmptyReload)
    {
        MechanicalCueTimes.Add(Ready);
        MechanicalCueSounds.Add(ChargeReleaseSound);
    }
    ReloadStages={Super90ReloadTail,Super90SpeedloaderAssets::FeedContact(Super90ReloadTail,FMath::Max(0,Super90ReloadCount-1)),Ready};
    NextMechanicalCue=0;
    const float SourceTime=Super90ReloadSourceTime(WeaponStateElapsed);
    while(NextMechanicalCue<MechanicalCueTimes.Num()&&MechanicalCueTimes[NextMechanicalCue]<SourceTime)
        ++NextMechanicalCue;
}
