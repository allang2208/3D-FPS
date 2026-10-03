#include "WeatherViewEffectsComponent.h"
#include "Weapons/HK416WeaponAssets.h"
#include "Weapons/LMG201Attachments.h"
#include "FPSWeatherManager.h"
#include "FPSGAMECharacter.h"
#include "WeatherSurfaceComponent.h"
#include "WeatherPresentationValidation.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/GameInstance.h"
#include "UI/ColdSteelStatusModel.h"
#include "Weapons/DanWesson715WeaponAssets.h"
#include "Weapons/RSH12WeaponAssets.h"
#include "Weapons/DanWesson715FittedParts.h"
#include "Weapons/M1911WeaponAssets.h"
#include "Weapons/G18WeaponAssets.h"
#include "Weapons/PistolGripSurface.h"
#include "Weapons/ASH12WeaponAssets.h"
#include "Weapons/PKMLowpolyWeaponAssets.h"
#include "Weapons/PSO1AttachmentAssets.h"
#include "Weapons/SVDAttachments.h"
#include "Weapons/WeaponSurfaceStandard.h"
#include "HAL/IConsoleManager.h"

static TAutoConsoleVariable<float> CVarScreenRain(TEXT("fps.ScreenRain"),.75f,TEXT("Screen edge water strength, 0 disables."),ECVF_Scalability);
static TAutoConsoleVariable<float> CVarWeaponWetness(TEXT("fps.WeaponWetness"),1.f,TEXT("Weapon wet material strength, 0 disables."),ECVF_Scalability);

namespace
{
UObject* SourceMesh(UMeshComponent* Mesh)
{
    if(auto* Skel=Cast<USkeletalMeshComponent>(Mesh))return Skel->GetSkinnedAsset();
    if(auto* Static=Cast<UStaticMeshComponent>(Mesh))return Static->GetStaticMesh();
    return nullptr;
}
bool IsArmMaterialSlot(FName Slot)
{
    const FString Name=Slot.ToString().ToLower();
    // Imported tool/sword viewmodels combine hands and weapon geometry. Keep
    // only the physical weapon slots; "Handguard" is still a weapon part.
    return Name.Contains(TEXT("manny"))||Name==TEXT("hand")||Name==TEXT("hands")
        ||Name.EndsWith(TEXT("_hand"))||Name.EndsWith(TEXT("_hands"))
        ||Name.Contains(TEXT("glove"))||Name.Contains(TEXT("sleeve"))||Name==TEXT("skin");
}
bool IsMeleeWetnessItem(const FColdSteelItem& Item)
{
    // Use the current definition keys without parsing the item's JSON each tick.
    return Item.Definition==TEXT("ue_rune_sword")||Item.Definition==TEXT("ue_frost_crystal_sword")
        ||Item.Definition==TEXT("ue_highland_claymore")||Item.Definition==TEXT("ue_apprentice_staff")
        ||ColdSteelInventory::IsEquippedProductionTool(Item)||Item.Definition==TEXT("tool_shovel");
}
void RestoreBinding(FWeatherViewMaterial& Binding)
{
    auto* Mesh=Binding.Mesh.Get();
    if(Mesh&&Mesh->GetMaterial(Binding.Slot)==Binding.Wet)
        Mesh->SetMaterial(Binding.Slot,SourceMesh(Mesh)==Binding.MeshAsset.Get()?Binding.Original.Get():nullptr);
}
/** The FNames of the weather scalars, so per-frame writes skip FName construction. */
const FName WetnessName(TEXT("WeaponWetness")),
    ScreenWetnessName(TEXT("ScreenWetness")), StrengthName(TEXT("RainStrength")), AimName(TEXT("AimProtection"));
}
const FName UWeatherViewEffectsComponent::NameWetness=WetnessName;
const FName UWeatherViewEffectsComponent::NameScreenWetness=ScreenWetnessName;
const FName UWeatherViewEffectsComponent::NameStrength=StrengthName;
const FName UWeatherViewEffectsComponent::NameAim=AimName;

UWeatherViewEffectsComponent::UWeatherViewEffectsComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

void UWeatherViewEffectsComponent::Initialize(UWeatherPresentationAssets* InAssets)
{
    Assets=InAssets;
    if(Assets)
        if(const auto* RSH12Materials=LoadObject<UWeatherPresentationAssets>(nullptr,RSH12WeaponAssets::WetMaterialsPath))
            for(const auto& Entry:RSH12Materials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    // The 715's material-only revision supplies its dry/wet pairs separately
    // from the shared weather profiles, which may be open in another editor.
    if(Assets)
        if(const auto* PistolMaterials=LoadObject<UWeatherPresentationAssets>(nullptr,DanWesson715WeaponAssets::WetMaterialsPath))
            for(const auto& Entry:PistolMaterials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
        if(const auto* PistolParts=LoadObject<UWeatherPresentationAssets>(nullptr,DanWesson715FittedParts::WetMaterials))
            for(const auto& Entry:PistolParts->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
        if(const auto* CompactParts=LoadObject<UWeatherPresentationAssets>(nullptr,DanWesson715FittedParts::CompactWetMaterials))
            for(const auto& Entry:CompactParts->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
        if(const auto* G18Materials=LoadObject<UWeatherPresentationAssets>(nullptr,G18WeaponAssets::WetMaterials))
            for(const auto& Entry:G18Materials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
        if(const auto* HK416Materials=LoadObject<UWeatherPresentationAssets>(nullptr,HK416WeaponAssets::WetMaterialsPath))
            for(const auto& Entry:HK416Materials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
        if(const auto* MagazineMaterials=LoadObject<UWeatherPresentationAssets>(nullptr,M1911WeaponAssets::ExtendedMagazineWetMaterials))
            for(const auto& Entry:MagazineMaterials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
        if(const auto* GripSurfaces=LoadObject<UWeatherPresentationAssets>(nullptr,PistolGripSurface::WetMaterialsPath))
            for(const auto& Entry:GripSurfaces->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
        if(const auto* ASH12Materials=LoadObject<UWeatherPresentationAssets>(nullptr,ASH12WeaponAssets::WetMaterialsPath))
            for(const auto& Entry:ASH12Materials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
        if(const auto* LMGMaterials=LoadObject<UWeatherPresentationAssets>(nullptr,LMG201Attachments::WetMaterialsPath))
            for(const auto& Entry:LMGMaterials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
        if(const auto* PKMMaterials=LoadObject<UWeatherPresentationAssets>(nullptr,PKMLowpolyWeaponAssets::WetMaterialsPath))
            for(const auto& Entry:PKMMaterials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
        if(const auto* PSO1Materials=LoadObject<UWeatherPresentationAssets>(nullptr,PSO1AttachmentAssets::WetMaterialsPath))
            for(const auto& Entry:PSO1Materials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
        if(const auto* SVDMaterials=LoadObject<UWeatherPresentationAssets>(nullptr,SVDAttachments::WetMaterialsPath))
            for(const auto& Entry:SVDMaterials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    // Melee originals carry their own wet layer. The dedicated table maps each
    // asset to itself, preserving rune/guard/crystal parameters when copied to a MID.
    if(Assets)
        if(const auto* MeleeMaterials=LoadObject<UWeatherPresentationAssets>(nullptr,TEXT("/Game/Weather/MeleeWetness20261002/DA_MeleeWetMaterials.DA_MeleeWetMaterials")))
            for(const auto& Entry:MeleeMaterials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    // Extended-magazine seam blending must also survive the wet-material swap.
    if(Assets)
        if(const auto* M16Materials=LoadObject<UWeatherPresentationAssets>(nullptr,TEXT("/Game/Weapons/M16A2/UniversalAttachments20260920/DA_M16_AttachmentWetMaterials")))
            for(const auto& Entry:M16Materials->WetMaterials)Assets->WetMaterials.Add(Entry.Key,Entry.Value);
    if(Assets)
    {
        const TCHAR* Dry[] = {
            TEXT("/Game/Weapons/ExtMagContinuity20260919/Materials/M_M4_Continuous.M_M4_Continuous"),
            TEXT("/Game/Weapons/ExtMagContinuity20260919/Materials/M_AKM_Continuous_Graph.M_AKM_Continuous_Graph"),
            TEXT("/Game/Weapons/ASH12/ExtendedMagazine20260919/Materials/M_ASH12_Continuous_Graph.M_ASH12_Continuous_Graph")};
        const TCHAR* Wet[] = {
            TEXT("/Game/Weapons/ExtMagContinuity20260919/Materials/M_M4Wet_Continuous.M_M4Wet_Continuous"),
            TEXT("/Game/Weapons/ExtMagContinuity20260919/Materials/M_AKMWet_Continuous_Graph.M_AKMWet_Continuous_Graph"),
            TEXT("/Game/Weapons/ASH12/ExtendedMagazine20260919/Materials/M_ASH12Wet_Continuous_Graph.M_ASH12Wet_Continuous_Graph")};
        for(int32 I=0;I<3;++I)
            if(auto* Material=LoadObject<UMaterialInterface>(nullptr,Wet[I]))
                Assets->WetMaterials.Add(Dry[I],Material);
    }
    if(Assets&&Assets->ScreenMaterial)
    {
        LensMaterial=UMaterialInstanceDynamic::Create(Assets->ScreenMaterial,this);
        PostProcess=NewObject<UPostProcessComponent>(GetOwner(),TEXT("RainLensPostProcess"));
        PostProcess->bUnbound=true;
        PostProcess->Priority=20.f;
        PostProcess->BlendWeight=0.f;
        PostProcess->Settings.WeightedBlendables.Array.Add(FWeightedBlendable(1.f,LensMaterial));
        PostProcess->RegisterComponent();
    }
    // The wet table is keyed by FStrings from the authoring scripts. Re-key it by
    // object path so BindWeapon never builds a path string again.
    if(Assets)
        for(const auto& Entry:Assets->WetMaterials)
            if(Entry.Value)WetByPath.Add(FName(*Entry.Key),Entry.Value.Get());
    UE_LOG(LogTemp,Display,TEXT("WeatherPresentation ready screen=%d wetMaterialSources=%d"),LensMaterial!=nullptr,WetByPath.Num());
    StartWeatherPresentationValidation(Cast<AFPSWeatherManager>(GetOwner()));
}

/** One MID per immutable original; reused whenever that material binds again.
    Only asset-backed originals are pooled: a gunsmith MID is transient and may be
    destroyed and recreated, so keying on its pointer could later match a recycled
    address and hand out the wrong instance. */
UMaterialInstanceDynamic* UWeatherViewEffectsComponent::AcquireWet(UMaterialInterface* Original,UMaterialInterface* Replacement)
{
    // Self-mapped melee surfaces already contain the wet layer. Keep the same
    // live MID so staff illumination and animated rune/guard parameters keep
    // reaching the material whose pointer their components retained.
    if(auto* Dynamic=Cast<UMaterialInstanceDynamic>(Original))
        if(Dynamic->GetBaseMaterial()==Replacement->GetBaseMaterial())
        {
            Dynamic->SetScalarParameterValue(WetnessName,0.f);
            return Dynamic;
        }
    const bool bPoolable=Original&&Original->IsAsset();
    if(bPoolable)
        for(auto& Shared:SharedWet)
            if(Shared.Original==Original)
                return Shared.Wet;
    auto* Wet=UMaterialInstanceDynamic::Create(Replacement,this);
    if(!Wet)return nullptr;
    Wet->CopyMaterialUniformParameters(Original);
    Wet->SetScalarParameterValue(WetnessName,0.f);
    if(bPoolable)SharedWet.Add(FSharedWetMaterial{Original,Wet});
    return Wet;
}

void UWeatherViewEffectsComponent::RestoreMaterials()
{
    for(auto& Binding:Bindings)RestoreBinding(Binding);
    Bindings.Reset();
}

void UWeatherViewEffectsComponent::BindWeapon(AFPSGAMECharacter* Pawn,bool bScanAll)
{
    if(Pawn!=BoundPawn.Get()){RestoreMaterials();BoundPawn=Pawn;}
    if(!Pawn||!Assets)return;
    // Cheap prune runs every frame: a gunsmith swap empties override materials, so
    // a stale binding is detected and repaired on the next tick instead of up to
    // 200 ms later. The expensive slot scan only runs on demand.
    bool bPruned=false;
    for(int32 I=Bindings.Num()-1;I>=0;--I)
    {
        auto& B=Bindings[I];auto* Mesh=B.Mesh.Get();
        if(!Mesh||SourceMesh(Mesh)!=B.MeshAsset.Get()||Mesh->GetMaterial(B.Slot)!=B.Wet)
        {RestoreBinding(B);Bindings.RemoveAtSwap(I);bPruned=true;}
    }
    if(!bScanAll&&!bPruned)return;
    const TInlineComponentArray<UMeshComponent*> Meshes(Pawn);
    TArray<UMeshComponent*,TInlineAllocator<6>> Roots;
    for(auto* Mesh:Meshes)
    {
        const FName Name=Mesh->GetFName();
        if(Name==TEXT("AKMViewmodel")||Name==TEXT("RuneSwordViewmodel")
            ||Name==TEXT("ProductionToolMesh")||Name==TEXT("ProductionToolHands")
            ||Name==TEXT("StaffV7")||Name==TEXT("StaffAssembly")||Mesh->ComponentHasTag(TEXT("StaffAssembly")))
            Roots.Add(Mesh);
    }
    const auto* Body=Pawn->GetMesh();
    for(auto* Mesh:Meshes)
    {
        if(Mesh->GetFName()==TEXT("StaffV7Arms")||Mesh->GetFName()==TEXT("RuneSwordRift")
            ||Mesh->ComponentHasTag(TEXT("ModularOutfit")))continue;
        bool bWeaponMesh=Roots.ContainsByPredicate([Mesh](const auto* Root){return Mesh==Root||Mesh->IsAttachedTo(Root);});
        // FPSPlayerBodyEquipment creates WorldWeapons/WorldParts without tags.
        // Their roots attach to a body hand socket; outfits attach to the body
        // without one. Following that branch includes copied modular parts only.
        if(!bWeaponMesh&&Body)
        {
            const USceneComponent* Branch=Mesh;
            while(Branch->GetAttachParent()&&Branch->GetAttachParent()!=Body)Branch=Branch->GetAttachParent();
            const FName Socket=Branch->GetAttachSocketName();
            bWeaponMesh=Branch->GetAttachParent()==Body&&(Socket==TEXT("hand_r")||Socket==TEXT("hand_l"));
        }
        if(!bWeaponMesh)continue;
        const auto SlotNames=Mesh->GetMaterialSlotNames();
        for(int32 Slot=0;Slot<Mesh->GetNumMaterials();++Slot)
        {
            if(SlotNames.IsValidIndex(Slot)&&IsArmMaterialSlot(SlotNames[Slot]))continue;
            if(Bindings.ContainsByPredicate([Mesh,Slot](const auto& B){return B.Mesh==Mesh&&B.Slot==Slot;}))continue;
            auto* Original=Mesh->GetMaterial(Slot);if(!Original)continue;
            auto* Source=Original;
            auto* Replacement=WetByPath.Find(FName(*Source->GetPathName()));
            // A gunsmith may already have a MID. Preserve its texture/color values.
            while(!Replacement)
            {
                auto* MID=Cast<UMaterialInstanceDynamic>(Source);
                if(!MID||!MID->Parent)break;
                Source=MID->Parent;
                Replacement=WetByPath.Find(FName(*Source->GetPathName()));
            }
            UMaterialInterface* Target=Replacement&&*Replacement?*Replacement:WeaponSurfaceStandard::SelfWetSource(Source);
            if(!Target)continue;
            auto* Wet=AcquireWet(Original,Target);
            if(!Wet)continue;
            FWeatherViewMaterial B;B.Mesh=Mesh;B.MeshAsset=SourceMesh(Mesh);B.Original=Original;B.Wet=Wet;B.Slot=Slot;B.LastPushed=-1.f;
            Bindings.Add(B);Mesh->SetMaterial(Slot,Wet);
        }
    }
}

void UWeatherViewEffectsComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    auto* Weather=Cast<AFPSWeatherManager>(GetOwner());if(!Weather)return;
    auto* Pawn=Cast<AFPSGAMECharacter>(UGameplayStatics::GetPlayerPawn(this,0));
    BindCountdown-=Delta;
    // Full slot scan every 200 ms, or immediately once a binding was pruned.
    const bool bScan=BindCountdown<=0;
    if(bScan)BindCountdown=.2f;
    BindWeapon(Pawn,bScan);
    const float Rain=Weather->GetEffectiveRainIntensity()*Weather->GetRainExposure();
    const bool bAiming=Pawn&&Pawn->IsAiming();
    const auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0);
    const float Facing=Camera?FMath::Clamp(.7f+Camera->GetCameraRotation().Vector().Z*.45f,.3f,1.1f):.7f;
    ScreenWetness=FMath::Clamp(ScreenWetness+Delta*(Rain*.22f*Facing-1.f/32.f),0.f,1.f);
    FString Key;
    if(Pawn)
    {
        const bool bInventoryWeapon=Pawn->HasInventoryWeapon();
        if(auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        {
            if(const auto* Tool=Model->ActiveProductionTool())Key=Tool->InstanceId;
            else if(const auto* Item=Model->Equipped();Item&&(bInventoryWeapon||IsMeleeWetnessItem(*Item)))Key=Item->InstanceId;
        }
        if(Key.IsEmpty()&&bInventoryWeapon)Key=Pawn->bUseM4Infima?TEXT("PreviewM4"):TEXT("PreviewAKM");
    }
    for(auto& Pair:WeaponWetness)Pair.Value=FMath::Max(0.f,Pair.Value-Delta/120.f);
    if(!Key.IsEmpty())
    {
        float& Value=WeaponWetness.FindOrAdd(Key);
        Value=FMath::Clamp(Value+Delta*Rain*.065f,0.f,1.f);
        ActiveWeaponWetness=Value;
    }
    else ActiveWeaponWetness=0.f;
    const bool bVisible=UWeatherSurfaceComponent::GetQuality()>0;
    const float WeaponStrength=bVisible?FMath::Clamp(CVarWeaponWetness.GetValueOnGameThread(),0.f,1.f):0.f;
    // Quantised to 1/255 steps: a MID scalar write enqueues a render command that
    // invalidates the proxy's uniform expression cache (two global waits inside),
    // so the 120 s drying tail must not push a float every frame.
    constexpr float WetStep=1.f/255.f;
    const float TargetWetness=FMath::RoundToFloat(ActiveWeaponWetness*WeaponStrength/WetStep)*WetStep;
    int32 PushedWet=0,SkippedWet=0;
    for(auto& B:Bindings)if(B.Wet)
    {
        if(TargetWetness<=0.f)
        {
            if(B.LastPushed<=0.f)continue;          // already dry and reported dry
            B.Wet->SetScalarParameterValue(WetnessName,0.f);
            B.LastPushed=0.f;++PushedWet;
        }
        else if(FMath::Abs(TargetWetness-B.LastPushed)<WetStep*.5f)
        {
            ++SkippedWet;                            // guard absorbed the write
        }
        else
        {
            B.Wet->SetScalarParameterValue(WetnessName,TargetWetness);
            B.LastPushed=TargetWetness;++PushedWet;
        }
    }
    if(LensMaterial&&PostProcess)
    {
        const float Strength=bVisible?FMath::Clamp(CVarScreenRain.GetValueOnGameThread(),0.f,1.f):0.f;
        const float AimValue=bAiming?1.f:0.f;
        if(FMath::Abs(ScreenWetness-LastScreenWetness)>=WetStep*.5f)
        {LensMaterial->SetScalarParameterValue(ScreenWetnessName,ScreenWetness);LastScreenWetness=ScreenWetness;++PushedWet;}
        else ++SkippedWet;
        if(FMath::Abs(Strength-LastStrength)>=1e-3f)
        {LensMaterial->SetScalarParameterValue(StrengthName,Strength);LastStrength=Strength;++PushedWet;}
        else ++SkippedWet;
        if(AimValue!=LastAim)
        {LensMaterial->SetScalarParameterValue(AimName,AimValue);LastAim=AimValue;++PushedWet;}
        else ++SkippedWet;
        const float Weight=ScreenWetness>.001f&&Strength>0.f?1.f:0.f;
        if(PostProcess->BlendWeight!=Weight)PostProcess->BlendWeight=Weight;
    }
    // Per-second write counter (frame-budget-stat-semantics.md section 6): the
    // settled state must read zero; a sustained rate means a guard is not working.
    PushedFrame+=PushedWet;SkippedFrame+=SkippedWet;
    CounterSeconds+=Delta;
    if(CounterSeconds>=1.f)
    {
        if(PushedFrame>0||SkippedFrame>0)
            UE_LOG(LogTemp,Display,TEXT("WEATHER_WET_WRITES perSec=%d skippedPerSec=%d bindings=%d wet=%.3f screen=%.3f"),
                PushedFrame,SkippedFrame,Bindings.Num(),ActiveWeaponWetness,ScreenWetness);
        PushedFrame=0;SkippedFrame=0;CounterSeconds=0.f;
    }
}

void UWeatherViewEffectsComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    RestoreMaterials();
    if(PostProcess)PostProcess->DestroyComponent();
    Super::EndPlay(Reason);
}
