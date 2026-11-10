#include "ColdSteelEnhancementAuditTarget.h"
#include "EnhancementEscrowAuditCommandlet.h"
#include "ColdSteelStatusModel.h"
#include "../FPSGAMEPlayerController.h"
#include "Components/BoxComponent.h"
#include "Engine/GameInstance.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

AColdSteelEnhancementAuditTarget::AColdSteelEnhancementAuditTarget()
{
    auto* Box=CreateDefaultSubobject<UBoxComponent>(TEXT("Target"));SetRootComponent(Box);Box->SetBoxExtent(FVector(15,40,40));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionResponseToAllChannels(ECR_Ignore);
    Box->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);SetCanBeDamaged(true);
}
float AColdSteelEnhancementAuditTarget::TakeDamage(float Amount,const FDamageEvent&,AController*,AActor*){Received+=Amount;return Amount;}
void AFPSGAMEPlayerController::RunEnhancementAudit()
{
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Model||!Model->IsAudit())return;
    // The old audit processed inventory items directly and asserted the retired
    // preview studio. All processing now belongs to persistent bench escrow.
    // UI/ritual visuals and true RPC transport require their own runtime fixture.
    if(FParse::Param(FCommandLine::Get(),TEXT("EnhancementUIPreview")))
    {
        UE_LOG(LogTemp,Error,TEXT("Enhancement: retired studio preview is unsupported; use a real world workbench session"));
        ConsoleCommand(TEXT("quit"));return;
    }
    int32 Checks=0,Failures=0;
    UEnhancementEscrowAuditCommandlet::Run(Model,FParse::Param(FCommandLine::Get(),TEXT("EnhancementLoadAudit")),[&](bool Passed,const TCHAR* Name)
    {
        ++Checks;Failures+=!Passed;UE_LOG(LogTemp,Display,TEXT("Enhancement: %s %s"),Passed?TEXT("PASS"):TEXT("FAIL"),Name);
    });
    UE_LOG(LogTemp,Display,TEXT("Enhancement: COMPLETE checks=%d failures=%d (escrow authority; no UDP or visual coverage)"),Checks,Failures);
    ConsoleCommand(TEXT("quit"));
}
