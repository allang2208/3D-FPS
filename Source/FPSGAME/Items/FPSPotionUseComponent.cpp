#include "FPSPotionUseComponent.h"
#include "PotionVisuals.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Movement/FPSTraversalRules.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Sound/SoundBase.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "EngineGlobals.h"

UFPSPotionUseComponent::UFPSPotionUseComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
bool UFPSPotionUseComponent::IsPotion(const FString& Definition)
{
    return Definition==TEXT("hp_potion")||Definition.StartsWith(TEXT("hp_potion_"))||
        Definition==TEXT("mp_potion")||Definition.StartsWith(TEXT("mp_potion_"));
}
bool UFPSPotionUseComponent::IsDrink(const FString& Definition)
{
    return IsPotion(Definition)||Definition==TEXT("mineral_water")||Definition==TEXT("soda_can");
}
bool UFPSPotionUseComponent::IsFood(const FString& Definition)
{
    return Definition==TEXT("baguette_bread")||Definition==TEXT("bread");
}
bool UFPSPotionUseComponent::IsAnimatedConsumable(const FString& Definition)
{
    return IsDrink(Definition)||IsFood(Definition);
}
void UFPSPotionUseComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    if(auto* Bow=GetOwner()->FindComponentByClass<UBowWeaponComponent>())AddTickPrerequisiteComponent(Bow);
    HealthMotion.Load(false);ManaMotion.Load(true);WaterMotion.Load(false,TEXT("mineral_water"));
    FoodMotion.Load(false,TEXT("baguette_bread"));
    BreadMotion.Load(false,TEXT("bread"));
    SodaMotion.Load(false,TEXT("soda_can"));
    TArray<FSoftObjectPath> Paths;
    for(const auto& Tier:PotionVisuals::Tiers())
    {
        Paths.Add(FSoftObjectPath(Tier.Shell));Paths.Add(FSoftObjectPath(Tier.Liquid));Paths.Add(FSoftObjectPath(Tier.Stopper));
    }
    const int32 MeshCount=Paths.Num();
    Paths.Add(FSoftObjectPath(PotionVisuals::LiquidMaterial(false)));
    Paths.Add(FSoftObjectPath(PotionVisuals::LiquidMaterial(true)));
    for(const auto& Tier:PotionVisuals::Tiers())
        Paths.Add(FSoftObjectPath(Tier.LiquidMaterial.IsEmpty()?PotionVisuals::LiquidMaterial(false):Tier.LiquidMaterial));
    const int32 FoodIndex=Paths.Num();
    Paths.Add(FSoftObjectPath(TEXT("/Game/Items/Consumables/Baguette20261003/SM_Baguette.SM_Baguette")));
    Paths.Add(FSoftObjectPath(TEXT("/Game/Items/Consumables/Bread20261003/SM_Bread.SM_Bread")));
    Paths.Add(FSoftObjectPath(TEXT("/Game/Items/Consumables/SodaCan20261003/SM_SodaCan.SM_SodaCan")));
    const int32 AudioIndex=Paths.Num();
    Paths.Add(FSoftObjectPath(TEXT("/Game/Audio/Consumables20261003/S_WaterSwallow_01.S_WaterSwallow_01")));
    Paths.Add(FSoftObjectPath(TEXT("/Game/Audio/Consumables20261003/S_WaterSwallow_02.S_WaterSwallow_02")));
    Paths.Add(FSoftObjectPath(TEXT("/Game/Audio/Consumables20261003/S_WaterSwallow_03.S_WaterSwallow_03")));
    Paths.Add(FSoftObjectPath(TEXT("/Game/Audio/Consumables20261003/S_FoodSwallow.S_FoodSwallow")));
    LoadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Paths,MeshCount,FoodIndex,AudioIndex]()
    {
        Assets.Reset();LiquidMaterials.Reset();
        for(int32 I=0;I<MeshCount;++I)Assets.Add(Cast<UStaticMesh>(Paths[I].ResolveObject()));
        for(int32 I=MeshCount;I<FoodIndex;++I)LiquidMaterials.Add(Cast<UMaterialInterface>(Paths[I].ResolveObject()));
        FoodMesh=Cast<UStaticMesh>(Paths[FoodIndex].ResolveObject());
        BreadMesh=Cast<UStaticMesh>(Paths[FoodIndex+1].ResolveObject());
        SodaMesh=Cast<UStaticMesh>(Paths[FoodIndex+2].ResolveObject());
        WaterSwallowSounds.Reset();
        for(int32 I=AudioIndex;I<AudioIndex+3;++I)
            if(auto* Sound=Cast<USoundBase>(Paths[I].ResolveObject()))WaterSwallowSounds.Add(Sound);
        FoodSwallowSound=Cast<USoundBase>(Paths[AudioIndex+3].ResolveObject());
    }));
    auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    SwallowAudio=NewObject<UAudioComponent>(GetOwner(),TEXT("ConsumableSwallowAudio"));
    GetOwner()->AddInstanceComponent(SwallowAudio);SwallowAudio->SetupAttachment(Camera);
    SwallowAudio->SetAutoActivate(false);SwallowAudio->bAutoDestroy=false;
    SwallowAudio->bAllowSpatialization=false;SwallowAudio->bIsUISound=false;
    SwallowAudio->bStopWhenOwnerDestroyed=true;SwallowAudio->RegisterComponent();
    const auto MakePart=[&](const TCHAR* Name)
    {
        auto* Part=NewObject<UStaticMeshComponent>(GetOwner(),Name);GetOwner()->AddInstanceComponent(Part);
        Part->SetupAttachment(Camera);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetCanEverAffectNavigation(false);Part->SetCastShadow(false);Part->SetOnlyOwnerSee(true);
        Part->bReceivesDecals=false;Part->SetVisibility(false);Part->RegisterComponent();return Part;
    };
    Bottle=MakePart(TEXT("HeldPotionBottle"));Liquid=MakePart(TEXT("HeldPotionLiquid"));Stopper=MakePart(TEXT("HeldPotionStopper"));
    FallbackHands=NewObject<UFPSCastingMeshComponent>(GetOwner(),TEXT("PotionFallbackLeftArm"));
    GetOwner()->AddInstanceComponent(FallbackHands);FallbackHands->SetupAttachment(Camera);
    FallbackHands->SetRelativeRotation(FRotator(0,90,0));
    FallbackHands->SetSkeletalMesh(GetDefault<UFPSTraversalSettings>()->ArmsMesh.LoadSynchronous());
    FallbackHands->SetCollisionEnabled(ECollisionEnabled::NoCollision);FallbackHands->SetCanEverAffectNavigation(false);
    FallbackHands->SetCastShadow(false);FallbackHands->SetOnlyOwnerSee(true);FallbackHands->SetVisibility(false);
    FallbackHands->RegisterComponent();FallbackHands->SetComponentTickEnabled(false);
    FallbackHands->HideBoneByName(TEXT("clavicle_r"),EPhysBodyOp::PBO_None);
}
bool UFPSPotionUseComponent::TryBegin(const FString& ItemId,const FString& Definition)
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Player||!Player->IsLocallyControlled()||!Model||!Bottle||!IsAnimatedConsumable(Definition))return false; // M2: 联机放开（本地档案→通道上行）
    if(bActive){Model->Message=bFood?TEXT("正在进食"):TEXT("正在饮用");return false;}
    // Held equipment yields through a lower/use/raise presentation. Active
    // attacks, reloads and spells still own the hand until their action ends.
    if(!Player->CanBeginConsumableUse())
    {Model->Message=TEXT("左手当前被占用");return false;}
    const bool bMana=Definition.StartsWith(TEXT("mp_"));
    const bool Water=Definition==TEXT("mineral_water");
    const bool Food=IsFood(Definition);
    const bool Soda=Definition==TEXT("soda_can");
    const bool Solid=Food||Soda;
    UStaticMesh* SolidVisual=Soda?SodaMesh.Get():(Definition==TEXT("bread")?BreadMesh.Get():FoodMesh.Get());
    const int32 TierIndex=Solid?INDEX_NONE:PotionVisuals::FindTier(Definition);
    if(!Solid&&TierIndex==INDEX_NONE){Model->Message=TEXT("饮用瓶型尚未配置");return false;}
    const int32 Base=Solid?0:TierIndex*3;
    FPotionTierVisual Visual;
    if(Solid)
    {
        if(!SolidVisual){Model->Message=Soda?TEXT("汽水模型正在加载"):TEXT("食物模型正在加载");return false;}
        Visual.GripHeightCm=SolidVisual->GetBounds().Origin.Z;
    }
    else Visual=PotionVisuals::Tiers()[TierIndex];
    const int32 MaterialIndex=Visual.LiquidMaterial.IsEmpty()?(bMana?1:0):TierIndex+2;
    if(Water)
    {
        // Resolve this drink's own parts at use time. A failed preload must not
        // leave an imported bottle permanently unavailable in this pawn.
        if(Assets.Num()<Base+3)Assets.SetNum(Base+3);
        Assets[Base]=Cast<UStaticMesh>(FSoftObjectPath(Visual.Shell).TryLoad());
        Assets[Base+1]=Cast<UStaticMesh>(FSoftObjectPath(Visual.Liquid).TryLoad());
        Assets[Base+2]=Cast<UStaticMesh>(FSoftObjectPath(Visual.Stopper).TryLoad());
        if(LiquidMaterials.Num()<=MaterialIndex)LiquidMaterials.SetNum(MaterialIndex+1);
        LiquidMaterials[MaterialIndex]=Cast<UMaterialInterface>(FSoftObjectPath(Visual.LiquidMaterial).TryLoad());
    }
    if(!Solid&&(!Assets.IsValidIndex(Base+2)||!Assets[Base]||!Assets[Base+1]||!Assets[Base+2]||
        !LiquidMaterials.IsValidIndex(MaterialIndex)||!LiquidMaterials[MaterialIndex]))
    {
        Model->Message=Water?TEXT("矿泉水模型加载失败"):TEXT("饮用动作资源正在加载");
        if(Water)UE_LOG(LogTemp,Warning,TEXT("MineralWater visual load failed: shell=%s liquid=%s cap=%s material=%s"),
            *Visual.Shell,*Visual.Liquid,*Visual.Stopper,*Visual.LiquidMaterial);
        return false;
    }
    // Bottle geometry is shared by HP/MP. Keep a common grasp and the existing
    // mouth-to-hand distance; height differences move only the bottle's bottom.
    Motion=Food?(Definition==TEXT("bread")?BreadMotion:FoodMotion):(Soda?SodaMotion:(Water?WaterMotion:HealthMotion));
    Motion.GripHeight=Visual.GripHeightCm;
    if(Motion.Keys.IsEmpty()){Model->Message=TEXT("消耗品动作尚未加载");return false;}
    // Resolve ownership, not visibility: the inventory temporarily hides native
    // sword/tool/staff arms, which return as soon as the menu closes.
    auto* NativeHands=Player->ConsumableHands();
    auto* UseHands=NativeHands?Cast<UFPSCastingMeshComponent>(NativeHands):FallbackHands.Get();
    if(!UseHands || !UseHands->GetSkeletalMeshAsset() || !UseHands->bApplyLeftHandCast || UseHands->GetBoneIndex(TEXT("hand_l"))<0)
    {Model->Message=TEXT("消耗品手部动作资源正在加载");return false;}
    // Closing the inventory clears its Selected string, which may be ItemId's
    // caller-owned storage. Keep the instance identity through contact settlement.
    const FString PendingItemId=ItemId;
    auto* PC=Cast<AFPSGAMEPlayerController>(Player->GetController());
    if(PC&&PC->GetColdSteelHUD()&&PC->GetColdSteelHUD()->IsInventoryOpen())PC->GetColdSteelHUD()->ToggleInventory();
    if(AFPSGAMEPlayerController::BlocksOngoingActions(PC))return false;
    Player->PrepareForConsumableUse();
    Bottle->SetStaticMesh(Solid?SolidVisual:Assets[Base].Get());
    if(!Solid)
    {
        Liquid->SetStaticMesh(Assets[Base+1]);Stopper->SetStaticMesh(Assets[Base+2]);
        Liquid->SetMaterial(0,LiquidMaterials[MaterialIndex]);
    }
    bFood=Food;bWater=Water;bSoda=Soda;LastWaterLevel=-1.f;WaterMaterial=nullptr;
    if(bWater)
    {
        const auto* Item=Model->FindItem(PendingItemId);if(!Item)return false;
        const int32 Uses=FMath::Clamp(int32(ColdSteelInventory::Number(*Item,TEXT("remainingUses"),2)),1,2);
        WaterStartFill=Uses*.5f;WaterEndFill=(Uses-1)*.5f;
        WaterBottomCm=Visual.LiquidBottomCm;WaterFullCm=Visual.LiquidFullCm;
        WaterMaterial=UMaterialInstanceDynamic::Create(LiquidMaterials[MaterialIndex],this);
        Liquid->SetMaterial(0,WaterMaterial);
    }
    StopSwallowAudio();bSwallowStarted=false;
    UsingItem=PendingItemId;PresentationDefinition=*Definition;++PresentationSerial;
    bStowOffhand=Player->HasOffhandPistol();
    bCommitted=bUncapped=bDiscarded=false;
    // Keep every authored contact/audio/release time relative to actual use;
    // the leading equipment transition must never consume the item early.
    StartTime=GetWorld()->GetTimeSeconds()+(bStowOffhand?OffhandLowerSeconds:0.f);
    ArmPose.Reset();ActiveHands=UseHands;LastHandPoseFrame=MAX_uint64;
    if(ActiveHands.IsValid())AddTickPrerequisiteComponent(ActiveHands.Get());
    bActive=true;SetComponentTickEnabled(true);Model->Message=bFood?(Definition==TEXT("bread")?TEXT("食用普通面包"):TEXT("食用法棍面包")):(bWater?TEXT("饮用矿泉水"):(bSoda?TEXT("饮用汽水"):TEXT("饮用药水")));return true;
}
float UFPSPotionUseComponent::Age() const{return bActive?float(GetWorld()->GetTimeSeconds()-StartTime):0.f;}
float UFPSPotionUseComponent::OffhandLowerWeight() const
{
    if(!IsStowingOffhand())return 0.f;
    const float T=Age();
    return FPotionUseMotion::Ease((T+OffhandLowerSeconds)/OffhandLowerSeconds)*
        (1.f-FPotionUseMotion::Ease((T-Motion.Duration)/OffhandRaiseSeconds));
}
bool UFPSPotionUseComponent::IsOffhandWeaponHidden() const
{
    if(!IsStowingOffhand())return false;
    const float T=Age();
    return T>=0.f&&T<Motion.Duration;
}
void UFPSPotionUseComponent::ApplyHandPose(UFPSCastingMeshComponent& Mesh)
{
    if(!bActive||ActiveHands.Get()!=&Mesh)return;
    const float T=Age();
    // Keep the original equipped grasp while lowering/raising the entire rig.
    // Only the use phase takes over the native arm and fingers.
    if(T<0.f||T>=Motion.Duration){LastHandPoseFrame=GFrameCounter;return;}
    FTransform PalmWorld;
    if(ArmPose.Apply(Mesh,Motion,T,PalmWorld))
    {
        LastHandPoseFrame=GFrameCounter;
        UpdateBottle(PalmWorld);
    }
}
void UFPSPotionUseComponent::UpdateBottle(const FTransform& PalmWorld)
{
    const float T=Age();
    // Follow the solved hand (including this rig's entry blend), never a socket
    // from the previous frame or an independently animated bottle trajectory.
    const FQuat Upright=FRotationMatrix::MakeFromXZ(FVector::ForwardVector,FVector::RightVector).ToQuat();
    const FQuat Rotation=PalmWorld.GetRotation()*Upright.Inverse();
    const FVector Grip=PalmWorld.TransformPosition(Motion.GripInPalm);
    const FTransform World(Rotation,Grip-Rotation.RotateVector(FVector(0,0,Motion.GripHeight)));
    const bool Show=T>=Motion.Grab&&T<Motion.Release&&!bDiscarded;
    Bottle->SetWorldTransform(World);Bottle->SetVisibility(Show);
    if(bFood||bSoda)
    {
        Liquid->SetVisibility(false);Stopper->SetVisibility(false);
        return;
    }
    if(bWater)
    {
        // The same solved palm carries the bottle, cap and liquid. Collapse the
        // cavity's upper rings onto the fill plane, without narrowing the water.
        const float Progress=bCommitted?1.f:FPotionUseMotion::Ease((T-Motion.DrinkStart)/(Motion.Contact-Motion.DrinkStart));
        const float Fill=FMath::Lerp(WaterStartFill,WaterEndFill,Progress);
        const float Level=FMath::Lerp(WaterBottomCm,WaterFullCm,Fill);
        if(WaterMaterial&&!FMath::IsNearlyEqual(Level,LastWaterLevel,.001f))
        {WaterMaterial->SetScalarParameterValue(TEXT("FillHeightCm"),Level);LastWaterLevel=Level;}
        Liquid->SetWorldTransform(World);Liquid->SetVisibility(Show&&Fill>.001f);
        const float Open=FPotionUseMotion::Ease((T-.47f)/.17f);
        // Recap while lowering the bottle, without a separate closing pause.
        // The drink endpoint also keeps the cap off for the full sip duration.
        const float CloseStart=Motion.DrinkEnd;
        const float Close=FPotionUseMotion::Ease((T-CloseStart)/.30f);
        const float Lift=Open*(1.f-Close);
        FTransform Cap=World;
        Cap.SetRotation(Rotation*FQuat(FVector::UpVector,FMath::DegreesToRadians(240.f*Lift)));
        Cap.AddToTranslation(Rotation.RotateVector(FVector(0,0,1.4f*Lift)));
        Stopper->SetWorldTransform(Cap);
        Stopper->SetVisibility(Show&&(T<Motion.Uncap||T>=CloseStart));
        return;
    }
    Stopper->SetWorldTransform(World);Stopper->SetVisibility(Show&&T<Motion.Uncap&&!bUncapped);
    const float Fill=1.f-FPotionUseMotion::Ease((T-Motion.DrinkStart)/(Motion.DrinkEnd-Motion.DrinkStart));
    FTransform Fluid=World;Fluid.SetScale3D(FVector(1,1,FMath::Max(.015f,Fill)));
    Fluid.AddToTranslation(Rotation.RotateVector(FVector(0,0,.62f*(1.f-Fill))));
    Liquid->SetWorldTransform(Fluid);Liquid->SetVisibility(Show&&!bCommitted&&Fill>.015f);
}
void UFPSPotionUseComponent::Discard(UStaticMeshComponent* Visual,const FVector& Velocity,float Lifetime)
{
    if(!Visual||!Visual->GetStaticMesh())return;
    if(auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();Body&&Body->PresentConsumableDiscard(Visual,Velocity,Lifetime))return;
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    FActorSpawnParameters Params;Params.Owner=GetOwner();Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Prop=GetWorld()->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),Visual->GetComponentTransform(),Params);
    if(!Prop)return;
    auto* Mesh=Prop->GetStaticMeshComponent();Mesh->SetMobility(EComponentMobility::Movable);Mesh->SetStaticMesh(Visual->GetStaticMesh());
    Mesh->SetCanEverAffectNavigation(false);Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Mesh->SetCollisionObjectType(ECC_PhysicsBody);Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);
    Mesh->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);Mesh->SetCollisionResponseToChannel(ECC_WorldDynamic,ECR_Block);
    Mesh->SetSimulatePhysics(true);Mesh->SetMassOverrideInKg(NAME_None,.12f,true);Mesh->SetUseCCD(true);
    Mesh->SetPhysicsLinearVelocity(GetOwner()->GetVelocity()+Camera->GetComponentTransform().TransformVectorNoScale(Velocity));
    Mesh->SetPhysicsAngularVelocityInDegrees(Camera->GetComponentTransform().TransformVectorNoScale(FVector(-210,360,180)));
    Prop->SetLifeSpan(Lifetime);
}
void UFPSPotionUseComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);if(!bActive)return;
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Player||!Health||Health->IsDead()||Player->IsTraversing()||
        AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(Player->GetController())))
    {Cancel();return;}
    if(ActiveHands==FallbackHands)FallbackHands->SetVisibility(true);
    // Some weapon arms are sampled manually and have their component tick
    // disabled. Keep the drink pose and its held model updating in that case,
    // without evaluating a normally sampled arm twice in the same frame.
    if(ActiveHands.IsValid()&&LastHandPoseFrame!=GFrameCounter)
    {
        ActiveHands->TickAnimation(0.f,false);ActiveHands->RefreshBoneTransforms();
    }
    const float T=Age();
    if(!bSwallowStarted&&T>=Motion.DrinkStart&&T<Motion.DrinkEnd)
    {
        bSwallowStarted=true;
        if(bFood)PlayFoodSwallow();else PlayHydrationAudio(Motion.DrinkEnd-T);
    }
    if(!bFood&&!bSoda&&T>=Motion.Uncap&&!bUncapped){bUncapped=true;if(!bWater)Discard(Stopper,FVector(80,-140,160),2.5f);Stopper->SetVisibility(false);}
    if(T>=Motion.Contact&&!bCommitted)
    {
        auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        // Publication calls ApplyColdSteelProfile and UI listeners synchronously.
        // Mark contact before that callback so any nested interruption cannot
        // treat an already consumed bottle as an uncommitted action.
        bCommitted=true;
        const bool Applied=Model&&Model->UseConsumableAtContact(UsingItem,true);
        if(!bActive)return;
        if(!Applied){bCommitted=false;Cancel();return;}
        if(!bWater)Liquid->SetVisibility(false);
    }
    if(T>=Motion.Release&&!bDiscarded){bDiscarded=true;if(!bWater&&!bFood&&!bSoda)Discard(Bottle,FVector(540,-360,190),7.f);Bottle->SetVisibility(false);Liquid->SetVisibility(false);Stopper->SetVisibility(false);}
    if(T>=Motion.Duration+(bStowOffhand?OffhandRaiseSeconds:0.f))Finish();
}
void UFPSPotionUseComponent::Cancel()
{
    StopSwallowAudio();
    if(!bActive)return;
    // Before contact there is no inventory mutation. After contact the empty
    // bottle can drop, but the successful save/effect must never be refunded.
    if(bCommitted&&!bDiscarded&&!bWater&&!bFood&&!bSoda)Discard(Bottle,FVector(40,-40,-50),5.f);
    Finish();
}
void UFPSPotionUseComponent::Finish()
{
    if(ActiveHands.IsValid())RemoveTickPrerequisiteComponent(ActiveHands.Get());
    bActive=false;bStowOffhand=false;UsingItem.Reset();ActiveHands.Reset();ArmPose.Reset();SetComponentTickEnabled(false);
    if(Bottle)Bottle->SetVisibility(false);if(Liquid)Liquid->SetVisibility(false);if(Stopper)Stopper->SetVisibility(false);
    if(FallbackHands)FallbackHands->SetVisibility(false);
}
void UFPSPotionUseComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    StopSwallowAudio();Finish();LoadHandle.Reset();Super::EndPlay(Reason);
}
