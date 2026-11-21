// Source/FPSGAME/Multiplayer/FPSStatusReplicationComponent.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 8-8 | file scope
#include "../WorldGeneration/VillageDefenseSection.h"

// Lines 34-51 | void UFPSStatusReplicationComponent::BindDefenseEffects(UStatusEffectsComponent& Effects)
void UFPSStatusReplicationComponent::BindDefenseEffects(UStatusEffectsComponent& Effects)
{
    AActor* Owner=Effects.GetOwner();
    if(!Owner->IsA<AVillageDefenseSection>() || !Owner->HasAuthority() || Owner->GetNetMode()==NM_Standalone)return;
    auto* Replica=NewObject<UFPSStatusReplicationComponent>(Owner);
    Owner->AddInstanceComponent(Replica);
    Replica->RegisterComponent();
    Replica->SetComponentTickEnabled(false);
    Effects.OnChanged.AddUObject(Replica,&UFPSStatusReplicationComponent::PublishDefenseEffects);
}

void UFPSStatusReplicationComponent::PublishDefenseEffects()
{
    GetOwner()->FlushNetDormancy();
    CaptureAuthorityState();
    GetOwner()->ForceNetUpdate();
}


// Lines 153-153 | void UFPSStatusReplicationComponent::OnRep_State()
    if(GetOwner()->IsA<AVillageDefenseSection>())SetComponentTickEnabled(!State.Display.IsEmpty());
