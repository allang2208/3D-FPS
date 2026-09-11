#include "BallisticAuditTarget.h"
#include "Components/BoxComponent.h"
ABallisticAuditTarget::ABallisticAuditTarget()
{
    auto* Box=CreateDefaultSubobject<UBoxComponent>(TEXT("Target"));SetRootComponent(Box);
    Box->SetBoxExtent(FVector(15,40,40));Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Box->SetCollisionResponseToAllChannels(ECR_Ignore);Box->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    SetCanBeDamaged(true);
}
float ABallisticAuditTarget::TakeDamage(float Amount,const FDamageEvent&,AController*,AActor*)
{Received+=Amount;return Amount;}
