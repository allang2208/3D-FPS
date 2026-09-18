#include "ColdSteelFountain.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    // 资产名按类区分（UBT 的 unity 合并会把同模块的 .cpp 并进一块，匿名命名空间是共享的）。
    const TCHAR* FountainMeshAsset=TEXT("/Game/Props/RomanFountain20260917/SM_RomanFountain_20.SM_RomanFountain_20");
    const TCHAR* FountainFxMeshAsset=TEXT("/Game/Props/RomanFountain20260917/SM_RomanFountain_WaterFX.SM_RomanFountain_WaterFX");
    const TCHAR* FountainJetAsset=TEXT("/Niagara/DefaultAssets/Templates/Systems/FountainLightweight.FountainLightweight");
    // 占位水声：项目里唯一与水相关的现成音频（全量盘点过，没有水流循环声）。
    const TCHAR* FountainSplash1=TEXT("/Game/Audio/FreeFootsteps/S_splash1.S_splash1");
    const TCHAR* FountainSplash2=TEXT("/Game/Audio/FreeFootsteps/S_splash2.S_splash2");
    const TCHAR* FountainSplashDeep=TEXT("/Game/Audio/FreeFootsteps/S_splash1_deep.S_splash1_deep");
    constexpr float FountainJetScale=1.2f;
}

static TAutoConsoleVariable<int32> CVarFountainQuality(
    TEXT("fps.Fountain.Quality"),
    1,
    TEXT("罗马喷泉附加水效质量：0=只留水面材质，1=默认（水膜/溢流网格 + 塔尖水柱 + 占位水声），2=预留"));

AColdSteelFountain::AColdSteelFountain()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickInterval=0.25f;   // 只用来读 CVar 与占位水声计时
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("FountainRoot")));

    FountainMesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FountainMesh"));
    FountainMesh->SetupAttachment(GetRootComponent());
    FountainMesh->SetMobility(EComponentMobility::Movable);
    FountainMesh->SetCollisionProfileName(TEXT("BlockAll"));
    FountainMesh->SetCanEverAffectNavigation(false);

    // 水膜/溢流网格挂在主网格之下：两者共用同一物体空间，主网格一贴地它就跟着对齐。
    WaterFxMesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FountainWaterFx"));
    WaterFxMesh->SetupAttachment(FountainMesh);
    WaterFxMesh->SetMobility(EComponentMobility::Movable);
    WaterFxMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    WaterFxMesh->SetCanEverAffectNavigation(false);
    WaterFxMesh->SetCastShadow(false);

    Jet=CreateDefaultSubobject<UNiagaraComponent>(TEXT("FountainJet"));
    Jet->SetupAttachment(FountainMesh);
    Jet->SetMobility(EComponentMobility::Movable);
    Jet->SetRelativeScale3D(FVector(FountainJetScale));

    static ConstructorHelpers::FObjectFinder<UStaticMesh> MeshAsset(FountainMeshAsset);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> FxAsset(FountainFxMeshAsset);
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> JetAsset(FountainJetAsset);
    if(MeshAsset.Succeeded())FountainMesh->SetStaticMesh(MeshAsset.Object);
    if(FxAsset.Succeeded())WaterFxMesh->SetStaticMesh(FxAsset.Object);
    if(JetAsset.Succeeded())Jet->SetAsset(JetAsset.Object);

    static ConstructorHelpers::FObjectFinder<USoundBase> Splash1(FountainSplash1);
    static ConstructorHelpers::FObjectFinder<USoundBase> Splash2(FountainSplash2);
    static ConstructorHelpers::FObjectFinder<USoundBase> SplashDeep(FountainSplashDeep);
    if(Splash1.Succeeded())SplashCues.Add(Splash1.Object);
    if(Splash2.Succeeded())SplashCues.Add(Splash2.Object);
    if(SplashDeep.Succeeded())SplashCues.Add(SplashDeep.Object);
}

void AColdSteelFountain::BeginPlay()
{
    Super::BeginPlay();
    AlignGeometry();
    ApplyFxQuality();
    AudioCountdown=FMath::FRandRange(AudioMinInterval,AudioMaxInterval);
}

void AColdSteelFountain::Configure(UMaterialInterface* Surface)
{
    // 只覆盖大理石槽：水／泡沫／溢流／焦散都是自带实例，换材质行不该把水一起换掉。
    if(Surface&&FountainMesh)FountainMesh->SetMaterial(0,Surface);
}

void AColdSteelFountain::AlignGeometry()
{
    if(const UStaticMesh* Mesh=FountainMesh?FountainMesh->GetStaticMesh():nullptr)
    {
        const FBoxSphereBounds Bounds=Mesh->GetBounds();
        // 包围盒底面对齐 Actor 原点（构件锚点＝占格底面中心），X／Y 居中；与门的 AlignGeometry 同一口径。
        FountainMesh->SetRelativeLocation(FVector(-Bounds.Origin.X,-Bounds.Origin.Y,Bounds.BoxExtent.Z-Bounds.Origin.Z));
        if(Jet)
        {
            // 塔尖 = 包围盒顶面中心（网格 pivot 在底面／中心都不影响）。
            Jet->SetRelativeLocation(FVector(0.f,0.f,Bounds.BoxExtent.Z*2.f));
        }
    }
}

void AColdSteelFountain::ApplyFxQuality()
{
    const int32 Quality=FMath::Clamp(CVarFountainQuality.GetValueOnGameThread(),0,2);
    if(Quality==CachedQuality)return;
    CachedQuality=Quality;
    const bool bFx=Quality>=1;
    if(WaterFxMesh)WaterFxMesh->SetVisibility(bFx,false);
    if(Jet)
    {
        if(bFx)Jet->Activate(true);
        else Jet->Deactivate();
    }
}

void AColdSteelFountain::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    ApplyFxQuality();
    if(!bEnableAudio||CachedQuality<1||SplashCues.Num()==0)return;
    AudioCountdown-=DeltaSeconds;
    if(AudioCountdown>0.f)return;
    AudioCountdown=FMath::FRandRange(AudioMinInterval,AudioMaxInterval);
    const UWorld* World=GetWorld();
    if(!World)return;
    const APawn* Pawn=UGameplayStatics::GetPlayerPawn(World,0);
    if(!Pawn)return;
    if(FVector::DistSquared(Pawn->GetActorLocation(),GetActorLocation())>FMath::Square(AudioRadiusCm))return;
    if(USoundBase* Cue=SplashCues[FMath::RandRange(0,SplashCues.Num()-1)])
    {
        UGameplayStatics::PlaySoundAtLocation(this,Cue,GetActorLocation()+FVector(0.f,0.f,AudioHeightCm),
            AudioVolume,1.f+FMath::FRandRange(-0.08f,0.08f));
    }
}
