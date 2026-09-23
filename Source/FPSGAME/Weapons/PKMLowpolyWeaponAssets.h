#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Rendering/SkeletalMeshRenderData.h"

namespace PKMLowpolyWeaponAssets
{
inline constexpr const TCHAR* Definition = TEXT("ue_pkm_lowpoly");
inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular.SK_PKM_Manny_Modular");
inline constexpr const TCHAR* WetMaterialsPath = TEXT("/Game/Weapons/PKMLowpoly20260922/Finish20/DA_PKM_WetMaterials.DA_PKM_WetMaterials");
// PKM keeps its own fire one-shot. It replaces the AKM voice the family fallback
// used to borrow; source and level record: SourceAssets/PKMLowpolyAudio20260922.
inline constexpr const TCHAR* FireSoundPath = TEXT("/Game/Weapons/PKMLowpoly20260922/Audio/S_PKM_Fire.S_PKM_Fire");
inline FString ReloadSoundPath(const TCHAR* Contact)
{
    return FString::Printf(TEXT("/Game/Weapons/PKMLowpoly20260922/ReloadAudio22/S_PKM_%s.S_PKM_%s"),Contact,Contact);
}
inline FString ChargeSoundPath(const TCHAR* Contact)
{
    return FString::Printf(TEXT("/Game/Weapons/PKMLowpoly20260922/ChargeAudio35/S_PKM_%s.S_PKM_%s"),Contact,Contact);
}
inline bool Matches(const USkeletalMeshComponent* Mesh)
{
    return Mesh && Mesh->GetSkeletalMeshAsset() && Mesh->GetSkeletalMeshAsset()->GetPathName().StartsWith(TEXT("/Game/Weapons/PKMLowpoly20260922/"));
}
inline FString AnimationPath(const TCHAR* Clip)
{
    return FString::Printf(TEXT("/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_%s.A_PKM_%s"), Clip, Clip);
}
// Reload16 bypasses the spent-belt handling in the empty branch. Every
// mechanical event after the handoff shares the same shortened source clock.
inline float ReloadEventTime(float OriginalSeconds, bool Empty)
{
    return OriginalSeconds - (Empty && OriginalSeconds >= 2.3f ? .9f : 0.f);
}
inline UStaticMeshComponent* FindBipod(AActor* Owner)
{
    if (!Owner) return nullptr;
    TInlineComponentArray<UStaticMeshComponent*> Parts(Owner);
    for (auto* Part : Parts)
        if (Part->ComponentHasTag(TEXT("PKMBipod"))) return Part;
    return nullptr;
}
inline void RemoveBipod(AActor* Owner)
{
    if (auto* Part=FindBipod(Owner)) Part->DestroyComponent();
}
void ConfigureBipod(AActor* Owner, USkeletalMeshComponent* Weapon, bool Enabled);
// Animated props move at their authored size. Hidden parked duplicates never
// participate in item framing or appear during the action-to-idle handoff.
inline void SetSections(USkeletalMeshComponent* Mesh, bool Reloading, bool Empty, float SourceTime, int32 Rounds)
{
    if (!Matches(Mesh)) return;
    const auto* Asset=Mesh->GetSkeletalMeshAsset();
    const auto* Render=Asset->GetResourceForRendering();
    if (!Render) return;
    for (int32 L=0; L<Render->LODRenderData.Num(); ++L)
        for (int32 S=0; S<Render->LODRenderData[L].RenderSections.Num(); ++S)
        {
            const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString();
            bool Visible=true;
            if (Name.Contains(TEXT("__New"))) Visible=Reloading && SourceTime>=ReloadEventTime(3.55f,Empty);
            else if (Name.Contains(TEXT("__OldBox"))) Visible=!Reloading || SourceTime<ReloadEventTime(3.2f,Empty);
            else if (Name.Contains(TEXT("__OldBelt"))) Visible=Rounds>0 && (!Reloading || (!Empty && SourceTime<ReloadEventTime(3.2f,Empty)));
            else continue;
            if (Mesh->IsMaterialSectionShown(M,L)!=Visible) Mesh->ShowMaterialSection(M,S,Visible,L);
        }
}
}
