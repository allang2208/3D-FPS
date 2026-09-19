#include "ColdSteelFountain.h"
#include "Components/SceneComponent.h"
#include "Components/AudioComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundConcurrency.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    // 资产名按类区分（UBT 的 unity 合并会把同模块的 .cpp 并进一块，匿名命名空间是共享的）。
    const TCHAR* FountainMeshAsset=TEXT("/Game/Props/RomanFountain20260917/PolishV9/SM_FountainPolishedV9.SM_FountainPolishedV9");
    const TCHAR* FountainFxMeshAsset=TEXT("/Game/Props/RomanFountain20260917/SM_RomanFountain_WaterFX.SM_RomanFountain_WaterFX");
    const TCHAR* FountainWaterMeshAsset=TEXT("/Game/Props/RomanFountain20260917/SM_RomanFountain_WaterWaves.SM_RomanFountain_WaterWaves");
    const TCHAR* FountainJetAsset=TEXT("/Niagara/DefaultAssets/Templates/Systems/FountainLightweight.FountainLightweight");
    const TCHAR* FountainOverflowAsset=TEXT("/Game/Props/RomanFountain20260917/OverflowV7/SM_FountainOverflowV7.SM_FountainOverflowV7");
    const TCHAR* FountainSprayAsset=TEXT("/Game/Props/RomanFountain20260917/OverflowV8/NS_FountainLandingSprayV8.NS_FountainLandingSprayV8");
    struct FFountainSprayWorldBudget
    {
        TArray<TWeakObjectPtr<AColdSteelFountain>> Fountains;
        double NextUpdate=-1.0;
        TWeakObjectPtr<USoundConcurrency> BedConcurrency;
        TWeakObjectPtr<USoundConcurrency> DetailConcurrency;
    };
    TMap<TWeakObjectPtr<UWorld>,FFountainSprayWorldBudget> FountainSprayBudgets;

    bool FountainViewLocation(const UWorld* World,FVector& Location)
    {
        if(const APlayerController* PC=World?World->GetFirstPlayerController():nullptr)
        {
            if(PC->PlayerCameraManager)
            {
                Location=PC->PlayerCameraManager->GetCameraLocation();
                return true;
            }
        }
        return false;
    }
    constexpr float FountainJetScale=1.2f;
}

static TAutoConsoleVariable<int32> CVarFountainQuality(
    TEXT("fps.Fountain.Quality"),
    1,
    TEXT("罗马喷泉水效：0=仅盆水，1=默认溢流与飞沫，2=较密飞沫；均遵守距离与实例预算"));

static TAutoConsoleVariable<int32> CVarFountainSprayBudget(
    TEXT("fps.Fountain.MaxSpraySystems"),4,
    TEXT("每个世界近处可见喷泉的附加飞沫系统上限（0..4）；其余保留网格溢流"));

AColdSteelFountain::AColdSteelFountain()
{
    PrimaryActorTick.bCanEverTick=true;
    PrimaryActorTick.TickInterval=0.25f;   // 分级/预算/水声；水帘形变与飞沫不在 CPU 逐帧更新
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
    // 水效网格不进 RT 几何/距离场：它只有几厘米厚、又是半透明，白占常驻显存（截图里的 RT 几何超预算告警）
    WaterFxMesh->bVisibleInRayTracing=false;
    WaterFxMesh->bAffectDistanceFieldLighting=false;

    // 会起伏的水面：独立组件，永远可见（远处只关水膜/水柱，不关水面）
    WaterMesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FountainWater"));
    WaterMesh->SetupAttachment(FountainMesh);
    WaterMesh->SetMobility(EComponentMobility::Movable);
    WaterMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    WaterMesh->SetCanEverAffectNavigation(false);
    WaterMesh->SetCastShadow(false);
    WaterMesh->bVisibleInRayTracing=false;
    WaterMesh->bAffectDistanceFieldLighting=false;
    // 水面靠 WPO 起伏：显式打开 WPO 求值（默认 true，但被关卡/默认值改动过时这里兜底）
    WaterMesh->bEvaluateWorldPositionOffset=true;

    CascadeMesh=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FountainOverflowV7"));
    CascadeMesh->SetupAttachment(FountainMesh);
    CascadeMesh->SetMobility(EComponentMobility::Movable);
    CascadeMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    CascadeMesh->SetCanEverAffectNavigation(false);
    CascadeMesh->SetCastShadow(false);
    CascadeMesh->bVisibleInRayTracing=false;
    CascadeMesh->bAffectDistanceFieldLighting=false;
    CascadeMesh->bEvaluateWorldPositionOffset=true;

    Jet=CreateDefaultSubobject<UNiagaraComponent>(TEXT("FountainJet"));
    Jet->SetupAttachment(FountainMesh);
    Jet->SetMobility(EComponentMobility::Movable);
    Jet->SetRelativeScale3D(FVector(FountainJetScale));
    Jet->SetAutoActivate(false);

    LandingSpray=CreateDefaultSubobject<UNiagaraComponent>(TEXT("FountainLandingSprayV7"));
    LandingSpray->SetupAttachment(FountainMesh);
    LandingSpray->SetMobility(EComponentMobility::Movable);
    LandingSpray->SetAutoActivate(false);
    LandingSpray->SetCastShadow(false);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> MeshAsset(FountainMeshAsset);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> FxAsset(FountainFxMeshAsset);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> WaterAsset(FountainWaterMeshAsset);
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> JetAsset(FountainJetAsset);
    if(MeshAsset.Succeeded())FountainMesh->SetStaticMesh(MeshAsset.Object);
    PolishedFountainMesh=MeshAsset.Object;
    if(FxAsset.Succeeded())WaterFxMesh->SetStaticMesh(FxAsset.Object);
    if(WaterAsset.Succeeded())WaterMesh->SetStaticMesh(WaterAsset.Object);
    if(JetAsset.Succeeded())Jet->SetAsset(JetAsset.Object);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> OverflowAsset(FountainOverflowAsset);
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> SprayAsset(FountainSprayAsset);
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> NearMat(TEXT("/Game/Props/RomanFountain20260917/OverflowV8/M_FountainOverflowNearV8.M_FountainOverflowNearV8"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> FarMat(TEXT("/Game/Props/RomanFountain20260917/OverflowV8/M_FountainOverflowFarV8.M_FountainOverflowFarV8"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> HiddenMat(TEXT("/Game/Props/RomanFountain20260917/Materials/M_FountainHidden.M_FountainHidden"));
    if(OverflowAsset.Succeeded())CascadeMesh->SetStaticMesh(OverflowAsset.Object);
    if(NearMat.Succeeded())CascadeMesh->SetMaterial(0,NearMat.Object);
    if(SprayAsset.Succeeded())LandingSpray->SetAsset(SprayAsset.Object);
    CascadeNearMaterial=NearMat.Object;
    CascadeFarMaterial=FarMat.Object;
    HiddenCascadeMaterial=HiddenMat.Object;
    if(OverflowAsset.Succeeded()&&HiddenMat.Succeeded())WaterFxMesh->SetMaterial(2,HiddenMat.Object);

    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Stone(TEXT("/Game/Props/RomanFountain20260917/PolishV9/MIC_FountainStoneV9.MIC_FountainStoneV9"));
    PolishedStoneMaterial=Stone.Object;
    // The shared default is resolved below; explicit alternative build surfaces remain supported.
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> OriginalStone(TEXT("/Game/Props/RomanColumn20260915/M_RomanStone_V2.M_RomanStone_V2"));
    OriginalStoneMaterial=OriginalStone.Object;
    WaterLoop=CreateDefaultSubobject<UAudioComponent>(TEXT("FountainWaterLoop"));
    CloseWaterLoop=CreateDefaultSubobject<UAudioComponent>(TEXT("FountainCloseWaterLoop"));
    for(UAudioComponent* Audio:{WaterLoop.Get(),CloseWaterLoop.Get()})
    {
        Audio->SetupAttachment(FountainMesh);
        Audio->SetAutoActivate(false);
        Audio->bAutoDestroy=false;
        Audio->bStopWhenOwnerDestroyed=true;
        Audio->bOverrideAttenuation=true;
    }
    static ConstructorHelpers::FObjectFinder<USoundBase> Bed(TEXT("/Game/Props/RomanFountain20260917/PolishV9/Audio/S_FountainBed_LoopV9.S_FountainBed_LoopV9"));
    static ConstructorHelpers::FObjectFinder<USoundBase> Detail(TEXT("/Game/Props/RomanFountain20260917/PolishV9/Audio/S_FountainDetail_LoopV9.S_FountainDetail_LoopV9"));
    WaterLoop->SetSound(Bed.Object);
    CloseWaterLoop->SetSound(Detail.Object);
}

void AColdSteelFountain::BeginPlay()
{
    Super::BeginPlay();
    // Existing level components can serialize the earlier default mesh/material.
    if(PolishedFountainMesh&&FountainMesh->GetStaticMesh()&&
       FountainMesh->GetStaticMesh()->GetPathName()==TEXT("/Game/Props/RomanFountain20260917/SM_RomanFountain_20.SM_RomanFountain_20"))
        FountainMesh->SetStaticMesh(PolishedFountainMesh);
    Configure(FountainMesh->GetMaterial(0));
    AlignGeometry();
    if(GetNetMode()==NM_DedicatedServer)
    {
        SetActorTickEnabled(false);
        return;
    }
    // Instance overrides retire only the old curtain; basin assets and FX slots
    // 0/1/3 are unchanged. Saved instances receive the same override at BeginPlay.
    if(CascadeMesh->GetStaticMesh()&&HiddenCascadeMaterial)WaterFxMesh->SetMaterial(2,HiddenCascadeMaterial);
    const float Phase=static_cast<float>(GetUniqueID()%997)*0.173f;
    LandingSpray->SetVariableFloat(TEXT("User.FountainSeed"),Phase);
    if(CascadeNearMaterial)
    {
        CascadeNearInstance=UMaterialInstanceDynamic::Create(CascadeNearMaterial,this);
        CascadeNearInstance->SetScalarParameterValue(TEXT("InstancePhase"),Phase);
    }
    if(CascadeFarMaterial)
    {
        CascadeFarInstance=UMaterialInstanceDynamic::Create(CascadeFarMaterial,this);
        CascadeFarInstance->SetScalarParameterValue(TEXT("InstancePhase"),Phase);
    }
    FountainSprayBudgets.FindOrAdd(GetWorld()).Fountains.AddUnique(this);
    ApplyFxQuality();
    InitializeLoopAudio();
    UpdateLoopAudio();
    // 运行期一次性自证：这台喷泉实际在渲染哪些网格/材质（排查"看着没变化"时按这行日志对账）
    const auto Describe=[](const UStaticMeshComponent* Comp)->FString
    {
        if(!Comp)return FString(TEXT("null"));
        const UStaticMesh* Mesh=Comp->GetStaticMesh();
        const UMaterialInterface* Mat=Comp->GetMaterial(0);
        FString Out=Comp->GetName();
        Out+=TEXT("{")+(Mesh?Mesh->GetName():FString(TEXT("none")));
        Out+=TEXT("|mat:")+(Mat?Mat->GetName():FString(TEXT("none")));
        Out+=FString::Printf(TEXT("|vis:%d}"),Comp->IsVisible()?1:0);
        return Out;
    };
    UE_LOG(LogTemp,Display,
        TEXT("ColdSteelFountain %s 位置=(%.0f,%.0f,%.0f) 质量=%d 距离档=%d 组件: Main=%s Water=%s Fx=%s Jet=%s"),
        *GetName(),GetActorLocation().X,GetActorLocation().Y,GetActorLocation().Z,
        CachedQuality,CachedTier,*Describe(FountainMesh),*Describe(WaterMesh),*Describe(WaterFxMesh),
        Jet?*Jet->GetName():TEXT("null"));
}

void AColdSteelFountain::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    SetSprayBudget(false,0.f);
    if(WaterLoop)WaterLoop->Stop();
    if(CloseWaterLoop)CloseWaterLoop->Stop();
    if(FFountainSprayWorldBudget* Budget=FountainSprayBudgets.Find(GetWorld()))
    {
        Budget->Fountains.RemoveAll([this](const TWeakObjectPtr<AColdSteelFountain>& F){return !F.IsValid()||F.Get()==this;});
        Budget->NextUpdate=-1.0;
        if(Budget->Fountains.IsEmpty())FountainSprayBudgets.Remove(GetWorld());
    }
    Super::EndPlay(EndPlayReason);
}

void AColdSteelFountain::Configure(UMaterialInterface* Surface)
{
    // 只覆盖大理石槽：水／泡沫／溢流／焦散都是自带实例，换材质行不该把水一起换掉。
    if(Surface&&FountainMesh)
        FountainMesh->SetMaterial(0,Surface==OriginalStoneMaterial&&PolishedStoneMaterial?PolishedStoneMaterial.Get():Surface);
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
    if(Quality!=CachedQuality)
    {
        CachedQuality=Quality;
        CachedTier=INDEX_NONE;   // 质量变了要重算距离档
    }
    ApplyTier(Quality<1?3:ComputeTier());
    // Fade the extra noise octave before switching to the one-sample far material.
    // Both materials share their coarse flow field, so water bundles stay in place.
    if(CascadeNearInstance&&CachedTier<2)
    {
        FVector View;
        if(FountainViewLocation(GetWorld(),View))
        {
            const float Start=(NearDetailDistanceCm+SprayEndDistanceCm)*.5f;
            const float Detail=FMath::Clamp((SprayEndDistanceCm-FVector::Dist(View,GetActorLocation()))/
                FMath::Max(1.f,SprayEndDistanceCm-Start),0.f,1.f);
            CascadeNearInstance->SetScalarParameterValue(TEXT("FlowDetail"),Detail);
        }
    }
    if(Quality<1||CachedTier>=2)SetSprayBudget(false,0.f);
    RefreshSprayBudgets(GetWorld());
}

int32 AColdSteelFountain::ComputeTier() const
{
    FVector View;
    if(!FountainViewLocation(GetWorld(),View))return 3;
    const float Dist=FVector::Dist(View,GetActorLocation());
    if(Dist<=NearDetailDistanceCm)return 0;
    if(Dist<=SprayEndDistanceCm)return 1;
    if(Dist<=MidJetDistanceCm)return 2;
    return 3;
}

void AColdSteelFountain::ApplyTier(int32 Tier)
{
    if(Tier==CachedTier)return;
    CachedTier=Tier;
    const bool bExtras=Tier<3;
    if(WaterFxMesh)WaterFxMesh->SetVisibility(bExtras,true);
    if(CascadeMesh)
    {
        CascadeMesh->SetVisibility(bExtras,true);
        UMaterialInterface* Material=Tier<2?static_cast<UMaterialInterface*>(CascadeNearInstance.Get()):static_cast<UMaterialInterface*>(CascadeFarInstance.Get());
        if(Material)CascadeMesh->SetMaterial(0,Material);
    }
    if(Jet)
    {
        if(bExtras&&!Jet->IsActive())Jet->Activate(true);
        else if(!bExtras&&Jet->IsActive())Jet->DeactivateImmediate();
    }
}

void AColdSteelFountain::SetSprayBudget(bool bGranted,float DistanceCm)
{
    if(!LandingSpray)return;
    const float Fade=FMath::Clamp((SprayEndDistanceCm-DistanceCm)/FMath::Max(1.f,SprayEndDistanceCm-NearDetailDistanceCm),0.f,1.f);
    const float Rate=bGranted?(CachedQuality>=2?480.f:360.f)*Fade:0.f;
    const bool bActive=Rate>1.f&&LandingSpray->GetAsset()!=nullptr;
    if(!FMath::IsNearlyEqual(Rate,CachedSprayRate,.5f))
    {
        LandingSpray->SetVariableFloat(TEXT("User.SpawnRate"),Rate);
        CachedSprayRate=Rate;
    }
    if(bActive!=bSprayBudgetGranted)
    {
        bSprayBudgetGranted=bActive;
        if(bActive)LandingSpray->Activate(true);
        else LandingSpray->DeactivateImmediate();
    }
}

void AColdSteelFountain::RefreshSprayBudgets(UWorld* World)
{
    FFountainSprayWorldBudget* Budget=World?FountainSprayBudgets.Find(World):nullptr;
    if(!Budget||World->GetTimeSeconds()<Budget->NextUpdate)return;
    Budget->NextUpdate=World->GetTimeSeconds()+.25;
    Budget->Fountains.RemoveAll([](const TWeakObjectPtr<AColdSteelFountain>& F){return !F.IsValid();});
    FVector View;
    const bool bHasView=FountainViewLocation(World,View);
    struct FCandidate { AColdSteelFountain* Fountain; float Distance; };
    TArray<FCandidate,TInlineAllocator<16>> Candidates;
    for(const TWeakObjectPtr<AColdSteelFountain>& Weak:Budget->Fountains)
    {
        AColdSteelFountain* F=Weak.Get();
        if(!bHasView||!F||F->CachedQuality<1||F->IsHidden()||!F->IsActorTickEnabled())continue;
        const float Distance=FVector::Dist(View,F->GetActorLocation());
        if(Distance>=F->SprayEndDistanceCm)continue;
        if(!F->CascadeMesh->WasRecentlyRendered(.75f))continue;
        Candidates.Add({F,Distance});
    }
    Candidates.Sort([](const FCandidate& A,const FCandidate& B)
    {
        return A.Distance==B.Distance?A.Fountain->GetUniqueID()<B.Fountain->GetUniqueID():A.Distance<B.Distance;
    });
    const int32 Count=FMath::Min(Candidates.Num(),FMath::Clamp(CVarFountainSprayBudget.GetValueOnGameThread(),0,4));
    // Revoke before granting so changing the nearest four never creates a transient
    // fifth live system. Unchanged winners keep their particles and emission phase.
    for(const TWeakObjectPtr<AColdSteelFountain>& Weak:Budget->Fountains)
    {
        AColdSteelFountain* F=Weak.Get();
        bool bSelected=false;
        for(int32 I=0;I<Count;++I)bSelected|=Candidates[I].Fountain==F;
        if(F&&!bSelected)F->SetSprayBudget(false,0.f);
    }
    for(int32 I=0;I<Count;++I)Candidates[I].Fountain->SetSprayBudget(true,Candidates[I].Distance);
}

void AColdSteelFountain::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    ApplyFxQuality();
    UpdateLoopAudio();
}

void AColdSteelFountain::InitializeLoopAudio()
{
    FFountainSprayWorldBudget& Budget=FountainSprayBudgets.FindChecked(GetWorld());
    const auto Setup=[this](UAudioComponent* Audio,TWeakObjectPtr<USoundConcurrency>& Shared,float Radius,float Height,float Gain)
    {
        if(!Shared.IsValid())
        {
            USoundConcurrency* Concurrency=NewObject<USoundConcurrency>(GetWorld());
            Concurrency->Concurrency.SetMaxCount(4);
            Concurrency->Concurrency.ResolutionRule=EMaxConcurrentResolutionRule::StopFarthestThenPreventNew;
            Concurrency->Concurrency.VoiceStealReleaseTime=.7f;
            Shared=Concurrency;
        }
        Audio->ConcurrencySet.Add(Shared.Get());
        Audio->SetRelativeLocation(FVector(0.f,0.f,Height));
        Audio->SetVolumeMultiplier(AudioVolume*Gain);
        FSoundAttenuationSettings& Attenuation=Audio->AttenuationOverrides;
        Attenuation.bAttenuate=true;
        Attenuation.bSpatialize=true;
        Attenuation.DistanceAlgorithm=EAttenuationDistanceModel::NaturalSound;
        Attenuation.AttenuationShape=EAttenuationShape::Sphere;
        Attenuation.AttenuationShapeExtents=FVector(450.f,0.f,0.f);
        Attenuation.FalloffDistance=FMath::Max(1.f,Radius-450.f);
        Attenuation.bAttenuateWithLPF=true;
        Attenuation.LPFRadiusMin=450.f;
        Attenuation.LPFRadiusMax=Radius;
        Attenuation.LPFFrequencyAtMin=20000.f;
        Attenuation.LPFFrequencyAtMax=3500.f;
    };
    Setup(WaterLoop,Budget.BedConcurrency,AudioRadiusCm,AudioHeightCm,.8f);
    Setup(CloseWaterLoop,Budget.DetailConcurrency,1600.f,AudioHeightCm+90.f,.5f);
}

void AColdSteelFountain::UpdateLoopAudio()
{
    FVector View;
    const bool bAudible=bEnableAudio&&CachedQuality>0&&!IsHidden()&&FountainViewLocation(GetWorld(),View);
    const double Now=GetWorld()->GetTimeSeconds();
    const float Phase=static_cast<float>(GetUniqueID()%997)*.173f;
    const auto Update=[&](UAudioComponent* Audio,float Radius,float Offset,bool& bWasWanted,double& NextAttempt)
    {
        // Offscreen water still sounds. Hysteresis prevents boundary oscillation;
        // actual falloff and filtering are processed continuously by the mixer.
        const bool bWanted=bAudible&&FVector::DistSquared(View,Audio->GetComponentLocation())<FMath::Square(Radius+(bWasWanted?200.f:0.f));
        if(!bWanted)
        {
            if(bWasWanted&&Audio->IsPlaying())Audio->FadeOut(1.f,0.f);
            bWasWanted=false;
            return;
        }
        if(!bWasWanted&&Audio->GetPlayState()==EAudioComponentPlayState::FadingOut)
            Audio->AdjustVolume(.8f,1.f);
        bWasWanted=true;
        if(Audio->IsPlaying()||Now<NextAttempt)return;
        NextAttempt=Now+1.; // Concurrency-denied/stolen voices retry at most once a second.
        if(USoundBase* Sound=Audio->Sound)
        {
            const float Start=FMath::Fmod(static_cast<float>(Now)+Phase+Offset,FMath::Max(.01f,Sound->Duration));
            Audio->FadeIn(.9f,1.f,Start);
        }
    };
    Update(WaterLoop,AudioRadiusCm,0.f,bBedLoopWanted,NextBedLoopAttempt);
    Update(CloseWaterLoop,1600.f,3.37f,bDetailLoopWanted,NextDetailLoopAttempt);
}
