#include "VillageArtisanAppearance.h"
#include "ResidentConversation.h"

#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

namespace VillageArtisanAssets
{
    const FSoftObjectPath StrongBody(TEXT("/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Body.SK_Smith_Body"));
    const FSoftObjectPath StandingBreath(TEXT("/Game/Characters/VillageBlacksmithNPC20261118/Animations/A_Smith_StandingBreath.A_Smith_StandingBreath"));
}

TArray<FSoftObjectPath> FVillageArtisanAppearance::Paths() const
{
    return {VillageArtisanAssets::StrongBody, HeadMesh, WorkwearMesh, VillageArtisanAssets::StandingBreath};
}

bool FVillageArtisanAppearance::IsCompiling() const
{
#if WITH_EDITOR
    for (const FSoftObjectPath& Path : Paths())
        if (const USkeletalMesh* Mesh = Cast<USkeletalMesh>(Path.ResolveObject()); Mesh && Mesh->IsCompiling())
            return true;
#endif
    return false;
}

void FVillageArtisanAppearance::Dress(USkeletalMeshComponent& Body, USkeletalMeshComponent& Head,
                                      USkeletalMeshComponent& Workwear, FResidentConversationFacing& Facing) const
{
    const FSoftObjectPath& IdlePath = VillageArtisanAssets::StandingBreath;
    UAnimSequence* Idle = Cast<UAnimSequence>(IdlePath.ResolveObject());
    if (!Idle)
    {
        UE_LOG(LogTemp, Error, TEXT("%s cannot load %s"), *GetNameSafe(Body.GetOwner()), *IdlePath.ToString());
        return;
    }
    USkeletalMeshComponent* Parts[] = {&Body, &Head, &Workwear};
    const FSoftObjectPath* Meshes[] = {&VillageArtisanAssets::StrongBody, &HeadMesh, &WorkwearMesh};
    for (int32 Index = 0; Index < UE_ARRAY_COUNT(Parts); ++Index)
    {
        USkeletalMesh* Mesh = Cast<USkeletalMesh>(Meshes[Index]->ResolveObject());
        if (!Mesh)
        {
            UE_LOG(LogTemp, Error, TEXT("%s cannot load %s"), *GetNameSafe(Body.GetOwner()), *Meshes[Index]->ToString());
            return;
        }
        Parts[Index]->SetSkeletalMeshAsset(Mesh);
    }
    float IdleTime=0.f;
    if (const auto* GameState = Body.GetWorld()->GetGameState(); GameState && Idle->GetPlayLength() > 0.f)
        IdleTime=FMath::Fmod(GameState->GetServerWorldTimeSeconds(), double(Idle->GetPlayLength()));
    Facing.StartIdle(Body,*Idle,IdleTime);
    for (USkeletalMeshComponent* Part : {&Head, &Workwear})
    {
        Part->SetLeaderPoseComponent(&Body);
        Part->SetComponentTickEnabled(false);
    }
    for (USkeletalMeshComponent* Part : Parts)
        Part->SetVisibility(true);
}
