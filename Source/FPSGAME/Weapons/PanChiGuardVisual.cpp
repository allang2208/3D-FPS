#include "PanChiGuardComponent.h"
#include "RuneSwordComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "UDynamicMesh.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace PanChiVisual
{
const FSoftObjectPath Guard(TEXT("/Game/Weapons/XuanChiZhenYue20261004/PanChiEffects20261006/M_PanChiGuardGlow.M_PanChiGuardGlow"));
const FSoftObjectPath Spirit(TEXT("/Game/Weapons/XuanChiZhenYue20261004/PanChiFlight20261007/M_PanChiFlyingDragon.M_PanChiFlyingDragon"));
const FSoftObjectPath Motes(TEXT("/Game/Weapons/XuanChiZhenYue20261004/PanChiRelease20261007/M_PanChiGoldenMotes.M_PanChiGoldenMotes"));
const FSoftObjectPath Circle(TEXT("/Game/Weapons/XuanChiZhenYue20261004/PanChiUppercut20261007/M_PanChiUppercutCircle.M_PanChiUppercutCircle"));
}
void UPanChiGuardComponent::RequestVisuals()
{
    if(bVisualsRequested||GetNetMode()==NM_DedicatedServer)return;bVisualsRequested=true;
    const TWeakObjectPtr<UPanChiGuardComponent> Weak(this);
    VisualLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{PanChiVisual::Guard,PanChiVisual::Spirit,PanChiVisual::Motes,PanChiVisual::Circle},FStreamableDelegate::CreateLambda([Weak]()
    {
        if(auto* Self=Weak.Get())
        {
            Self->GuardMaterial=Cast<UMaterialInterface>(PanChiVisual::Guard.ResolveObject());
            Self->SpiritMaterial=Cast<UMaterialInterface>(PanChiVisual::Spirit.ResolveObject());
            Self->MoteMaterial=Cast<UMaterialInterface>(PanChiVisual::Motes.ResolveObject());
            Self->CircleMaterial=Cast<UMaterialInterface>(PanChiVisual::Circle.ResolveObject());
            Self->RefreshGuardVisual();
            if(Self->Clock()-Self->ReleaseAt<Self->ReleaseVisualSeconds){Self->BuildSpiritMeshes();Self->TickReleaseVisual();}
        }
    }));
}
void UPanChiGuardComponent::RefreshGuardVisual()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(!IsActive())
    {
        if(GuardMID)GuardMID->SetScalarParameterValue(TEXT("Stacks"),0.f);
        if(GuardMesh.IsValid()&&GuardMesh->GetOverlayMaterial()==GuardMID)GuardMesh->SetOverlayMaterial(nullptr);
        GuardMesh.Reset();return;
    }
    if(!GuardMaterial)return;
    if(!GuardMesh.IsValid())
    {
        const auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>();
        const auto* Arms=Sword?Sword->ArmsMesh():nullptr;if(!Arms)return;
        TInlineComponentArray<UStaticMeshComponent*> Meshes(GetOwner());
        for(auto* Mesh:Meshes)if(Mesh->ComponentHasTag(TEXT("SwordSlot=guard"))&&Mesh->IsAttachedTo(Arms))
        {GuardMesh=Mesh;break;}
    }
    if(!GuardMesh.IsValid())return;
    if(!GuardMID)GuardMID=UMaterialInstanceDynamic::Create(GuardMaterial,this);
    // Whirlwind may temporarily install a temporal material. Do not replace that override.
    if(!GuardMesh->GetOverlayMaterial()||GuardMesh->GetOverlayMaterial()==GuardMID)GuardMesh->SetOverlayMaterial(GuardMID);
    GuardMID->SetScalarParameterValue(TEXT("Stacks"),Charges());
    GuardMID->SetScalarParameterValue(TEXT("Ready"),CooldownRemaining()<=0.f?1.f:0.f);
    const float SinceRelease=float(Clock()-ReleaseAt);
    GuardMID->SetScalarParameterValue(TEXT("ReleaseFlash"),SinceRelease>=0.f?FMath::Square(FMath::Max(0.f,1.f-SinceRelease/.22f)):0.f);
}
