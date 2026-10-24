#include "ApartmentDeviceControl.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"

AApartmentDeviceControl::AApartmentDeviceControl()
{
    PrimaryActorTick.bCanEverTick=false;bReplicates=true;
    DeviceName=FText::FromString(TEXT("设备"));
    UseBounds=CreateDefaultSubobject<UBoxComponent>(TEXT("UseBounds"));SetRootComponent(UseBounds);
    UseBounds->SetBoxExtent(FVector(14,4,7));UseBounds->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    UseBounds->SetCollisionResponseToAllChannels(ECR_Ignore);UseBounds->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    UseBounds->SetGenerateOverlapEvents(false);UseBounds->SetCanEverAffectNavigation(false);
    Panel=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Panel"));Panel->SetupAttachment(UseBounds);
    Panel->SetCollisionEnabled(ECollisionEnabled::NoCollision);Panel->SetCanEverAffectNavigation(false);
}

bool AApartmentDeviceControl::ToggleFrom(APlayerController* Controller)
{
    if(!HasAuthority()||!IsValid(Controller)||ColdSteelWorldInteraction::TraceTarget(Controller)!=this)return false;
    bPowered=!bPowered;
    const auto* GS=GetWorld()->GetGameState();PowerStartedAt=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    ForceNetUpdate();return true;
}

float AApartmentDeviceControl::GetPoweredSeconds() const
{
    if(!bPowered)return 0.f;
    const auto* GS=GetWorld()->GetGameState();const float Now=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    return FMath::Max(0.f,Now-PowerStartedAt);
}

FString AApartmentDeviceControl::GetPrompt() const
{
    const TCHAR* State=!bPowered?TEXT("已关闭 · 启动"):
        bPresentationActive?TEXT("运行中 · 关闭"):
        bWorkout?TEXT("已暂停 · 关闭"):TEXT("待机 · 关闭");
    return DeviceName.ToString()+TEXT(" · ")+State;
}

void AApartmentDeviceControl::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AApartmentDeviceControl,bPowered);
    DOREPLIFETIME(AApartmentDeviceControl,PowerStartedAt);
}
