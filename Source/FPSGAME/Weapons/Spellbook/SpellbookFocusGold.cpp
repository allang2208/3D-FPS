#include "SpellbookComponent.h"
#include "SpellbookBookOrientation.h"
#include "SpellbookFocusMotion.h"
#include "SpellbookFocusInterruptMotion.h"
#include "Components/DynamicMeshComponent.h"
#include "SpellbookGoldGeometry.h"
#include "../../Characters/FPSPlayerBodyComponent.h"
#include "Materials/MaterialInstanceDynamic.h"


void USpellbookComponent::CreateFocusGold(UMaterialInterface* Material)
{
    if(FocusGold||!Material||!FocusBook)return;
    auto* Pawn=GetOwner();FocusGold=NewObject<UDynamicMeshComponent>(Pawn,TEXT("SpellbookGoldOrbits"));
    Pawn->AddInstanceComponent(FocusGold);FocusGold->SetupAttachment(FocusBook);
    FocusGold->SetRelativeTransform(SpellbookBookOrientation::ReadingSurface());
    FocusGold->SetCollisionEnabled(ECollisionEnabled::NoCollision);FocusGold->SetGenerateOverlapEvents(false);
    FocusGold->SetOnlyOwnerSee(true);
    FocusGold->SetCanEverAffectNavigation(false);FocusGold->SetCastShadow(false);
    FocusGold->bReceivesDecals=false;FocusGold->SetVisibility(false);FocusGold->RegisterComponent();
    FocusGold->SetComponentTickEnabled(false);FocusGold->SetMesh(SpellbookGoldGeometry::Build());
    FocusGoldMaterial=UMaterialInstanceDynamic::Create(Material,this);
    FocusGoldMaterial->SetScalarParameterValue(TEXT("Fade"),0.f);FocusGold->SetMaterial(0,FocusGoldMaterial);
}

void USpellbookComponent::ShowFocusGold(bool Visible)
{
    if(const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())Visible&=!Body->IsThirdPersonViewEnabled();
    if(FocusGold&&FocusGold->IsVisible()!=Visible)FocusGold->SetVisibility(Visible);
}

FVector USpellbookComponent::FocusGoldParameters() const
{
    return FVector(GoldFade,FMath::Max(0.f,FocusAge)+(bFocusInterrupted?InterruptAge:(bFocusClosing?CloseAge:0.f)),
        FMath::Abs(FMath::Sin(2.f*PI*PagePhase/SpellbookFocusMotion::PageCycle)));
}

void USpellbookComponent::PresentFocusGold()
{
    if(!FocusGoldMaterial)return;
    namespace Motion=SpellbookFocusMotion;
    GoldFade=bFocusInterrupted?InterruptGoldFade*(1.f-Motion::Ease(0.f,SpellbookFocusInterruptMotion::GoldOut,InterruptAge))
        :Motion::Ease(.18f,.85f,OpenAlpha);
    const FVector Params=FocusGoldParameters();
    FocusGoldMaterial->SetScalarParameterValue(TEXT("GoldAge"),Params.Y);
    FocusGoldMaterial->SetScalarParameterValue(TEXT("Fade"),Params.X);
    FocusGoldMaterial->SetScalarParameterValue(TEXT("PageActivity"),Params.Z);
}
