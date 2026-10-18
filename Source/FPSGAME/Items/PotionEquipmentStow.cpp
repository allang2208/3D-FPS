#include "FPSPotionUseComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/Actor.h"

void UFPSPotionUseComponent::BeginEquipmentStow()
{
    RestoreEquipment();
    auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    if(!EquipmentPivot)
    {
        EquipmentPivot=NewObject<USceneComponent>(GetOwner(),TEXT("ConsumableEquipmentStow"));
        GetOwner()->AddInstanceComponent(EquipmentPivot);EquipmentPivot->SetupAttachment(Camera);EquipmentPivot->RegisterComponent();
    }
    // Enumerate this pawn once per use, never the world. Keep native rigs,
    // attachments, animations and visibility intact beneath a temporary parent.
    TInlineComponentArray<UPrimitiveComponent*> Parts(GetOwner());
    for(auto* Part:Parts)
    {
        if(!Part->bOnlyOwnerSee||Part==Bottle||Part==Liquid||Part==Stopper||Part==FallbackHands)continue;
        USceneComponent* Root=Part;
        while(Root->GetAttachParent()&&Root->GetAttachParent()!=Camera)Root=Root->GetAttachParent();
        if(Root==Camera||Root->GetAttachParent()!=Camera||Root==EquipmentPivot||Root==FallbackHands)continue;
        FEquipmentRoot Entry;Entry.Root=Root;Entry.Parent=Camera;Entry.Socket=Root->GetAttachSocketName();
        EquipmentRoots.Add(Entry);Root->AttachToComponent(EquipmentPivot,FAttachmentTransformRules::KeepRelativeTransform);
    }
}

void UFPSPotionUseComponent::BeginEquipmentFrame()
{
    // Native IK and camera-space weapon placement sample their unshifted rig.
    // The post-update consumable tick applies one offset after that sampling.
    if(EquipmentPivot&&!EquipmentRoots.IsEmpty())EquipmentPivot->SetRelativeTransform(FTransform::Identity);
}

void UFPSPotionUseComponent::RestoreEquipment()
{
    BeginEquipmentFrame();
    for(const FEquipmentRoot& Entry:EquipmentRoots)
        if(Entry.Root.IsValid()&&Entry.Parent.IsValid()&&Entry.Root->GetAttachParent()==EquipmentPivot)
            Entry.Root->AttachToComponent(Entry.Parent.Get(),FAttachmentTransformRules::KeepRelativeTransform,Entry.Socket);
    EquipmentRoots.Reset();
}
