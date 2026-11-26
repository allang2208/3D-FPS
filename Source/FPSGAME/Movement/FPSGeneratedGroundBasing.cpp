#include "FPSCharacterMovementComponent.h"
#include "../Monsters/WildlifeAnimal.h"
#include "Components/PrimitiveComponent.h"
#include "Interfaces/MovementBaseInterface.h"

namespace
{
bool IsLocalHillsGround(const FMovementBaseInterfaceData* Base)
{
    const auto* C=Base?Cast<UPrimitiveComponent>(Base->PhysicsObjectOwner.Get()):nullptr;
    return C&&C->Mobility==EComponentMobility::Static
        &&(C->ComponentHasTag(TEXT("HillsGround"))||C->ComponentHasTag(TEXT("HillsStaticSupport")));
}
}

void UFPSCharacterMovementComponent::SetBase(UPrimitiveComponent* NewBase,const FName BoneName,bool bNotifyActor)
{
    FMovementBaseInterfaceData Data(NewBase);
    SetBase(&Data,BoneName,bNotifyActor);
}

void UFPSCharacterMovementComponent::SetBase(FMovementBaseInterfaceData* NewBase,const FName BoneName,bool bNotifyActor)
{
    if(IsLocalHillsGround(NewBase))
    {
        // These fixed collision tiles are rebuilt independently on each peer.
        // There is no moving transform to follow and no network object to send.
        // Keep the actual walkable floor: clearing a base must not clear support.
        const FFindFloorResult Floor=CurrentFloor;
        Super::SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr),NAME_None,bNotifyActor);
        CurrentFloor=Floor;
        return;
    }
    Super::SetBase(NewBase,BoneName,bNotifyActor);
}

// Wildlife deliberately keeps the engine's ordinary movement component. Apply
// the same local-ground policy at its Character boundary, without adding any
// player sprint/dodge or humanoid locomotion rules to quadrupeds and birds.
void AColdSteelAnimal::SetBase(UPrimitiveComponent* NewBase,const FName BoneName,bool bNotifyActor)
{
    FMovementBaseInterfaceData Data(NewBase);SetBase(&Data,BoneName,bNotifyActor);
}
void AColdSteelAnimal::SetBase(FMovementBaseInterfaceData* NewBase,const FName BoneName,bool bNotifyActor)
{
    if(IsLocalHillsGround(NewBase))
    {
        auto* Move=GetCharacterMovement();const FFindFloorResult Floor=Move->CurrentFloor;
        Super::SetBase(static_cast<FMovementBaseInterfaceData*>(nullptr),NAME_None,bNotifyActor);
        Move->CurrentFloor=Floor;return;
    }
    Super::SetBase(NewBase,BoneName,bNotifyActor);
}
