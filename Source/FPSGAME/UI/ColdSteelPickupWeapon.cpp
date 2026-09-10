#include "ColdSteelPickup.h"
#include "ColdSteelPickupStudio.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
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
    const double Begin=FPlatformTime::Seconds();ON_SCOPE_EXIT { UE_LOG(LogTemp,Display,TEXT("DropTiming: model %.3f ms"),(FPlatformTime::Seconds()-Begin)*1000); };
    if(Item.Definition!=TEXT("ue_m4a1")&&Item.Definition!=TEXT("ue_akm"))return false;
    if(!Context)Context=GetGameInstance();auto* Pool=Context->GetSubsystem<UColdSteelPickupStudio>();
    bool Created=false;auto* Rig=Pool->Acquire(Item.Definition,Created);if(!Rig)return false;
    if(Created){Rig->bUseM4Infima=Item.Definition==TEXT("ue_m4a1");Rig->InitializeWeaponVisuals();}
    auto* Source=Rig->AKMViewmodel.Get();if(!Source||!Source->GetSkeletalMeshAsset())return false;
    Source->SetWorldTransform(FTransform::Identity);Source->PlayAnimation(Rig->IdleAnimation,false);Source->SetPosition(0,false);Source->TickAnimation(0,false);Source->RefreshBoneTransforms();Source->UpdateComponentToWorld();
    const auto Parts=Context->GetSubsystem<UGunsmithSystem>()->Installed(Item);
    ApplyUnderbarrel(Rig,Parts.FindRef(TEXT("underbarrel")));Rig->SetGunsmithOptic(Parts.FindRef(TEXT("optic"))==TEXT("holographic"));Rig->SetGunsmithDrum(Parts.FindRef(TEXT("magazine"))==TEXT("large_drum"));Rig->SetGunsmithMuzzle(Parts.FindRef(TEXT("muzzle")));Rig->UpdateFoldingSights(1);
    Source->RefreshBoneTransforms();Source->UpdateChildTransforms();
    auto* Asset=Source->GetSkeletalMeshAsset();const auto* Render=Asset->GetResourceForRendering();if(!Render||Render->LODRenderData.IsEmpty())return false;
    Weapon->SetSkinnedAssetAndUpdate(Asset);Weapon->CopyPoseFromSkeletalComponent(Source);
    for(int32 M=0;M<Source->GetNumMaterials();++M)Weapon->SetMaterial(M,Source->GetMaterial(M));
    for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S){
        const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
        const bool Visible=Source->IsMaterialSectionShown(M,L)&&!Name.Contains(TEXT("manny"))&&!Name.Contains(TEXT("hand"))&&!Name.Contains(TEXT("glove"))&&!Name.Contains(TEXT("sleeve"))&&Name!=TEXT("skin");
        Source->ShowMaterialSection(M,S,Visible,L);Weapon->ShowMaterialSection(M,S,Visible,L);
    }
    const FVector Barrel=(Source->GetSocketLocation(TEXT("WPN_FrontSight"))-Source->GetSocketLocation(TEXT("WPN_RearSight"))).GetSafeNormal();
    const FVector Up=Source->GetSocketLocation(TEXT("WPN_RearSight"))-Source->GetSocketLocation(TEXT("WPN_SOCKET_Magazine"));
    const FQuat Align=Barrel.IsNearlyZero()?FQuat::Identity:FRotationMatrix::MakeFromXZ(Barrel,Up).ToQuat().Inverse();
    FTransform Pose(Align);const FString CacheKey=Pool->Key(Item);FBox Bounds(ForceInit);
    TArray<USceneComponent*> Attachments;Source->GetChildrenComponents(true,Attachments);
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
    if(!Bounds.IsValid)return false;Pose.SetTranslation(-Bounds.GetCenter());Weapon->SetRelativeTransform(Pose);
    int32 Attached=0;for(auto* Child:Attachments)if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->IsVisible()&&Part->GetStaticMesh()){
        auto* Copy=NewObject<UStaticMeshComponent>(this);AddInstanceComponent(Copy);Copy->SetStaticMesh(Part->GetStaticMesh());
        Copy->SetupAttachment(Body);Copy->SetRelativeTransform(Part->GetComponentTransform()*Pose);Copy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        for(int32 M=0;M<Part->GetNumMaterials();++M)Copy->SetMaterial(M,Part->GetMaterial(M));Copy->RegisterComponent();++Attached;
    }
    Body->SetBoxExtent(Bounds.GetExtent().ComponentMax(FVector(2)));Weapon->SetComponentTickEnabled(false);
    UE_LOG(LogTemp,Display,TEXT("WorldPickup: weapon=%s mesh=%s size=%s attachments=%d"),*Item.Definition,*Asset->GetPathName(),*Bounds.GetSize().ToString(),Attached);
    return true;
}
