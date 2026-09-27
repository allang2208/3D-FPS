#include "PistolGripSurface.h"
#include "GunsmithSystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"

namespace PistolGripSurface
{
bool IsPart(const FString& Part)
{
    return Part == TEXT("pistol_grip_granular") || Part == TEXT("pistol_grip_diamond") || Part == TEXT("pistol_grip_quickdot");
}
FString MeshPath(const FGunsmithWeapon* Weapon)
{
    const TSharedPtr<FJsonObject>* Binding = nullptr;
    FString Path;
    if (Weapon && Weapon->Source.IsValid() && Weapon->Source->TryGetObjectField(TEXT("pistol_grip_surface"), Binding))
        (*Binding)->TryGetStringField(TEXT("mesh"), Path);
    return Path;
}
bool Supports(const FGunsmithWeapon* Weapon) { return !MeshPath(Weapon).IsEmpty(); }
FString MaterialPath(const FString& Part)
{
    return IsPart(Part) ? TEXT("/Game/Weapons/PistolGripSurface20260927/Materials/M_") + Part : FString();
}
void MergeOptions(const TSharedPtr<FJsonObject>& Catalog, const TSharedPtr<FJsonObject>& Weapon, TArray<FString>& Allowed)
{
    const TSharedPtr<FJsonObject>* Binding = nullptr;
    const TArray<TSharedPtr<FJsonValue>>* Shared = nullptr;
    FString Mesh;
    if (!Weapon->TryGetObjectField(TEXT("pistol_grip_surface"), Binding)
        || !(*Binding)->TryGetStringField(TEXT("mesh"), Mesh) || Mesh.IsEmpty()
        || !Catalog->TryGetArrayField(TEXT("pistol_grip_surface_options"), Shared)) return;
    // Explicit host binding only: never broadcast the family to every firearm.
    // A surface-treatment slot does not merge in full replacement grips.
    Weapon->GetObjectField(TEXT("options"))->SetArrayField(TEXT("reargrip"), *Shared);
    Allowed.AddUnique(TEXT("reargrip"));
}
UStaticMeshComponent* Configure(AActor* Owner, USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing, const FGunsmithWeapon* Weapon, const FString& Part, bool bEnabled)
{
    auto Remove = [&]() -> UStaticMeshComponent*
    {
        // Weapon-wide visibility propagation must not resurrect an old overlay.
        if (Existing) Existing->DestroyComponent();
        return nullptr;
    };
    auto* Asset = Host ? Host->GetSkeletalMeshAsset() : nullptr;
    if (!bEnabled || !Asset || !Supports(Weapon) || !IsPart(Part)) return Remove();
    const auto Binding = Weapon->Source->GetObjectField(TEXT("pistol_grip_surface"));
    FString BoneName = TEXT("WPN_root");Binding->TryGetStringField(TEXT("bone"), BoneName);
    const FName Bone(*BoneName);
    const auto& Ref = Asset->GetRefSkeleton();
    if (Ref.FindBoneIndex(Bone) == INDEX_NONE) return Remove();
    auto* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath(Weapon));
    auto* Material = LoadObject<UMaterialInterface>(nullptr, *MaterialPath(Part));
    if (!Mesh || !Material)
    {
        UE_LOG(LogTemp, Error, TEXT("Missing pistol grip surface for %s / %s"), *Weapon->Id, *Part);
        return Remove();
    }
    if (!Existing)
    {
        Existing = NewObject<UStaticMeshComponent>(Owner);
        Existing->SetupAttachment(Host, Bone);
        Existing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Existing->SetCastShadow(false);
        Existing->bReceivesDecals = false;
        Existing->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);
        Existing->SetOnlyOwnerSee(Host->bOnlyOwnerSee);
        Existing->RegisterComponent();
    }
    Existing->EmptyOverrideMaterials();
    Existing->SetStaticMesh(Mesh);
    Existing->SetMaterial(0, Material);
    FTransform Bind = FTransform::Identity;
    for (int32 I = Ref.FindBoneIndex(Bone); I != INDEX_NONE; I = Ref.GetParentIndex(I))
        Bind = Bind * Ref.GetRefBonePose()[I];
    // Per-host mesh frame, original factory grip visible underneath.
    Existing->SetRelativeTransform(FTransform::Identity.GetRelativeTransform(Bind));
    Existing->SetVisibility(true);
    return Existing;
}
}
