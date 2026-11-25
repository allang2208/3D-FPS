#include "StableHoofstepNotify.h"
#include "StableRidingHorse.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundWave.h"

void UStableHoofstepNotify::Notify(USkeletalMeshComponent* Mesh, UAnimSequenceBase* Animation,
    const FAnimNotifyEventReference& EventReference)
{
    if (auto* Horse = Mesh ? Cast<AStableRidingHorse>(Mesh->GetOwner()) : nullptr)
    {
        if (Mesh == Horse->GetMesh())
            Horse->PlayHoofstep(*this, Animation);
    }
}

void AStableRidingHorse::PlayHoofstep(const UStableHoofstepNotify& Contact, const UAnimSequenceBase* Clip)
{
    // Each listener hears its local copy of the animated horse. No per-hoof network messages.
    if (GetNetMode() == NM_DedicatedServer || Clip != CurrentClip.Get() ||
        !GetCharacterMovement()->IsMovingOnGround() || (!IsSteppingInPlace() && GetVelocity().SizeSquared2D() <= FMath::Square(8.f)) ||
        (GetMesh()->GetPlayRate() < 0.f) != Contact.bReverseOnly || Contact.Variations.IsEmpty())
        return;

    const int32 Count = Contact.Variations.Num();
    int32 Index;
    if (Count > 1 && Contact.Variations.IsValidIndex(LastHoofVariation))
    {
        Index = FMath::RandRange(0, Count - 2);
        if (Index >= LastHoofVariation) ++Index;
    }
    else
    {
        Index = FMath::RandRange(0, Count - 1);
    }
    if (USoundWave* Sound = Contact.Variations[Index])
    {
        LastHoofVariation = Index;
        UGameplayStatics::PlaySoundAtLocation(this, Sound, GetMesh()->GetSocketLocation(Contact.HoofBone),
            FRotator::ZeroRotator, Contact.Gain, FMath::FRandRange(.97f, 1.03f), 0.f, nullptr, nullptr, this);
    }
}
