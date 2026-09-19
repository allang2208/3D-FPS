#include "ZombieDogAppearanceComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Character.h"
#include "Materials/MaterialInstanceDynamic.h"

UZombieDogAppearanceComponent::UZombieDogAppearanceComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UZombieDogAppearanceComponent::GenerateLayout()
{
    Wounds.Reset();
    if (!SurfaceSet || SurfaceSet->Surfaces.IsEmpty()) return;
    if (RandomSeed <= 0) RandomSeed = FMath::RandRange(1, MAX_int32);
    FRandomStream Random(RandomSeed);
    const int32 Minimum = FMath::Clamp(MinWounds, 0, 8);
    const int32 Desired = Random.RandRange(Minimum, FMath::Clamp(MaxWounds, Minimum, 8));
    float TotalArea = 0.f;
    TArray<float> CumulativeArea;
    for (const auto& Surface : SurfaceSet->Surfaces)
    {
        TotalArea += FMath::Max(0.f, Surface.Area);
        CumulativeArea.Add(TotalArea);
    }
    if (TotalArea <= SMALL_NUMBER) return;
    int32 RegionCounts[8] = {};
    for (int32 Attempt = 0; Attempt < 192 && Wounds.Num() < Desired; ++Attempt)
    {
        const float Pick = Random.FRand() * TotalArea;
        int32 Low = 0, High = CumulativeArea.Num() - 1;
        while (Low < High)
        {
            const int32 Mid = (Low + High) / 2;
            if (CumulativeArea[Mid] < Pick) Low = Mid + 1; else High = Mid;
        }
        const auto& Surface = SurfaceSet->Surfaces[Low];
        const int32 Region = FMath::Clamp(Surface.Region, 0, 7);
        const bool MainWound = Wounds.IsEmpty();
        // The one dominant injury belongs on a broad torso surface. Small marks
        // may use the neck and upper legs without turning every patch into a hole.
        if (MainWound && (Region == 4 || Region >= 6)) continue;
        if (RegionCounts[Region] >= 2) continue;
        const float Root = FMath::Sqrt(Random.FRand()), Along = Random.FRand();
        FZombieDogWoundPlacement Wound;
        Wound.Center = Surface.A * (1.f - Root) + Surface.B * (Root * (1.f - Along)) + Surface.C * (Root * Along);
        Wound.Normal = Surface.Normal.GetSafeNormal();
        Wound.Region = Region;
        const bool Leg = Region >= 6;
        const bool Neck = Region == 4;
        Wound.Style = MainWound ? (Random.FRand() < .65f ? 0 : 3)
            : (Leg || Neck ? (Random.FRand() < .7f ? 2 : 0) : (Random.FRand() < .55f ? 1 : 2));
        Wound.Healing = Wound.Style == 2 ? Random.FRandRange(.8f, 1.f)
            : MainWound ? Random.FRandRange(.12f, .3f) : Random.FRandRange(.35f, .65f);
        Wound.Radii = FVector(Random.FRandRange(MainWound ? 8.f : 3.f, MainWound ? 11.f : 6.f),
            Random.FRandRange(MainWound ? 4.f : Leg ? 1.4f : 2.f, MainWound ? 5.5f : Leg ? 2.2f : 3.8f),
            Leg ? 1.8f : Neck ? 3.f : 4.5f);
        bool Overlaps = false;
        for (const auto& Other : Wounds)
            if (FVector::DistSquared(Wound.Center, Other.Center) < FMath::Square(.85f * (Wound.Radii.X + Other.Radii.X)))
            { Overlaps = true; break; }
        if (Overlaps) continue;
        const FVector AnatomicalAxis = Leg || Neck || Region == 2 || Region == 3
            ? FVector::UpVector : FVector::RightVector; // Rest +Y follows the body.
        FVector Up = AnatomicalAxis - Wound.Normal * FVector::DotProduct(AnatomicalAxis, Wound.Normal);
        if (!Up.Normalize()) Up = FVector::CrossProduct(Wound.Normal, FVector::ForwardVector).GetSafeNormal();
        const FVector Side = FVector::CrossProduct(Wound.Normal, Up).GetSafeNormal();
        const float Angle = FMath::DegreesToRadians(Random.FRandRange(-25.f, 25.f));
        Wound.TangentU = Up * FMath::Cos(Angle) + Side * FMath::Sin(Angle);
        Wound.TangentV = FVector::CrossProduct(Wound.Normal, Wound.TangentU).GetSafeNormal();
        Wound.Severity = Random.FRandRange(MainWound ? .86f : .55f, MainWound ? 1.f : .8f);
        Wounds.Add(Wound); ++RegionCounts[Region];
    }
    AppliedSeed = RandomSeed; AppliedMin = MinWounds; AppliedMax = MaxWounds;
    AppliedSurfaceSet = SurfaceSet;
}

void UZombieDogAppearanceComponent::ApplyAppearance(USkeletalMeshComponent* Mesh)
{
    if (!bEnabled || !Mesh || !SurfaceSet) return;
    if (AppliedSeed != RandomSeed || AppliedMin != MinWounds || AppliedMax != MaxWounds || AppliedSurfaceSet != SurfaceSet)
        GenerateLayout();
    Materials.SetNum(Mesh->GetNumMaterials());
    for (int32 Slot = 0; Slot < Materials.Num(); ++Slot)
    {
        auto& Material = Materials[Slot];
        if (!Material || Mesh->GetMaterial(Slot) != Material)
            Material = Mesh->CreateDynamicMaterialInstance(Slot);
        if (!Material) continue;
        Material->SetScalarParameterValue(TEXT("WoundSeed"), static_cast<float>(RandomSeed % 8191));
        for (int32 Index = 0; Index < 8; ++Index)
        {
            const FString Suffix = FString::FromInt(Index);
            const FZombieDogWoundPlacement* Wound = Wounds.IsValidIndex(Index) ? &Wounds[Index] : nullptr;
            const auto Packed = [](const FVector& V, float W) { return FLinearColor(V.X, V.Y, V.Z, W); };
            Material->SetVectorParameterValue(FName(*(TEXT("WoundCenter") + Suffix)), Wound ? Packed(Wound->Center, Wound->Severity) : FLinearColor::Transparent);
            Material->SetVectorParameterValue(FName(*(TEXT("WoundU") + Suffix)), Wound ? Packed(Wound->TangentU, Wound->Radii.X) : FLinearColor(1,0,0,1));
            Material->SetVectorParameterValue(FName(*(TEXT("WoundV") + Suffix)), Wound ? Packed(Wound->TangentV, Wound->Radii.Y) : FLinearColor(0,1,0,1));
            Material->SetVectorParameterValue(FName(*(TEXT("WoundN") + Suffix)), Wound ? Packed(Wound->Normal, Wound->Radii.Z) : FLinearColor(0,0,1,1));
            Material->SetVectorParameterValue(FName(*(TEXT("WoundStyle") + Suffix)), Wound
                ? FLinearColor(Wound->Style, Wound->Healing, Index == 0 ? .12f : .065f, 0.f)
                : FLinearColor(0, 1, 0, 0));
        }
    }
}

void UZombieDogAppearanceComponent::RerollWounds()
{
    RandomSeed = 0; AppliedSeed = INDEX_NONE;
    if (auto* Character = Cast<ACharacter>(GetOwner())) ApplyAppearance(Character->GetMesh());
}
