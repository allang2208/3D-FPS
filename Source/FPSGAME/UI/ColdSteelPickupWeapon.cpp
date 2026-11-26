#include "ColdSteelPickup.h"
#include "ColdSteelPickupStudio.h"
#include "FPSPerformanceMetrics.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSBodyGunAimTypes.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponPresentationMaterials.h"
#include "../Weapons/Super90SpeedloaderAssets.h"
#include "../Weapons/M24Attachments.h"
#include "PreviewScene.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Misc/ScopeExit.h"

// Reuse optional underbarrel visuals when the host weapon module provides them.
template<typename TRig> static void ApplyUnderbarrel(TRig* Rig,const FString& Variant)
{
    if constexpr(requires{Rig->SetGunsmithHandstop(Variant);})Rig->SetGunsmithHandstop(Variant);
}

bool AColdSteelPickup::BuildWeapon(const FColdSteelItem& Item,UGameInstance* Context)
{
    if(!Context)Context=GetGameInstance();
    return Context && AssembleWorldGun(Item,*Context,*Weapon,Body);
}

bool AColdSteelPickup::AssembleWorldGun(const FColdSteelItem& Item,UGameInstance& Context,UPoseableMeshComponent& GunMesh,UBoxComponent* DropBody,FTransform* OutMuzzleInMesh)
{
    const double Begin=FPlatformTime::Seconds();ON_SCOPE_EXIT { UE_LOG(LogTemp,Display,TEXT("DropTiming: model %.3f ms"),(FPlatformTime::Seconds()-Begin)*1000); };
    if(Item.Definition!=TEXT("ue_super90")&&Item.Definition!=TEXT("ue_m870")&&Item.Definition!=TEXT("ue_m4a1")&&Item.Definition!=TEXT("ue_hk416")&&Item.Definition!=TEXT("ue_akm")&&Item.Definition!=TEXT("ue_a762")&&Item.Definition!=TEXT("ue_lmg201")&&Item.Definition!=TEXT("ue_svd")&&Item.Definition!=TEXT("ue_svch")&&Item.Definition!=TEXT("ue_m24")&&Item.Definition!=TEXT("ue_saiga12k")&&Item.Definition!=TEXT("ue_pkm_lowpoly")&&Item.Definition!=TEXT("ue_m249")&&Item.Definition!=TEXT("ue_qbz191")&&Item.Definition!=TEXT("ue_ash12")&&Item.Definition!=TEXT("ue_m16a2")&&Item.Definition!=TEXT("ue_m1911")&&Item.Definition!=TEXT("ue_g18")&&Item.Definition!=TEXT("ue_pit_viper2011")&&(Item.Definition!=TEXT("ue_dan_wesson715")&&Item.Definition!=TEXT("ue_rsh12")))return false;
    auto* Pool=Context.GetSubsystem<UColdSteelPickupStudio>();
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Pickup_BuildWeapon);
    FFPSPerformanceScope BuildScope(&Context,TEXT("Pickup.BuildWeapon"),Pool->Key(Item));
    bool Created=false;auto* Rig=Pool->Acquire(Item.Definition,Created);if(!Rig)return false;
    if(Created){
        TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Pickup_InitializeVisuals);
        FFPSPerformanceScope VisualScope(&Context,TEXT("Pickup.InitializeVisuals"));
        Rig->ActiveInventoryWeaponDefinition=Item.Definition;Rig->bUseM4Infima=(Item.Definition==TEXT("ue_m4a1")||Item.Definition==TEXT("ue_hk416"));Rig->bUseQBZ191=Item.Definition==TEXT("ue_qbz191");Rig->bUseASH12=Item.Definition==TEXT("ue_ash12");Rig->bUseM16=Item.Definition==TEXT("ue_m16a2");Rig->bUseM1911=(Item.Definition==TEXT("ue_m1911")||Item.Definition==TEXT("ue_g18")||Item.Definition==TEXT("ue_pit_viper2011"));Rig->bUseDanWesson715=(Item.Definition==TEXT("ue_dan_wesson715")||Item.Definition==TEXT("ue_rsh12"));Rig->InitializeWeaponVisuals(true);
    }
    auto* Source=Rig->AKMViewmodel.Get();if(!Source||!Source->GetSkeletalMeshAsset())return false;
    Source->SetWorldTransform(FTransform::Identity);if(!Rig->SampleRSH12Presentation(Rig->IdleAnimation)){Source->PlayAnimation(Rig->IdleAnimation,false);Source->SetPosition(0,false);}Source->TickAnimation(0,false);Source->RefreshBoneTransforms();Source->UpdateComponentToWorld();
    const auto Parts=Context.GetSubsystem<UGunsmithSystem>()->Installed(Item);
    ApplyUnderbarrel(Rig,Parts.FindRef(Item.Definition==TEXT("ue_m24")?TEXT("body"):TEXT("underbarrel")));Rig->SetGunsmithBipod(Parts.FindRef(TEXT("bipod")));Rig->SetGunsmithOpticVariant(Parts.FindRef(TEXT("optic")));Rig->SetGunsmithMagazineAttachment(Parts.FindRef(TEXT("magazine")));Rig->SetGunsmithMuzzle(Parts.FindRef(TEXT("muzzle")));Rig->SetGunsmithStock(Parts.FindRef(TEXT("stock")));Rig->SetGunsmithRearGrip(Parts.FindRef(TEXT("reargrip")),Context.GetSubsystem<UGunsmithSystem>()->Weapon(Item.Definition),Parts.FindRef(TEXT("grip_body")));Rig->SetGunsmithTactical(Parts.FindRef(TEXT("tactical")),Parts.FindRef(TEXT("tactical_secondary")));Rig->UpdateFoldingSights(1);
    // Keep the complete visual recipe, including parts omitted by the old pickup path.
    Rig->SetSuper90Speedloader((Item.Definition==TEXT("ue_super90")||Item.Definition==TEXT("ue_m870"))
        &&Parts.FindRef(TEXT("reload_device"))==Super90SpeedloaderAssets::Id);
    if(Item.Definition==TEXT("ue_m24"))M24Attachments::SetBoltMaterial(Source,Parts.FindRef(TEXT("bolt")));
    Source->RefreshBoneTransforms();Source->UpdateChildTransforms();
    if(OutMuzzleInMesh)
    {
        *OutMuzzleInMesh=Rig->GetNativeMuzzleTransform().GetRelativeTransform(Source->GetComponentTransform());
        FTransform Sight;
        // The assembly studio has no gameplay eye. Resolve the native muzzle's
        // sign against the posed sights, never its helper camera's cached yaw.
        if(FPSBodyGunAim::SightFrame(*Source,Sight)&&FVector::DotProduct(
            OutMuzzleInMesh->GetRotation().GetForwardVector(),Sight.GetRotation().GetForwardVector())<0.)
            OutMuzzleInMesh->SetRotation((-OutMuzzleInMesh->GetRotation().GetForwardVector()).Rotation().Quaternion());
    }
    auto* Asset=Source->GetSkeletalMeshAsset();const auto* Render=Asset->GetResourceForRendering();if(!Render||Render->LODRenderData.IsEmpty())return false;
    // Copy the final evaluated component-space pose, including procedural belt
    // and carry-handle corrections. CopyPoseFromSkeletalComponent only copies
    // animation-local bones, so it drops those final layers on PKM / LMG201.
    const auto& SourcePose=Source->GetComponentSpaceTransforms();
    const auto& Reference=Asset->GetRefSkeleton();
    if(SourcePose.Num()!=Reference.GetNum())return false;
    GunMesh.SetSkinnedAssetAndUpdate(Asset);
    for(int32 Bone=0;Bone<SourcePose.Num();++Bone)
    {
        const int32 Parent=Reference.GetParentIndex(Bone);
        GunMesh.BoneSpaceTransforms[Bone]=Parent==INDEX_NONE?SourcePose[Bone]
            :SourcePose[Bone].GetRelativeTransform(SourcePose[Parent]);
        GunMesh.BoneSpaceTransforms[Bone].NormalizeRotation();
    }
    // The display disables ticking below. Finalize now, not on a later frame,
    // so the gun and its copied static attachments share exactly this pose.
    GunMesh.RefreshBoneTransforms();
    // Pistol presentation poses extend beyond their imported reference bounds.
    GunMesh.SetBoundsScale(Source->BoundsScale);
    for(int32 M=0;M<Source->GetNumMaterials();++M)GunMesh.SetMaterial(M,Source->GetMaterial(M));
    for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S){
        const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
        // Match inventory icons: named weapon handles are not first-person hands.
        const bool HandMaterial=Name.Contains(TEXT("hand"))&&!Name.Contains(TEXT("handguard"))&&!Name.Contains(TEXT("charginghandle"))&&!Name.Contains(TEXT("carryhandle"))&&!Name.EndsWith(TEXT("_handle"));
        const bool Visible=Source->IsMaterialSectionShown(M,L)&&!HandMaterial&&!WeaponPresentationMaterials::IsArmSection(Asset->GetMaterials()[M]);
        Source->ShowMaterialSection(M,S,Visible,L);GunMesh.ShowMaterialSection(M,S,Visible,L);
    }
    TArray<USceneComponent*> Attachments;
    Source->GetChildrenComponents(true,Attachments);
    if(DropBody)
    {
        const FVector Barrel=(Source->GetSocketLocation(TEXT("WPN_FrontSight"))-Source->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
        const FVector Up=Source->GetSocketLocation(TEXT("WPN_RearSight"))-Source->GetSocketLocation(TEXT("WPN_SOCKET_Magazine"));
        const FQuat Align=Barrel.IsNearlyZero()?FQuat::Identity:FRotationMatrix::MakeFromXZ(Barrel,Up).ToQuat().Inverse();
        FTransform Pose(Align);
        const FString CacheKey=Pool->Key(Item);FBox Bounds(ForceInit);
        if(const auto* Cached=Pool->Bounds.Find(CacheKey))Bounds=*Cached;
        else {
            const auto& LOD=Render->LODRenderData[0];
            if(auto* Weights=Source->GetSkinWeightBuffer(0)){TArray<FMatrix44f> Matrices;Source->GetCurrentRefToLocalMatrices(Matrices,0);
                for(const auto& Section:LOD.RenderSections)if(Source->IsMaterialSectionShown(Section.MaterialIndex,0))for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V)
                    Bounds+=Pose.TransformPosition(FVector(USkinnedMeshComponent::GetSkinnedVertexPosition(Source,V,LOD,*Weights,Matrices)));
            }
            for(auto* Child:Attachments)if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->IsVisible()&&Part->GetStaticMesh())Bounds+=Part->GetStaticMesh()->GetBoundingBox().TransformBy(Part->GetComponentTransform()*Pose);
            if(Bounds.IsValid){if(Pool->Bounds.Num()>=64)Pool->Bounds.Empty();Pool->Bounds.Add(CacheKey,Bounds);}
        }
        if(!Bounds.IsValid)return false;
        Pose.SetTranslation(-Bounds.GetCenter());
        GunMesh.SetRelativeTransform(Pose);
        DropBody->SetBoxExtent(Bounds.GetExtent().ComponentMax(FVector(2)));
        UE_LOG(LogTemp,Display,TEXT("WorldPickup: weapon=%s mesh=%s size=%s"),*Item.Definition,*Asset->GetPathName(),*Bounds.GetSize().ToString());
    }
    for(auto* Child:Attachments)if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->IsVisible()&&Part->GetStaticMesh()){
        auto* Owner=GunMesh.GetOwner();
        auto* Copy=NewObject<UStaticMeshComponent>(Owner);
        Owner->AddInstanceComponent(Copy);
        Copy->SetStaticMesh(Part->GetStaticMesh());
        if(DropBody)
        {
            Copy->SetupAttachment(DropBody);
            Copy->SetRelativeTransform(Part->GetComponentTransform()*GunMesh.GetRelativeTransform());
        }
        else
        {
            Copy->SetupAttachment(&GunMesh);
            Copy->SetRelativeTransform(Part->GetComponentTransform().GetRelativeTransform(Source->GetComponentTransform()));
        }
        Copy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        for(int32 M=0;M<Part->GetNumMaterials();++M)Copy->SetMaterial(M,Part->GetMaterial(M));Copy->RegisterComponent();
    }
    GunMesh.SetComponentTickEnabled(false);
    return true;
}
