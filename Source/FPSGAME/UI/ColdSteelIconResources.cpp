#include "ColdSteelWeaponIcons.h"
#include "ColdSteelMeleePreview.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/MeleeRuneVisual.h"
#include "../Weapons/FrostSwordRunes.h"
#include "../Weapons/A762Attachments.h"
#include "../Weapons/PKMAttachments.h"
#include "../Weapons/PSO1AttachmentAssets.h"
#include "../Weapons/PKMBipodComponent.h"
#include "../Weapons/M16Attachments.h"
#include "../Weapons/M16WeaponAssets.h"
#include "../Weapons/QBZ191Attachments.h"
#include "../Weapons/ASH12WeaponAssets.h"
#include "../Weapons/SVDWeaponAssets.h"
#include "../Weapons/SVDAttachments.h"
#include "../Weapons/M1911WeaponAssets.h"
#include "../Weapons/DanWesson715WeaponAssets.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"

void UColdSteelWeaponIcons::ResetPreparation()
{
    if(ResourceLoad){ResourceLoad->CancelHandle();ResourceLoad.Reset();}
    RequiredResources.Reset();PrepareStep=0;AttachmentStep=0;BoundsSection=0;BoundsVertex=0;bBoundsStarted=false;
    WorkingBounds=FPreparedBounds();BoundsBoneMatrices.Reset();
}

void UColdSteelWeaponIcons::BeginResourceLoad(const FColdSteelItem& Item)
{
    FFPSPerformanceScope Scope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.ResourceRequest"));
    ResetPreparation();
    TArray<FSoftObjectPath> Paths;
    const auto Add=[&](const FString& Path,bool Required=false)
    {
        if(Path.IsEmpty())return;
        const FSoftObjectPath Ref(Path.Contains(TEXT("."))?Path:Path+TEXT(".")+FPaths::GetCleanFilename(Path));
        if(Required)RequiredResources.AddUnique(Ref);
        // Optional family fittings may not exist for a particular weapon. Never synchronously load to probe them.
        if(Required||Ref.ResolveObject()||FPackageName::DoesPackageExist(Ref.GetLongPackageName()))Paths.AddUnique(Ref);
    };
    Add(TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment"),true);
    const FString& D=Item.Definition;
    if(ColdSteelMeleePreview::Supports(Item))
    {
        if(ColdSteelModularSword::Supports(Item))
        {
            const FGunsmithParts Factory;
            ColdSteelModularSword::GatherVisualResources(Item,RequiredResources,bCatalogExport?&Factory:nullptr);
            for(const auto& Ref:RequiredResources)Paths.AddUnique(Ref);
        }
        else Add(ColdSteelMeleePreview::MeshPath(Item),true);
        const FString Rune=bCatalogExport?FString():ColdSteelMeleeRune::Selected(Item);
        const bool Frost=D==ColdSteelFrostRunes::Definition;
        const FString Visual=Frost&&(Rune.IsEmpty()||Rune==TEXT("false"))?TEXT("erosion_rune"):Rune;
        if(Visual==TEXT("golden_glow_rune")&&D==TEXT("ue_rune_sword"))
        {
            Add(TEXT("/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/MI_AzureRunesword_NativeGold"));
            Add(TEXT("/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/T_RuneSword_NativeMask"));
            Add(TEXT("/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/T_RuneSword_GuardNativeMask"));
        }
        else if(!Visual.IsEmpty()&&Visual!=TEXT("false"))
        {
            const bool Wild=D==TEXT("ue_highland_claymore")&&Visual==TEXT("wild_rune");
            const bool Spirit=Frost&&Visual==ColdSteelFrostRunes::SpiritBurst;
            Add(Wild?TEXT("/Game/Weapons/HighlandClaymore20260922/WildRune/M_SilverRuneSurface_HighlandWild"):
                Spirit?TEXT("/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit"):
                TEXT("/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2"));
            Add(Wild?FString(TEXT("/Game/Weapons/HighlandClaymore20260922/WildRune/T_Mask_wild_rune")):
                TEXT("/Game/Weapons/MeleeRunes20260915/SurfaceV2/T_Mask_")+(Spirit?FString(TEXT("erosion_rune")):Visual==TEXT("golden_glow_rune")?FString(TEXT("resonance_rune")):Visual));
        }
    }
    else
    {
        if(D==TEXT("ue_svd")){Add(SVDWeaponAssets::MeshPath,true);Add(SVDWeaponAssets::AnimationPath(TEXT("idle")),true);}
        else if(D==TEXT("ue_a762")){Add(A762WeaponAssets::MeshPath,true);Add(A762WeaponAssets::AnimationPath(TEXT("idle")),true);for(int32 I=0;I<2;++I)Add(A762WeaponAssets::SightPath(I));}
        else if(D==TEXT("ue_pkm_lowpoly")){Add(PKMLowpolyWeaponAssets::MeshPath,true);Add(PKMLowpolyWeaponAssets::AnimationPath(TEXT("idle")),true);}
        else if(D==TEXT("ue_m16a2")){Add(M16WeaponAssets::MeshPath,true);Add(M16WeaponAssets::AnimationPath(TEXT("idle")),true);}
        else if(D==TEXT("ue_ash12")){Add(ASH12WeaponAssets::MeshPath,true);Add(ASH12WeaponAssets::AnimationPath(TEXT("idle")),true);}
        else if(D==TEXT("ue_m1911")){Add(TEXT("/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny"),true);Add(M1911WeaponAssets::AnimationPath(TEXT("idle")),true);}
        else if(D==TEXT("ue_dan_wesson715")){Add(DanWesson715WeaponAssets::MeshPath,true);Add(DanWesson715WeaponAssets::AnimationPath(TEXT("idle")),true);}
        else if(D==TEXT("ue_qbz191"))
        {
            Add(TEXT("/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny"),true);
            Add(TEXT("/Game/Weapons/QBZ191/Refined20260913/Animations/base/A_QBZ191_idle"),true);
            Add(TEXT("/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_RearSight"));Add(TEXT("/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_FrontSight"));
        }
        else if(D==TEXT("ue_m4a1"))
        {
            Add(TEXT("/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416"),true);Add(TEXT("/Game/Weapons/M4ContactImpactFinal/A_AKM_idle"),true);
            Add(TEXT("/Game/Weapons/M4FoldingSights/SM_M4_RearSight"));Add(TEXT("/Game/Weapons/M4FoldingSights/SM_M4_FrontSight"));
        }
        else
        {
            Add(TEXT("/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative"),true);
            Add(TEXT("/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_idle"),true);
        }
        const auto Parts=bCatalogExport?FGunsmithParts():GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Installed(Item);
        const FString Family=D==TEXT("ue_akm")?TEXT("AKM"):D==TEXT("ue_qbz191")?TEXT("QBZ191"):D==TEXT("ue_ash12")?TEXT("ASH12"):TEXT("M4");
        for(const auto& Part:Parts)
        {
            FString Key=Part.Value;
            if(Key.IsEmpty()||Key==TEXT("false")||Key==TEXT("factory"))continue;
            if(Part.Key==TEXT("optic")&&Key==PSO1AttachmentAssets::Variant)
            {
                if(PSO1AttachmentAssets::Supports(D))Add(PSO1AttachmentAssets::MeshPath(D));
                continue;
            }
            if(Key==TEXT("angled_foregrip"))Key=TEXT("angled");
            else if(Key==TEXT("vertical_foregrip"))Key=TEXT("vertical");
            else if(Key==TEXT("tactical_vertical_foregrip"))Key=TEXT("tactical_vertical");
            else if(Key==TEXT("canted_foregrip"))Key=TEXT("canted");
            else if(Key==TEXT("prism_handstop"))Key=TEXT("prism");
            if(D==TEXT("ue_svd"))
            {
                if(Part.Key==TEXT("muzzle")&&Key==TEXT("true"))Key=TEXT("suppressor");
                if(Part.Key!=TEXT("barrel"))Add(SVDAttachments::MeshPath(Key));
                if(Part.Key==TEXT("optic"))Add(SVDAttachments::MeshPath(TEXT("optic_bridge")));
                if(Key==TEXT("lpvo_1_6x"))Add(SVDAttachments::MeshPath(TEXT("lpvo_ring")));
                continue;
            }
            if(D==TEXT("ue_a762"))Add(A762Attachments::MeshPath(Key));
            else if(D==TEXT("ue_pkm_lowpoly"))
            {
                if(Key==TEXT("pkm_bipod"))
                {Add(PKMBipodAssets::Base);Add(PKMBipodAssets::LegA);Add(PKMBipodAssets::LegB);}
                else Add(PKMAttachments::MeshPath(Key));
            }
            else if(D==TEXT("ue_m16a2"))Add(M16Attachments::MeshPath(Key));
            else if(D==TEXT("ue_qbz191"))Add(QBZ191Attachments::MeshPath(Key));
            else if(D==TEXT("ue_ash12"))Add(ASH12WeaponAssets::OpticMeshPath(Key));
            else if(D==TEXT("ue_m1911"))Add(M1911WeaponAssets::AttachmentPath(Key));
            if(D==TEXT("ue_m4a1")||D==TEXT("ue_akm"))
            {
                if(Part.Key==TEXT("optic"))
                {
                    const FString Root=D==TEXT("ue_akm")?TEXT("/Game/Weapons/AKMIntegration/SovietFab/OpticSteel/"):TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/");
                    const FString Name=Key==TEXT("lpvo_1_6x")?TEXT("SM_LPVO1to6X"):Key==TEXT("prism_scope_2x")?TEXT("SM_PrismScope2X"):Key==TEXT("panoramic_red_dot")?TEXT("SM_PanoramicRedDot"):D==TEXT("ue_akm")?TEXT("SM_AKM_optic"):TEXT("SM_M4_Holographic");
                    Add(Root+Name);if(Key==TEXT("lpvo_1_6x"))Add(Root+TEXT("SM_LPVORing"));
                    if(D==TEXT("ue_akm"))Add(TEXT("/Game/Weapons/AKMIntegration/SovietFab/Optics/SM_AKM_Mount_")+Key);
                }
                if(Part.Key==TEXT("underbarrel")||Part.Key==TEXT("muzzle"))
                {
                    if(Key==TEXT("angled"))Add(TEXT("/Game/Weapons/ResonanceGrip20260913/MeshyIntegration/")+Family+TEXT("/SM_ResonanceGrip"));
                    if(D==TEXT("ue_akm"))Add(TEXT("/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_")+Key+(Key==TEXT("canted")?TEXT("_CompactMount"):TEXT("")));
                    else
                    {
                        Add(TEXT("/Game/Weapons/M4MuzzlesV1/SM_M4_")+Key);
                        if(Key==TEXT("prism"))Add(TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PrismHandstop"));
                        if(Key==TEXT("vertical"))Add(TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_VerticalForegrip"));
                        if(Key==TEXT("canted"))Add(TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_CantedForegrip"));
                    }
                }
                if(Part.Key==TEXT("stock"))
                {
                    if(Key==TEXT("skeleton"))Add(D==TEXT("ue_akm")?TEXT("/Game/Weapons/ReferenceStock5080/AKM/SM_SkeletonStock"):TEXT("/Game/Weapons/ReferenceStock5080/SM_SkeletonStock"));
                    if(Key==TEXT("qr_performance"))Add(TEXT("/Game/Weapons/QRPerformanceStock/Meshy20260913/")+Family+TEXT("/SM_PerformanceStock"));
                    if(Key==TEXT("core_stock"))Add(TEXT("/Game/Weapons/CoreStock20260914/Meshy0914005605/")+Family+TEXT("/SM_CoreStock"));
                    if(Key==TEXT("tactical_telescopic"))Add(TEXT("/Game/Weapons/TacticalTelescopicStock20260914/")+Family+TEXT("/SM_TacticalTelescopicStock"));
                }
                if(Part.Key==TEXT("reargrip"))
                {
                    Add(TEXT("/Game/Weapons/StableAntiSlipRearGrip/Selected91727/")+Family+TEXT("/SM_StableAntiSlipRearGrip"));
                    Add(TEXT("/Game/Weapons/RearGripFinish20260913/")+Family+TEXT("/balanced/SM_BalancedRearGrip"));
                    Add(TEXT("/Game/Weapons/RearGripFinish20260913/")+Family+TEXT("/phantom/SM_PhantomRearGrip"));
                    if(D==TEXT("ue_m4a1"))Add(TEXT("/Game/Weapons/RearGripFinish20260913/M4/balanced/Seam20260914/SM_BalancedRearGrip"));
                }
            }
            if(Key==TEXT("tactical_vertical"))Add(TEXT("/Game/Weapons/TacticalVerticalForegrip20260919/")+Family+TEXT("/SM_TacticalVerticalForegrip"));
            if(Key==TEXT("tactical_suppressor"))Add(D==TEXT("ue_ash12")?FString(ASH12WeaponAssets::TacticalSuppressorMeshPath):TacticalSuppressorAssets::MeshPath(*Family));
            if(Key==TEXT("ext_mag"))
            {
                if(D==TEXT("ue_akm"))Add(TEXT("/Game/Weapons/ExtMagContinuity20260919/SM_ExtMag_AKM40_Continuous"));
                if(D==TEXT("ue_m4a1"))Add(TEXT("/Game/Weapons/M4GridUnified20260919/SM_M4_ExtMag40_Grid"));
                if(D==TEXT("ue_qbz191"))Add(TEXT("/Game/Weapons/ExtMagRemodel20260919/SM_ExtMag_QBZ40_Remodel"));
                if(D==TEXT("ue_ash12"))Add(ASH12WeaponAssets::ExtendedMagazineMeshPath);
            }
            if(Key==TEXT("large_drum"))
            {
                if(D==TEXT("ue_akm"))Add(TEXT("/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_drum"));
                if(D==TEXT("ue_m4a1"))Add(TEXT("/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_LargeDrum"));
            }
            if(Key==TEXT("lpvo_1_6x"))
            {
                if(D==TEXT("ue_a762"))Add(A762Attachments::MeshPath(TEXT("lpvo_ring")));
                else if(D==TEXT("ue_pkm_lowpoly"))Add(PKMAttachments::MeshPath(TEXT("lpvo_ring")));
                else if(D==TEXT("ue_m16a2"))Add(M16Attachments::MeshPath(TEXT("lpvo_ring")));
                else if(D==TEXT("ue_qbz191"))Add(QBZ191Attachments::MeshPath(TEXT("lpvo_ring")));
                else if(D==TEXT("ue_ash12"))Add(ASH12WeaponAssets::OpticMeshPath(TEXT("lpvo_ring")));
            }
        }
    }
    // Keep the handle until capture/pickup preparation finishes, so GC cannot unload prefetched resources.
    ResourceLoad=bCatalogExport?UAssetManager::GetStreamableManager().RequestSyncLoad(Paths):
        UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate(),FStreamableManager::DefaultAsyncLoadPriority);
    SetWaitState(TEXT("AsyncResources"));
}
