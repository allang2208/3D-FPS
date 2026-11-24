#include "BowArrow.h"
#include "../../Skills/ElementalArrowVisual.h"
#include "../../Skills/ElementalArrowBurst.h"
#include "Engine/World.h"
#include "Components/SceneComponent.h"

void ABowArrow::SetElementalCast(const FElementalArrowCast& Snapshot)
{
    ElementalCast=Snapshot;Presentation.Element=Snapshot.Element;
    if(Snapshot.Element==EArrowElement::Fire){Presentation.bFlameArmor=false;StopFlameVisual();}
    ForceNetUpdate();
}
void ABowArrow::UpdateElementVisual(float Delta)
{
    if(Presentation.bAuroraBeam||bStuck||bElementBurst||!ElementalArrow::IsElement(Presentation.Element))
    {if(ElementVisual)ElementVisual->Clear();return;}
    if(!ElementVisual){ElementVisual=NewObject<UElementalArrowVisual>(this);ElementVisual->RegisterComponent();}
    const FVector Tip=GetActorLocation();
    ElementVisual->Update(Presentation.Element,Tip-GetActorForwardVector()*Presentation.Length,Tip,Delta,true,true,Root);
}
void ABowArrow::BurstElement(const FHitResult& Hit)
{
    if(!HasAuthority()||bElementBurst||!ElementalArrow::IsElement(ElementalCast.Element))return;
    bElementBurst=true;if(ElementVisual)ElementVisual->Clear();ForceNetUpdate();
    ElementalCast.EclipseShot = EclipseShot;
    FActorSpawnParameters P;P.Owner=GetInstigator();P.Instigator=GetInstigator();P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Burst=GetWorld()->SpawnActor<AElementalArrowBurst>(Hit.ImpactPoint,FRotator::ZeroRotator,P))Burst->Launch(GetInstigator(),ElementalCast,Hit);
}
