#include "ColdSteelContactDoor.h"
#include "Components/BoxComponent.h"
#include "GameFramework/Pawn.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    // 触发盒尺寸（cm）：门洞宽 120（Y 半 60）、进深 40（X 半 20，两侧各多出 10 容忍贴面站位）、
    // 高 240。挂在占格锚点上（门族构件锚点 = 占格底面中心，门自己往上搭）。
    const FVector ContactZoneExtent(30.f, 60.f, 120.f);
    const FVector ContactZoneCentre(0.f, 0.f, 120.f);
    // 铁门开/关共用金属声（opengameart "Iron Door"，CC0）。
    const TCHAR* IronDoorSoundPath=TEXT("/Game/Audio/Interactions/DoorAudio20261004/S_Door_Iron.S_Door_Iron");
}

AColdSteelContactDoor::AColdSteelContactDoor()
{
    ContactZone=CreateDefaultSubobject<UBoxComponent>(TEXT("ContactZone"));
    ContactZone->SetupAttachment(GetRootComponent());
    ContactZone->SetRelativeLocation(ContactZoneCentre);
    ContactZone->SetBoxExtent(ContactZoneExtent);
    // 只做触发，不挡路：门板自己的碰撞口径（关门才挡玩家）不变。
    ContactZone->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    ContactZone->SetCollisionObjectType(ECC_WorldDynamic);
    ContactZone->SetCollisionResponseToAllChannels(ECR_Ignore);
    ContactZone->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    ContactZone->SetCanEverAffectNavigation(false);

    static ConstructorHelpers::FObjectFinder<USoundBase> IronSound(IronDoorSoundPath);
    if(IronSound.Succeeded()){OpenSound=IronSound.Object;CloseSound=IronSound.Object;}
}

void AColdSteelContactDoor::BeginPlay()
{
    Super::BeginPlay();
    // 接触开门只在服务器判定：远端玩家由服务器模拟代理覆盖到，开门经开合复制回放。
    if(HasAuthority())
        ContactZone->OnComponentBeginOverlap.AddDynamic(this, &AColdSteelContactDoor::HandleContact);
}

void AColdSteelContactDoor::HandleContact(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
    UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
    if(!HasAuthority()||IsDoorOpen())return;
    auto* Pawn=Cast<APawn>(OtherActor);
    // 只对玩家开门；怪物撞门不开（守家口径），也不响应道具/残骸。
    if(!Pawn||!Pawn->IsPlayerControlled())return;
    OpenDoorFrom(Pawn);
}
