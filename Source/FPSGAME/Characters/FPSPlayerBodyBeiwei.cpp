#include "FPSPlayerBodyComponent.h"
#include "../Weapons/BeiweiSwordTrailComponent.h"
#include "../Weapons/FrostSwordRunes.h"
#include "../FPSGAMECharacter.h"
#include "Components/StaticMeshComponent.h"

void UFPSPlayerBodyComponent::PresentBeiweiTrail()
{
    if(GetNetMode()==NM_DedicatedServer||!Character.IsValid())return;
    for(const auto& Binding:MotionBindings)
    {
        const auto& W=Binding.Definition;
        if(W.ItemInstance!=DisplayState.WeaponInstance||W.PoseFamily!=TEXT("Sword"))continue;
        for(int32 I=0;I<W.Parts.Num();++I)
        {
            const auto& P=W.Parts[I];
            const bool Gold=P.RuneDefinition==ColdSteelFrostRunes::Zhanmadao&&P.RuneId==ColdSteelFrostRunes::Beiwei&&
                P.RuneSlot==TEXT("SwordSlot=blade_1");
            if((!Gold&&!P.bChixiaoBlade&&!P.bZhufengBlade)||!Binding.Parts.IsValidIndex(I))continue;
            auto* Blade=Binding.Parts[I].Get();if(!Blade)continue;
            if(!BeiweiWorldTrail)
            {
                BeiweiWorldTrail=NewObject<UBeiweiSwordTrailComponent>(GetOwner());GetOwner()->AddInstanceComponent(BeiweiWorldTrail);
                BeiweiWorldTrail->RegisterComponent();
            }
            if(BeiweiWorldInstance!=W.ItemInstance){BeiweiWorldTrail->Clear();BeiweiWorldInstance=W.ItemInstance;}
            BeiweiWorldTrail->SetView(false,!IsThirdPersonViewEnabled());
            Blade->UpdateComponentToWorld();const auto& Frame=Blade->GetComponentTransform();
            const bool Crimson=P.bChixiaoBlade&&DisplayState.bChixiaoHeavyTrail;
            const bool Cyan=P.bZhufengBlade&&DisplayState.bZhufengWhirlwindTrail;
            const bool Active=(Cyan||Crimson||(Gold&&DisplayState.bBeiweiMartial))&&Blade->IsVisible()&&!Blade->bHiddenInGame&&
                !IsWorldWeaponStowed(Blade)&&DisplayState.Action!=EFPSBodyAction::Dead;
            BeiweiWorldTrail->Feed(Frame.TransformPosition(P.BeiweiBladeBase),Frame.TransformPosition(P.BeiweiBladeTip),Active,
                Cyan?ESwordTrailPalette::Cyan:Crimson?ESwordTrailPalette::Crimson:ESwordTrailPalette::Gold);
            return;
        }
    }
    if(BeiweiWorldTrail)BeiweiWorldTrail->Clear();BeiweiWorldInstance.Reset();
}
