#include "FPSPlayerBodyComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyPoses.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Dom/JsonObject.h"

namespace FPSBodyEquipment
{
/** Applies owner-visibility flags only where they differ from the current value.
 *
 *  SetOnlyOwnerSee/SetOwnerNoSee/SetCastShadow each mark the primitive's render
 *  state dirty, which on a skeletal body or a viewmodel part costs a render-state
 *  recreate plus shadow-scene re-registration. The body component re-asserts the
 *  same flags on every camera update, so re-applying them unconditionally turned a
 *  one-off setup into continuous render-thread churn.
 */
void ApplyOwnerVisibilityFlags(UPrimitiveComponent* Mesh,bool bOnlyOwnerSee,bool bOwnerNoSee)
{
    if(!Mesh)return;
    // No short-circuit: each flag is independent and each change must be seen.
    const bool bOnlyChanged=Mesh->bOnlyOwnerSee!=bOnlyOwnerSee;
    const bool bOwnerChanged=Mesh->bOwnerNoSee!=bOwnerNoSee;
    if(bOnlyChanged)Mesh->SetOnlyOwnerSee(bOnlyOwnerSee);
    if(bOwnerChanged)Mesh->SetOwnerNoSee(bOwnerNoSee);
    // Count changed fields in this instrumented path, not calls or render-state recreates.
    if(bOnlyChanged)UFPSPerformanceMetricsSubsystem::CountVisibilityFlagChange();
    if(bOwnerChanged)UFPSPerformanceMetricsSubsystem::CountVisibilityFlagChange();
}
void ApplyShadowFlags(UPrimitiveComponent* Mesh,bool bCastShadow)
{
    if(!Mesh)return;
    const bool bCastChanged=Mesh->CastShadow!=bCastShadow;
    const bool bHiddenChanged=Mesh->bCastHiddenShadow!=bCastShadow;
    if(bCastChanged)Mesh->SetCastShadow(bCastShadow);
    if(bHiddenChanged)Mesh->SetCastHiddenShadow(bCastShadow);
    if(bCastChanged)UFPSPerformanceMetricsSubsystem::CountVisibilityFlagChange();
    if(bHiddenChanged)UFPSPerformanceMetricsSubsystem::CountVisibilityFlagChange();
}
static UMaterialInterface* PersistentMaterial(UMaterialInterface* Material)
{
    while(auto* Dynamic=Cast<UMaterialInstanceDynamic>(Material))Material=Dynamic->Parent;
    return Material;
}
static bool IsArmMaterial(const FString& Slot)
{
    const FString Name=Slot.ToLower();
    // "Handguard" is a weapon part, not a first-person hand section.
    return Name.Contains(TEXT("manny"))||Name==TEXT("hand")||Name==TEXT("hands")
        ||Name.EndsWith(TEXT("_hand"))||Name.EndsWith(TEXT("_hands"))
        ||Name.Contains(TEXT("glove"))||Name.Contains(TEXT("sleeve"))||Name==TEXT("skin");
}
static void WorldVisibility(UPrimitiveComponent* Mesh)
{
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetGenerateOverlapEvents(false);
    const auto* Body=Mesh->GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    ApplyOwnerVisibilityFlags(Mesh,/*bOnlyOwnerSee=*/false,/*bOwnerNoSee=*/!Body||!Body->IsThirdPersonViewEnabled());
    // Final shadow/visibility policy is applied after the equipment's hand is registered.
}
}

FFPSBodyWeapon UFPSPlayerBodyComponent::CaptureWeapon(USkeletalMeshComponent* Source,UAnimSequence* Idle,FName Grip) const
{
    FFPSBodyWeapon Result;if(!Source||!Source->GetSkeletalMeshAsset())return Result;
    auto* Asset=Source->GetSkeletalMeshAsset();Result.Mesh=Asset;Result.HoldClip=Idle;Result.GripBone=Grip;
    for(int32 I=0;I<Asset->GetMaterials().Num();++I)
    {
        Result.Materials.Add(FPSBodyEquipment::PersistentMaterial(Source->GetMaterial(I)));
        if(FPSBodyEquipment::IsArmMaterial(Asset->GetMaterials()[I].MaterialSlotName.ToString())||!Source->IsMaterialSectionShown(I,0))Result.HiddenMaterials.Add(I);
    }
    TArray<USceneComponent*> Children;Source->GetChildrenComponents(true,Children);
    for(auto* Child:Children)if(auto* Part=Cast<UStaticMeshComponent>(Child);Part&&Part->IsVisible()&&!Part->bHiddenInGame&&Part->GetStaticMesh())
    {
        FFPSBodyAttachment Entry;Entry.Mesh=Part->GetStaticMesh();
        Entry.RelativeTransform=Part->GetRelativeTransform();
        USceneComponent* Branch=Part;
        while(Branch->GetAttachParent()&&Branch->GetAttachParent()!=Source)
        {Branch=Branch->GetAttachParent();Entry.RelativeTransform=Entry.RelativeTransform*Branch->GetRelativeTransform();}
        Entry.Socket=Branch->GetAttachSocketName();
        for(int32 I=0;I<Part->GetNumMaterials();++I)Entry.Materials.Add(FPSBodyEquipment::PersistentMaterial(Part->GetMaterial(I)));
        Result.Parts.Add(MoveTemp(Entry));
    }
    return Result;
}
void UFPSPlayerBodyComponent::CaptureEquipment()
{
    UFPSPerformanceMetricsSubsystem::CountEquipmentCapture();
    const auto* Pawn=Character.Get();TArray<FFPSBodyWeapon> Weapons;
    if(Pawn->IsDualWieldingPistols())
    {
        for(int32 I=0;I<2;++I)
        {
            const auto& Hand=Pawn->DualPistols->Hand(I);
            // Both imported pistol rigs use the right-hand grip; the world instance attaches to the chosen body hand.
            Weapons.Add(CaptureWeapon(Hand.Mesh,Hand.Clips.FindRef(TEXT("idle")),TEXT("hand_r")));
        }
    }
    else if(Pawn->HasInventoryWeapon())Weapons.Add(CaptureWeapon(Pawn->AKMViewmodel,Pawn->IdleAnimation,TEXT("hand_r")));
    else if(const auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsEquipped())
        Weapons.Add(CaptureWeapon(Sword->Viewmodel,Sword->Animations.FindRef(TEXT("Idle")),TEXT("hand_r")));
    else if(const auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool&&Tool->IsEquipped())
    {
        if(Tool->bUsesArms)Weapons.Add(CaptureWeapon(Tool->Viewmodel,Tool->Motions.FindRef(TEXT("Idle")),TEXT("hand_r")));
        else if(Tool->ToolMesh&&Tool->ToolMesh->GetStaticMesh())
        {
            FFPSBodyWeapon Entry;Entry.StaticMesh=Tool->ToolMesh->GetStaticMesh();
            // Preserve the tool's authored mount and scale. Convert its camera
            // basis into Manny's +Y facing basis, relative to the hand bind frame.
            FQuat HandBasis=FQuat::Identity;
            if(const auto* Body=GetBodyMesh();Body&&Body->GetSkeletalMeshAsset())
            {
                const auto& Ref=Body->GetSkeletalMeshAsset()->GetRefSkeleton();
                FTransform Hand=FTransform::Identity;
                for(int32 Bone=Ref.FindBoneIndex(TEXT("hand_r"));Bone!=INDEX_NONE;Bone=Ref.GetParentIndex(Bone))
                    Hand=Hand*Ref.GetRefBonePose()[Bone];
                HandBasis=Hand.GetRotation();
            }
            Entry.StaticGrip=FTransform(HandBasis.Inverse()*FRotator(0,90,0).Quaternion()*Tool->ToolMesh->GetRelativeRotation().Quaternion(),
                FVector::ZeroVector,Tool->ToolMesh->GetRelativeScale3D());
            for(int32 I=0;I<Tool->ToolMesh->GetNumMaterials();++I)
                Entry.Materials.Add(FPSBodyEquipment::PersistentMaterial(Tool->ToolMesh->GetMaterial(I)));
            Weapons.Add(MoveTemp(Entry));
        }
    }
    FString Key=DisplayState.Weapon.ToString();
    for(const auto& W:Weapons)
    {
        Key+=TEXT("|")+W.Mesh.ToSoftObjectPath().ToString()+TEXT("|")+W.HoldClip.ToSoftObjectPath().ToString();
        Key+=TEXT("|")+W.StaticMesh.ToSoftObjectPath().ToString()+TEXT("|")+W.StaticGrip.ToString();
        for(const int32 Hidden:W.HiddenMaterials)Key+=FString::Printf(TEXT("#%d"),Hidden);
        for(const auto& Material:W.Materials)Key+=TEXT("|")+Material.ToSoftObjectPath().ToString();
        for(const auto& Part:W.Parts)
        {
            Key+=TEXT("|")+Part.Mesh.ToSoftObjectPath().ToString()+TEXT("|")+Part.RelativeTransform.ToString();
            for(const auto& Material:Part.Materials)Key+=TEXT("|")+Material.ToSoftObjectPath().ToString();
        }
    }
    if(EquipmentKey!=Key)
    {
        EquipmentKey=Key;LocalWeapons=Weapons;
        if(GetOwner()->HasAuthority())ReplicatedWeapons=Weapons;
        if(GetNetMode()!=NM_DedicatedServer)RebuildWeapons(Weapons);
        bOutfitDirty=true;
    }
    if(bOutfitDirty&&Pawn->GetGameInstance())if(auto* Profile=Pawn->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    {
        LocalOutfit.Reset();
        for(const auto& Item:Profile->Items())if(Item.Place==1&&Item.Cell!=6&&Item.Cell!=8&&Item.Cell!=9&&Item.Cell!=11)
        {FFPSBodyOutfitSlot Entry;Entry.Slot=Item.Cell;Entry.Definition=FName(*Item.Definition);LocalOutfit.Add(Entry);}
        LocalOutfit.Sort([](const auto& A,const auto& B){return A.Slot<B.Slot;});
        if(GetOwner()->HasAuthority())ReplicatedOutfit=LocalOutfit;
        if(GetNetMode()!=NM_DedicatedServer)ApplyOutfit(LocalOutfit);
        bOutfitDirty=false;
    }
}
void UFPSPlayerBodyComponent::RebuildWeapons(const TArray<FFPSBodyWeapon>& Weapons)
{
    auto* Body=GetBodyMesh();if(!Body)return;
    if(FPSPlayerBodyWorldBodySuppressed())return;
    UFPSPerformanceMetricsSubsystem::CountEquipmentRebuild();
    for(auto Part:WorldParts)if(Part)Part->DestroyComponent();WorldParts.Reset();
    for(auto Weapon:WorldWeapons)if(Weapon)Weapon->DestroyComponent();WorldWeapons.Reset();
    WorldEquipmentHands.Reset();
    if(BodyAnimation)BodyAnimation->bHasLeftGrip=false;
    for(int32 Index=0;Index<Weapons.Num();++Index)
    {
        const auto& Definition=Weapons[Index];
        if(auto* Static=Definition.StaticMesh.LoadSynchronous())
        {
            auto* Part=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
            GetOwner()->AddInstanceComponent(Part);Part->SetStaticMesh(Static);
            Part->SetupAttachment(Body,Index==1?TEXT("hand_l"):TEXT("hand_r"));Part->SetRelativeTransform(Definition.StaticGrip);
            WorldEquipmentHands.Add(Part,static_cast<uint8>(Index));
            FPSBodyEquipment::WorldVisibility(Part);
            for(int32 I=0;I<Definition.Materials.Num();++I)if(auto* Material=Definition.Materials[I].LoadSynchronous())Part->SetMaterial(I,Material);
            Part->RegisterComponent();WorldParts.Add(Part);continue;
        }
        auto* Asset=Definition.Mesh.LoadSynchronous();if(!Asset)continue;
        auto* Weapon=NewObject<USkeletalMeshComponent>(GetOwner(),NAME_None,RF_Transient);
        GetOwner()->AddInstanceComponent(Weapon);Weapon->SetSkeletalMeshAsset(Asset);
        Weapon->SetupAttachment(Body,Index==1?TEXT("hand_l"):TEXT("hand_r"));
        WorldEquipmentHands.Add(Weapon,static_cast<uint8>(Index));
        FPSBodyEquipment::WorldVisibility(Weapon);Weapon->RegisterComponent();
        Weapon->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        if(auto* Hold=Definition.HoldClip.LoadSynchronous())
        {Weapon->PlayAnimation(Hold,false);Weapon->SetPosition(0.f,false);Weapon->SetPlayRate(0.f);Weapon->TickAnimation(0.f,false);}
        Weapon->RefreshBoneTransforms();
        FTransform Grip=Weapon->GetSocketTransform(Definition.GripBone,RTS_Component);
        // Imported viewmodel hand bones can carry scale 100. Their component-space
        // locations are already centimetres; invert only the rigid grip transform.
        Grip.SetScale3D(FVector::OneVector);
        Weapon->SetRelativeTransform(Grip.Inverse());
        for(int32 I=0;I<Definition.Materials.Num();++I)if(auto* Material=Definition.Materials[I].LoadSynchronous())Weapon->SetMaterial(I,Material);
        if(const auto* Render=Asset->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 Material=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                Weapon->ShowMaterialSection(Material,S,!Definition.HiddenMaterials.Contains(Material),L);
            }
        Weapon->SetComponentTickEnabled(false);WorldWeapons.Add(Weapon);
        if(Index==0&&Weapons.Num()==1&&BodyAnimation&&Weapon->DoesSocketExist(TEXT("hand_l")))
        {
            FTransform LeftGrip=Weapon->GetSocketTransform(TEXT("hand_l"),RTS_Component);
            LeftGrip.SetScale3D(FVector::OneVector);
            BodyAnimation->LeftGripFromRight=LeftGrip.GetRelativeTransform(Grip);
            BodyAnimation->bHasLeftGrip=true;
        }
        for(const auto& DefinitionPart:Definition.Parts)if(auto* AssetPart=DefinitionPart.Mesh.LoadSynchronous())
        {
            auto* Part=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
            GetOwner()->AddInstanceComponent(Part);Part->SetStaticMesh(AssetPart);
            Part->SetupAttachment(Weapon,DefinitionPart.Socket);Part->SetRelativeTransform(DefinitionPart.RelativeTransform);
            WorldEquipmentHands.Add(Part,static_cast<uint8>(Index));
            FPSBodyEquipment::WorldVisibility(Part);
            for(int32 I=0;I<DefinitionPart.Materials.Num();++I)if(auto* Material=DefinitionPart.Materials[I].LoadSynchronous())Part->SetMaterial(I,Material);
            Part->RegisterComponent();WorldParts.Add(Part);
        }
    }
    UpdateWorldWeaponPresentation();
}

bool UFPSPlayerBodyComponent::IsWorldWeaponStowed(UPrimitiveComponent* Mesh) const
{
    const float Now=ServerClock();
    if(FPSBodyPoses::Traversing(DisplayState.Motion)||Now<WorldWeaponsHiddenUntil)return true;
    const auto* Hand=WorldEquipmentHands.Find(Mesh);
    return Hand&&*Hand==1&&((DisplayState.bDual&&DisplayState.Action==EFPSBodyAction::Cast)||Now<OffhandWeaponHiddenUntil);
}

void UFPSPlayerBodyComponent::UpdateWorldWeaponPresentation()
{
    const bool BodyVisible=!FPSPlayerBodyWorldBodyHidden();
    const bool BodyShadow=ShouldWorldBodyCastShadow();
    const auto Apply=[&](UPrimitiveComponent* Mesh)
    {
        if(!Mesh)return;
        const bool Stowed=IsWorldWeaponStowed(Mesh);
        const bool Visible=BodyVisible&&!Stowed;
        if(Mesh->IsVisible()!=Visible)Mesh->SetVisibility(Visible);
        if(Mesh->bHiddenInGame==Visible)Mesh->SetHiddenInGame(!Visible);
        // A stowed weapon must not leave a floating weapon-shaped shadow.
        FPSBodyEquipment::ApplyShadowFlags(Mesh,BodyShadow&&!Stowed);
    };
    for(const auto& Weapon:WorldWeapons)Apply(Weapon.Get());
    for(const auto& Part:WorldParts)Apply(Part.Get());
}

void UFPSPlayerBodyComponent::ApplyOutfit(const TArray<FFPSBodyOutfitSlot>& Outfit)
{
    if(FPSPlayerBodyWorldBodySuppressed())return;
    auto* Body=GetBodyMesh();if(!Body||!Configuration.IsValid())return;
    for(auto Part:OutfitMeshes)if(Part)Part->DestroyComponent();OutfitMeshes.Reset();
    for(auto It=OriginalMaterials.CreateIterator();It;++It)
    {
        auto* Mesh=It.Key().Get();if(!IsValid(Mesh)){It.RemoveCurrent();continue;}
        if(auto* Skeletal=Cast<USkeletalMeshComponent>(Mesh);Skeletal&&Skeletal->GetSkeletalMeshAsset()!=It.Value().MeshAsset)
        {It.RemoveCurrent();continue;}
        for(int32 I=0;I<It.Value().Materials.Num();++I)Mesh->SetMaterial(I,It.Value().Materials[I]);
    }
    // Body sections are controlled by the outfit; restore them before applying a new combination.
    const auto* Render=Body->GetSkeletalMeshAsset()?Body->GetSkeletalMeshAsset()->GetResourceForRendering():nullptr;
    if(Render)for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
        Body->ShowMaterialSection(Render->LODRenderData[L].RenderSections[S].MaterialIndex,S,true,L);
    const TSharedPtr<FJsonObject>* Definitions=nullptr;
    if(!Configuration->TryGetObjectField(TEXT("outfits"),Definitions))return;
    const auto Remember=[&](UMeshComponent* Mesh)
    {
        if(OriginalMaterials.Contains(Mesh))return;
        FFPSBodyOriginalMaterials Backup;
        if(auto* Skeletal=Cast<USkeletalMeshComponent>(Mesh))Backup.MeshAsset=Skeletal->GetSkeletalMeshAsset();
        for(int32 I=0;I<Mesh->GetNumMaterials();++I)Backup.Materials.Add(Mesh->GetMaterial(I));
        OriginalMaterials.Add(Mesh,MoveTemp(Backup));
    };
    for(const auto& Entry:Outfit)
    {
        const TSharedPtr<FJsonObject>* Settings=nullptr;
        if(!(*Definitions)->TryGetObjectField(Entry.Definition.ToString(),Settings))continue;
        FString Path;
        if((*Settings)->TryGetStringField(TEXT("world_mesh"),Path))if(auto* Asset=LoadObject<USkeletalMesh>(nullptr,*Path))
        {
            auto* Part=NewObject<USkeletalMeshComponent>(GetOwner(),NAME_None,RF_Transient);
            GetOwner()->AddInstanceComponent(Part);Part->SetSkeletalMeshAsset(Asset);Part->SetupAttachment(Body);
            FPSBodyEquipment::WorldVisibility(Part);Part->RegisterComponent();Part->SetLeaderPoseComponent(Body);
            OutfitMeshes.Add(Part);
        }
        const TArray<TSharedPtr<FJsonValue>>* Hidden=nullptr;
        if(Render&&(*Settings)->TryGetArrayField(TEXT("hide_body_materials"),Hidden))
            for(const auto& Value:*Hidden)for(int32 L=0;L<Render->LODRenderData.Num();++L)for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
                if(Render->LODRenderData[L].RenderSections[S].MaterialIndex==static_cast<int32>(Value->AsNumber()))Body->ShowMaterialSection(static_cast<int32>(Value->AsNumber()),S,false,L);
        const TSharedPtr<FJsonObject>* Overrides=nullptr;
        if((*Settings)->TryGetObjectField(TEXT("body_materials"),Overrides))
        {
            Remember(Body);
            for(const auto& Pair:(*Overrides)->Values)if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*Pair.Value->AsString()))Body->SetMaterial(FCString::Atoi(*Pair.Key),Material);
        }
        if((*Settings)->TryGetObjectField(TEXT("first_person_materials"),Overrides)&&Character.IsValid()&&Character->IsLocallyControlled())
        {
            TArray<USkeletalMeshComponent*> Meshes;GetOwner()->GetComponents(Meshes);
            for(auto* Mesh:Meshes)
            {
                if(Mesh==Body||WorldWeapons.Contains(Mesh)||OutfitMeshes.Contains(Mesh)||!Mesh->GetSkeletalMeshAsset())continue;
                for(const auto& Pair:(*Overrides)->Values)
                {
                    const int32 Slot=Mesh->GetMaterialIndex(FName(*Pair.Key));
                    if(Slot!=INDEX_NONE)if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*Pair.Value->AsString())){Remember(Mesh);Mesh->SetMaterial(Slot,Material);}
                }
            }
        }
    }
    ApplyWorldBodyVisibility();
}
