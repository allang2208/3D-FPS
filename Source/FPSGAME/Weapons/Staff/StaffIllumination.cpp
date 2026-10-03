#include "StaffWeaponComponent.h"
#include "StaffAssembly.h"
#include "../../FPSGAMECharacter.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "../../FPSGAMEPlayerController.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "Camera/CameraComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace StaffIllumination
{
    const FName AmountParameter(TEXT("StaffLightAmount"));
    constexpr float Lumens=1000.f;
    constexpr float RadiusCm=800.f;
    constexpr float EmissiveStrength=3.f;
    constexpr float ChargeHoldSeconds=.12f;
    constexpr float GestureSeconds=StaffCastMotion::ReadySeconds+ChargeHoldSeconds+StaffCastMotion::RecoverSeconds;
    const FLinearColor Color(1.f,.94f,.82f);
}

void UStaffWeaponComponent::ConfigureIllumination(const FColdSteelItem& Resolved)
{
    // Resolve the actual installed head once, so every crystal option works and
    // wood, bindings and other copies of shared elemental materials stay unchanged.
    bCanIlluminate=Resolved.Definition==TEXT("ue_apprentice_staff");
    if(!bCanIlluminate||!Staff)return;
    const FString HeadPath=ColdSteelInventory::Text(Resolved,TEXT("staff_part_head_crystal_mesh"));
    UStaticMeshComponent* Head=nullptr;
    for(auto* Part:ColdSteelStaffAssembly::Components(Staff))
        if(Part->GetStaticMesh()&&Part->GetStaticMesh()->GetPathName()==HeadPath){Head=Part;break;}
    if(!Head){bCanIlluminate=false;return;}
    for(int32 Slot=0;Slot<Head->GetNumMaterials();++Slot)
    {
        auto* Material=Head->GetMaterial(Slot);float Value=0.f;
        if(!Material||!Material->GetScalarParameterValue(FMaterialParameterInfo(StaffIllumination::AmountParameter),Value))continue;
        if(auto* Dynamic=Head->CreateDynamicMaterialInstance(Slot))
        {
            Dynamic->SetScalarParameterValue(StaffIllumination::AmountParameter,0.f);
            CrystalLightMaterials.Add(Dynamic);
        }
    }
    if(!CrystalLight)
    {
        CrystalLight=NewObject<UPointLightComponent>(GetOwner(),TEXT("StaffCrystalLight"));
        GetOwner()->AddInstanceComponent(CrystalLight);
        CrystalLight->SetupAttachment(Staff);
        CrystalLight->SetMobility(EComponentMobility::Movable);
        CrystalLight->SetIntensityUnits(ELightUnits::Lumens);
        // A gameplay lamp stays readable under the scene's automatic exposure.
        CrystalLight->SetInverseExposureBlend(1.f);
        CrystalLight->SetAttenuationRadius(StaffIllumination::RadiusCm);
        CrystalLight->SetSourceRadius(3.f);
        CrystalLight->SetSoftSourceRadius(5.f);
        // One nearby shadowed light: dungeon walls still occlude its illumination.
        CrystalLight->SetCastShadows(true);
        CrystalLight->SetVolumetricScatteringIntensity(.15f);
        CrystalLight->SetLightColor(StaffIllumination::Color);
        CrystalLight->SetIntensity(0.f);
        CrystalLight->SetVisibility(false);
        CrystalLight->RegisterComponent();
    }
    const FVector HeadCenter=Head->GetRelativeTransform().TransformPosition(Head->GetStaticMesh()->GetBoundingBox().GetCenter());
    CrystalLight->SetRelativeLocation(HeadCenter);
    PublishedIllumination=-1.f;
    UpdateIllumination(0.f);
    PublishIllumination();
}

void UStaffWeaponComponent::ToggleIllumination()
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(!bCanIlluminate||!IsEquipped()||!Staff||!Staff->IsVisible()||!Pawn||!Pawn->IsLocallyControlled()||Pawn->IsTraversing())return;
    const auto* PC=Cast<APlayerController>(Pawn->GetController());
    if(AFPSGAMEPlayerController::BlocksOngoingActions(PC)||Pawn->IsAmmoWheelOpen())return;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    // No cooldown, mana/stamina debit, durability drain or held-button requirement.
    // Repeated clicks toggle immediately; only a free arm starts another gesture.
    // Snapshot the previous gesture so a click midway through recovery cannot jump.
    bIlluminationOn=!bIlluminationOn;
    if(!IsBusy()&&!Pawn->IsSpellGestureBlocking())
    {
        IlluminationGestureEntry=CarryPoseInCamera();
        IlluminationGestureAge=0.f;
    }
}

FStaffCastPose UStaffWeaponComponent::SampleIlluminationGesture(const FStaffCastPose& Carry)const
{
    if(IlluminationGestureAge<0.f)return Carry;
    if(IlluminationGestureAge<StaffCastMotion::ReadySeconds)
        return StaffCastMotion::Raise(IlluminationGestureEntry,IlluminationGestureAge/StaffCastMotion::ReadySeconds);
    const float RecoveryAge=IlluminationGestureAge-StaffCastMotion::ReadySeconds-StaffIllumination::ChargeHoldSeconds;
    if(RecoveryAge<0.f)return StaffCastMotion::Raised();
    return StaffCastMotion::Recover(StaffCastMotion::Raised(),Carry,RecoveryAge/StaffCastMotion::RecoverSeconds);
}

void UStaffWeaponComponent::UpdateIllumination(float Delta)
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    if(IlluminationGestureAge>=0.f)
    {
        IlluminationGestureAge+=Delta;
        // Spell entry already snapshots the actual carry pose. Its recovery must
        // target the ordinary carry, not a dormant second casting gesture.
        if(IlluminationGestureAge>=StaffIllumination::GestureSeconds||Age>=0.f
            ||(Pawn&&Pawn->IsSpellGestureBlocking()))IlluminationGestureAge=-1.f;
    }
    if(!CrystalLight)return;
    const bool On=bCanIlluminate&&bIlluminationOn&&IsEquipped();
    const float Seconds=On?StaffCastMotion::ReadySeconds:StaffCastMotion::RecoverSeconds;
    IlluminationBlend=FMath::FInterpConstantTo(IlluminationBlend,On?1.f:0.f,Delta,1.f/Seconds);
}

void UStaffWeaponComponent::PublishIllumination()
{
    if(!CrystalLight)return;
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Body=Pawn?Pawn->FindComponentByClass<UFPSPlayerBodyComponent>():nullptr;
    const bool Visible=Pawn&&Pawn->IsLocallyControlled()&&!Pawn->IsHidden()&&Staff&&Staff->IsVisible()&&(!Body||!Body->IsThirdPersonViewEnabled());
    const float Level=Visible?StaffCastMotion::Ease(IlluminationBlend):0.f;
    // Stable on/off states do not continually dirty the light or material proxies.
    if(Level==PublishedIllumination)return;
    PublishedIllumination=Level;
    CrystalLight->SetIntensity(StaffIllumination::Lumens*Level);
    CrystalLight->SetVisibility(Level>0.f);
    for(const auto& Material:CrystalLightMaterials)
        if(Material)Material->SetScalarParameterValue(StaffIllumination::AmountParameter,StaffIllumination::EmissiveStrength*Level);
}

void UStaffWeaponComponent::ResetIllumination()
{
    IlluminationGestureAge=-1.f;
    bCanIlluminate=false;bIlluminationOn=false;IlluminationBlend=0.f;PublishedIllumination=-1.f;
    if(CrystalLight){CrystalLight->SetIntensity(0.f);CrystalLight->SetVisibility(false);}
    for(const auto& Material:CrystalLightMaterials)
        if(Material)Material->SetScalarParameterValue(StaffIllumination::AmountParameter,0.f);
    CrystalLightMaterials.Reset();
}
