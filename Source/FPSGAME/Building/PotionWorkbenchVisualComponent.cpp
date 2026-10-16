#include "PotionWorkbenchVisualComponent.h"
#include "AlchemySystem.h"
#include "AlchemyInteractionAssets.h"
#include "Components/SplineMeshComponent.h"
#include "AlchemyManualComponent.h"
#include "AlchemyWorkbenchLayout.h"
#include "AlchemyThermometerLayout.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Components/TextRenderComponent.h"
#include "Sound/SoundBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "GameFramework/GameStateBase.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/PlayerCameraManager.h"

namespace {
const FString Root=TEXT("/Game/Building/PotionWorkbench20261015/RuntimeV2/");
const TCHAR* Meshes[]={TEXT("Body"),TEXT("Liquid"),TEXT("Heater"),TEXT("Pestle"),TEXT("Stirrer"),TEXT("Dose"),TEXT("Hourglass"),TEXT("Ladle"),TEXT("Stream"),TEXT("Sand"),TEXT("DoseFill"),TEXT("ToolRests")};
const FSoftObjectPath SteamPath(TEXT("/Game/Props/ForgeInteraction20260927/M_ForgeFume.M_ForgeFume"));
const FSoftObjectPath PlanePath(TEXT("/Engine/BasicShapes/Plane.Plane"));
const FSoftObjectPath SpherePath(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
const FSoftObjectPath WaterPath(TEXT("/Game/Props/CastingStation20260926/RealismV5/M_QuenchWater.M_QuenchWater"));
const FSoftObjectPath TemperatureTextPath(TEXT("/Game/Building/PotionWorkbench20261015/ThermometerV9/M_AlchemyTemperatureText.M_AlchemyTemperatureText"));
FSoftObjectPath MeshPath(const TCHAR* Name)
{
    if(FCString::Strcmp(Name,TEXT("Body"))==0)return FSoftObjectPath(TEXT("/Game/Building/PotionWorkbench20261015/ThermometerV9/SM_AlchemyBody.SM_AlchemyBody"));
    if(FCString::Strcmp(Name,TEXT("Liquid"))==0)return FSoftObjectPath(TEXT("/Game/Props/CastingStation20260926/SM_CoolingWater.SM_CoolingWater"));
    const FString N=FString(TEXT("SM_Alchemy"))+Name;
    return FSoftObjectPath(FCString::Strcmp(Name,TEXT("ToolRests"))==0?TEXT("/Game/Building/PotionWorkbench20261015/RefinementV4/")+N+TEXT(".")+N:Root+TEXT("Meshes/")+N+TEXT(".")+N);
}
FSoftObjectPath MatPath(const TCHAR* Name){const FString N=FString(TEXT("M_Alchemy"))+Name;return FSoftObjectPath(Root+TEXT("Materials/")+N+TEXT(".")+N);}
FSoftObjectPath SoundPath(const TCHAR* Name){const FString N=FString(TEXT("SW_Alchemy"))+Name;return FSoftObjectPath(Root+TEXT("Audio/")+N+TEXT(".")+N);}
float Smooth(float X){return FMath::SmoothStep(0.f,1.f,X);}
FTransform Carry(const FTransform& From,const FTransform& To,float Fraction)
{
    const float T=FMath::Clamp(Fraction,0.f,1.f);const FVector A=From.GetLocation(),B=To.GetLocation();
    const float Peak=float(FMath::Max(A.Z,B.Z))+14.f;
    FVector P=FMath::Lerp(A,B,Smooth((T-.25f)/.5f));
    P.Z=T<.5f?FMath::Lerp(float(A.Z),Peak,Smooth(T/.3f)):FMath::Lerp(Peak,float(B.Z),Smooth((T-.65f)/.35f));
    return FTransform(FQuat::Slerp(From.GetRotation(),To.GetRotation(),Smooth((T-.15f)/.65f)),P);
}
}
UPotionWorkbenchVisualComponent::UPotionWorkbenchVisualComponent()
{PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;}
void UPotionWorkbenchVisualComponent::Configure(UStaticMeshComponent* Body)
{
    Original=Body;if(!Body||GetNetMode()==NM_DedicatedServer)return;
    Manual=NewObject<UAlchemyManualComponent>(GetOwner());Manual->SetupAttachment(Original);Manual->RegisterComponent();Manual->Initialize(GetWorld());
    TArray<FSoftObjectPath> Assets;for(auto N:Meshes)Assets.Add(MeshPath(N));Assets.Add(MatPath(TEXT("Liquid")));Assets.Add(MatPath(TEXT("Rune")));
    Assets.Add(SteamPath);Assets.Add(PlanePath);Assets.Add(SpherePath);Assets.Add(WaterPath);Assets.Add(TemperatureTextPath);
    Assets.Add(FSoftObjectPath(TEXT("/Engine/EngineFonts/RobotoDistanceField.RobotoDistanceField")));
    for(const TCHAR* N:{TEXT("HeatControl"),TEXT("HeatKnob"),TEXT("ReagentTray"),TEXT("MortarHover"),TEXT("TransferRing"),TEXT("TransferGrain")})Assets.Add(AlchemyInteraction::Asset(*(FString(TEXT("SM_Alchemy"))+N)));
    for(const TCHAR* N:{TEXT("M_AlchemyTransferFluid"),TEXT("M_AlchemyTransferGrain")})Assets.Add(AlchemyInteraction::Asset(N));
    for(const TCHAR* N:{TEXT("M_AlchemyBottlingFlow"),TEXT("M_AlchemyVesselLiquid")})Assets.Add(AlchemyInteraction::BottlingAsset(N));
    Assets.Add(FSoftObjectPath(TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")));
    const auto* System=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelAlchemySystem>();
    const auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!System||!Model){bLoadFinished=true;return;}
    for(const auto& Recipe:System->Recipes())for(const auto& Input:Recipe.Inputs)if(!IngredientAssets.Contains(Input.Item))
    {
        const auto* Reagent=AlchemyInteraction::Reagent(Input.Item);
        const FString Path=Reagent?AlchemyInteraction::ReagentAsset(*Reagent,TEXT("Open")).ToString():ColdSteelInventory::Text(Model->CreateItem(Input.Item),TEXT("world_mesh"));
        if(Reagent)Assets.AddUnique(AlchemyInteraction::ReagentAsset(*Reagent,TEXT("Cap")));
        if(Path.IsEmpty()){bLoadFinished=true;return;}
        IngredientAssets.Add(Input.Item,FSoftObjectPath(Path));Assets.AddUnique(FSoftObjectPath(Path));
    }
    for(auto N:{TEXT("Pour"),TEXT("Grind"),TEXT("Boil"),TEXT("Page"),TEXT("Click"),TEXT("Bottle")})Assets.Add(SoundPath(N));
    Loading=UAssetManager::GetStreamableManager().RequestAsyncLoad(Assets,FStreamableDelegate::CreateUObject(this,&ThisClass::Loaded));
}
bool UPotionWorkbenchVisualComponent::Ready() const {return bReady&&Manual&&Manual->Ready();}
bool UPotionWorkbenchVisualComponent::Failed() const {return (bLoadFinished&&!bReady)||(Manual&&Manual->Failed());}
UStaticMeshComponent* UPotionWorkbenchVisualComponent::Part(const TCHAR* N) const
{const auto* Found=Parts.Find(FName(N));return Found?Found->Get():nullptr;}
void UPotionWorkbenchVisualComponent::Loaded()
{
    bLoadFinished=true;
    if(!IsValid(Original)||!IsValid(GetOwner()))return;
    for(auto N:Meshes)if(!MeshPath(N).ResolveObject())return;
    for(const TCHAR* N:{TEXT("SM_AlchemyHeatControl"),TEXT("SM_AlchemyHeatKnob"),TEXT("SM_AlchemyReagentTray"),TEXT("SM_AlchemyMortarHover"),TEXT("SM_AlchemyTransferRing"),TEXT("SM_AlchemyTransferGrain"),TEXT("M_AlchemyTransferFluid"),TEXT("M_AlchemyTransferGrain")})if(!AlchemyInteraction::Asset(N).ResolveObject())return;
    for(const TCHAR* N:{TEXT("M_AlchemyBottlingFlow"),TEXT("M_AlchemyVesselLiquid")})if(!AlchemyInteraction::BottlingAsset(N).ResolveObject())return;
    for(const auto& Pair:IngredientAssets)if(const auto* R=AlchemyInteraction::Reagent(Pair.Key))if(!AlchemyInteraction::ReagentAsset(*R,TEXT("Cap")).ResolveObject())return;
    for(const auto& Pair:IngredientAssets)if(!Cast<UStaticMesh>(Pair.Value.ResolveObject()))return;
    if(!MatPath(TEXT("Liquid")).ResolveObject()||!MatPath(TEXT("Rune")).ResolveObject()||!WaterPath.ResolveObject())return;
    if(!TemperatureTextPath.ResolveObject())return;
    for(auto N:Meshes)
    {
        auto* C=NewObject<UStaticMeshComponent>(GetOwner());C->SetStaticMesh(Cast<UStaticMesh>(MeshPath(N).ResolveObject()));
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);C->SetCanEverAffectNavigation(false);
        C->SetMobility(EComponentMobility::Movable);C->SetupAttachment(Original);C->RegisterComponent();Parts.Add(FName(N),C);
    }
    for(int32 I=0;I<3;++I)
    {
        auto* C=NewObject<UStaticMeshComponent>(GetOwner());C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);C->SetCanEverAffectNavigation(false);
        C->SetMobility(EComponentMobility::Movable);C->SetupAttachment(Original);C->RegisterComponent();C->SetVisibility(false);IngredientParts.Add(C);
    }
    if(auto* M=Cast<UMaterialInterface>(MatPath(TEXT("Liquid")).ResolveObject()))
    {LiquidMaterial=UMaterialInstanceDynamic::Create(M,this);}
    WaterMaterial=UMaterialInstanceDynamic::Create(Cast<UMaterialInterface>(WaterPath.ResolveObject()),this);
    Part(TEXT("Liquid"))->SetMaterial(0,WaterMaterial);Part(TEXT("Liquid"))->SetCastShadow(false);
    WaterMaterial->SetScalarParameterValue(TEXT("QuenchTime"),-10000);
    if(auto* M=Cast<UMaterialInterface>(MatPath(TEXT("Rune")).ResolveObject()))
    {RuneMaterial=UMaterialInstanceDynamic::Create(M,this);auto* C=Part(TEXT("Heater"));for(int32 I=0;I<C->GetNumMaterials();++I)if(C->GetMaterialSlotNames()[I].ToString().Contains(TEXT("Rune")))C->SetMaterial(I,RuneMaterial);}
    Part(TEXT("Heater"))->SetRelativeLocation(FVector(225,-106,102.5));
    Part(TEXT("Hourglass"))->SetRelativeLocation(AlchemyLayout::HourglassRest);
    Part(TEXT("DoseFill"))->AttachToComponent(Part(TEXT("Dose")),FAttachmentTransformRules::KeepRelativeTransform);
    Part(TEXT("DoseFill"))->SetMaterial(0,LiquidMaterial);Part(TEXT("Stream"))->SetMaterial(0,LiquidMaterial);
    auto* Sand=Part(TEXT("Sand"));Sand->AttachToComponent(Part(TEXT("Hourglass")),FAttachmentTransformRules::KeepRelativeTransform);Sand->SetRelativeLocation(FVector(0,0,.8));
    UpperSand=NewObject<UStaticMeshComponent>(GetOwner());UpperSand->SetupAttachment(Part(TEXT("Hourglass")));UpperSand->SetStaticMesh(Sand->GetStaticMesh());UpperSand->SetCollisionEnabled(ECollisionEnabled::NoCollision);UpperSand->RegisterComponent();
    UpperSand->SetRelativeLocationAndRotation(FVector(0,0,14.1),FRotator(180,0,0));
    if(auto* M=Cast<UMaterialInterface>(SteamPath.ResolveObject()))
    {
        Steam=NewObject<UInstancedStaticMeshComponent>(GetOwner());Steam->SetupAttachment(Original);Steam->SetStaticMesh(Cast<UStaticMesh>(PlanePath.ResolveObject()));
        Steam->SetCollisionEnabled(ECollisionEnabled::NoCollision);Steam->SetCastShadow(false);Steam->NumCustomDataFloats=3;Steam->SetCanEverAffectNavigation(false);Steam->RegisterComponent();
        SteamMaterial=UMaterialInstanceDynamic::Create(M,this);SteamMaterial->SetScalarParameterValue(TEXT("Steam"),1);Steam->SetMaterial(0,SteamMaterial);
        for(int32 I=0;I<12;++I)Steam->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector));
    }
    Bubbles=NewObject<UInstancedStaticMeshComponent>(GetOwner());Bubbles->SetupAttachment(Original);Bubbles->SetStaticMesh(Cast<UStaticMesh>(SpherePath.ResolveObject()));
    Bubbles->SetMaterial(0,LiquidMaterial);Bubbles->SetCollisionEnabled(ECollisionEnabled::NoCollision);Bubbles->SetCastShadow(false);Bubbles->SetCanEverAffectNavigation(false);Bubbles->RegisterComponent();
    for(int32 I=0;I<8;++I)Bubbles->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector));
    for(auto N:{TEXT("Pour"),TEXT("Grind"),TEXT("Boil"),TEXT("Page"),TEXT("Click"),TEXT("Bottle")})if(auto* S=Cast<USoundBase>(SoundPath(N).ResolveObject()))Sounds.Add(FName(N),S);
    auto Audio=[this](const TCHAR* Name,const FVector& P)
    {
        auto* C=NewObject<UAudioComponent>(GetOwner());C->SetupAttachment(Original);C->bAutoActivate=false;C->bAutoDestroy=false;
        C->bOverrideAttenuation=true;C->AttenuationOverrides.bAttenuate=true;C->AttenuationOverrides.bSpatialize=true;
        C->AttenuationOverrides.AttenuationShapeExtents=FVector(80);C->AttenuationOverrides.FalloffDistance=700;
        C->SetSound(Sounds.FindRef(FName(Name)));C->SetRelativeLocation(P);C->RegisterComponent();return C;
    };
    GrindAudio=Audio(TEXT("Grind"),FVector(45,-49,100));BoilAudio=Audio(TEXT("Boil"),FVector(225,-106,118));
    CreateInteractionParts();
    TemperatureReadout=NewObject<UTextRenderComponent>(GetOwner());
    TemperatureReadout->SetupAttachment(Original);
    TemperatureReadout->SetRelativeLocationAndRotation(AlchemyThermometer::ReadoutPosition,AlchemyThermometer::ReadoutRotation);
    TemperatureReadout->SetHorizontalAlignment(EHorizTextAligment::EHTA_Center);
    TemperatureReadout->SetVerticalAlignment(EVerticalTextAligment::EVRTA_TextCenter);
    TemperatureReadout->SetWorldSize(AlchemyThermometer::DigitSize);
    TemperatureReadout->SetTextMaterial(Cast<UMaterialInterface>(TemperatureTextPath.ResolveObject()));
    TemperatureReadout->SetTextRenderColor(FColor(238,246,232));
    TemperatureReadout->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    TemperatureReadout->SetCanEverAffectNavigation(false);TemperatureReadout->SetCastShadow(false);
    TemperatureReadout->SetText(FText::FromString(TEXT("--")));TemperatureReadout->RegisterComponent();
    // The buildable keeps its original bounds, collision and saved asset identity.
    Original->SetVisibility(false,false);bReady=true;UpdateBook();UpdateIngredients();SetComponentTickEnabled(true);TickComponent(0,LEVELTICK_All,nullptr);
}
void UPotionWorkbenchVisualComponent::Sound(const TCHAR* Name,const FVector& P)
{
    auto* S=Sounds.FindRef(FName(Name)).Get();auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0);
    if(!S||!Camera||!Original)return;const FVector Position=Original->GetComponentTransform().TransformPosition(P);
    const float Volume=FMath::Clamp(1-float(FVector::Distance(Camera->GetCameraLocation(),Position))/800,0.f,1.f)*.6f;
    if(Volume>0)UGameplayStatics::PlaySoundAtLocation(this,S,Position,Volume);
}
void UPotionWorkbenchVisualComponent::Present(const FAlchemyBenchState& S)
{
    if(bReady&&S.Operator)
    {
        if(State.Heat!=S.Heat)Sound(TEXT("Click"),FVector(225,-106,103));
        float Now=GetWorld()->GetTimeSeconds();if(auto* GS=GetWorld()->GetGameState())Now=GS->GetServerWorldTimeSeconds();
        if(State.ActionSerial!=S.ActionSerial&&Now-S.ActionTime<.8f)
        {if(S.Tool==uint8(EAlchemyOp::Pour))Sound(TEXT("Pour"),FVector(225,-106,126));}
    }
    State=S;if(bReady){UpdateBook();UpdateIngredients();UpdateThermometer();SetComponentTickEnabled(true);}
}
void UPotionWorkbenchVisualComponent::UpdateThermometer()
{
    if(!TemperatureReadout)return;
    // Read the same replicated sample that drives liquid/heat presentation.
    // Empty or unattended benches have no current measurement, not a fixed 72 C.
    const int32 Reading=IsValid(State.Operator)&&State.Fill>.001f?FMath::RoundToInt(State.Temperature*10.f):MIN_int32;
    if(Reading==DisplayedTemperature)return;
    DisplayedTemperature=Reading;
    TemperatureReadout->SetText(FText::FromString(Reading==MIN_int32?TEXT("--"):FString::Printf(TEXT("%.1f"),Reading/10.f)));
    TemperatureReadout->SetXScale(1.f);
    const float Width=TemperatureReadout->GetTextLocalSize().Y;
    if(Width>8.4f)TemperatureReadout->SetXScale(8.4f/Width);
}
void UPotionWorkbenchVisualComponent::UpdateBook()
{
    if(!Manual)return;
    Manual->SetOpen(IsValid(State.Operator));
    if(State.BookPage!=ObservedPage||State.Recipe!=ObservedRecipe)
    {
        if(const auto* System=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelAlchemySystem>())
            if(const auto* R=System->Recipe()&&System->Recipe()->Id==State.Recipe?System->Recipe():System->Find(State.Recipe))Manual->SetRecipe(*R,State.BookPage);
        ObservedPage=State.BookPage;ObservedRecipe=State.Recipe;
        if(State.Operator)Sound(TEXT("Page"),FVector(118,-45,97));
    }
}
FVector UPotionWorkbenchVisualComponent::FocusPoint() const
{
    const FVector Local=State.Tool==uint8(EAlchemyOp::Grind)?FVector(45,-50,102):FVector(225,-106,120);
    return Original?Original->GetComponentTransform().TransformPosition(Local):FVector::ZeroVector;
}
FTransform UPotionWorkbenchVisualComponent::ToolGrip() const
{
    const auto Tool=HandTool();auto* C=Part(Tool==EAlchemyOp::Grind?TEXT("Pestle"):Tool==EAlchemyOp::Pour?TEXT("Dose"):Tool==EAlchemyOp::Bottle?TEXT("Ladle"):Tool==EAlchemyOp::Timer?TEXT("Hourglass"):TEXT("Stirrer"));
    if(Tool==EAlchemyOp::Pour&&IngredientParts.IsValidIndex(State.Ingredient))
    {C=IngredientParts[State.Ingredient];return FTransform(IngredientMouth[State.Ingredient]*.45)*C->GetComponentTransform();}
    const float Height=Tool==EAlchemyOp::Timer?7.5f:4.f;
    return C?FTransform(FVector(0,0,Height))*C->GetComponentTransform():FTransform::Identity;
}
EAlchemyOp UPotionWorkbenchVisualComponent::HandTool() const {return bReturningStirrer?EAlchemyOp::Stir:EAlchemyOp(State.Tool);}
FTransform UPotionWorkbenchVisualComponent::BottleGrip() const
{if(HandTool()==EAlchemyOp::Pour&&IngredientCaps.IsValidIndex(State.Ingredient))return FTransform(IngredientMouth[State.Ingredient]+FVector(0,0,.6))*IngredientCaps[State.Ingredient]->GetComponentTransform();
    auto* C=Part(TEXT("Dose"));return C?FTransform(FVector(0,0,2))*C->GetComponentTransform():FTransform::Identity;}
void UPotionWorkbenchVisualComponent::TickComponent(float Dt,ELevelTick Kind,FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Dt,Kind,Fn);if(!bReady)return;VisualTime+=Dt;
    const bool Active=IsValid(State.Operator);const auto Tool=EAlchemyOp(State.Tool);
    UpdateThermometer();
    Manual->SetRelativeLocation(Active?AlchemyLayout::Book:FVector(23,-28,94));Manual->Advance(Dt);
    float Now=GetWorld()->GetTimeSeconds();if(auto* GS=GetWorld()->GetGameState())Now=GS->GetServerWorldTimeSeconds();
    const float T=FMath::Max(0.f,Now-State.ActionTime);
    if(ObservedSerial!=State.ActionSerial){ObservedSerial=State.ActionSerial;BeforePourColor=DisplayColor;}
    const FLinearColor TargetColor=Tool==EAlchemyOp::Pour?FMath::Lerp(BeforePourColor,State.Color,AlchemyInteraction::Poured(T)):State.Color;
    DisplayColor=Dt<=0?TargetColor:FMath::Lerp(DisplayColor,TargetColor,1-FMath::Exp(-3.f*Dt));
    const float TargetFill=Active?FMath::Max(0.f,State.Fill-(Tool==EAlchemyOp::Pour?UnitFill*(1-AlchemyInteraction::Poured(T)):0.f)):0.f;
    DisplayFill=Dt<=0?TargetFill:FMath::FInterpTo(DisplayFill,TargetFill,Dt,6.f);
    AnimateIngredients(T,Active&&Tool==EAlchemyOp::Pour);
    // Authored pointer points +Y after FBX conversion; detents mirror Blender Y.
    Part(TEXT("HeatKnob"))->SetRelativeRotation(FRotator(0,45-State.Heat*90,0));
    const float SurfaceZ=114.f+5.f*FMath::Clamp(DisplayFill/.85f,0.f,1.f);
    // Fit the reused 21 cm basin disk to the authored inner-wall profile at this liquid level.
    const float InnerRadius=SurfaceZ<=116?25.1f-.35f*(SurfaceZ-110):23.f-.3f*(SurfaceZ-116);
    Part(TEXT("Liquid"))->SetVisibility(Active&&DisplayFill>.001f);
    Part(TEXT("Liquid"))->SetRelativeLocation(FVector(225,-106,SurfaceZ));
    Part(TEXT("Liquid"))->SetRelativeScale3D(FVector((InnerRadius-.05f)/21.f,(InnerRadius-.05f)/21.f,1));
    // One authority phase and clock for owner, observers and late relevance.
    // Extrapolation stops at the server's input lease, so a stalled connection
    // cannot keep the spoon moving indefinitely on another client.
    const float StirStart=FMath::Max(State.SampleTime,State.ActionTime+AlchemyLayout::StirPickupSeconds);
    const float StirAge=Tool==EAlchemyOp::Stir?FMath::Max(0.f,FMath::Min(Now,State.InputEndTime)-StirStart):0.f;
    Motion=State.StirPhase+StirAge*State.Stir*1.5f*PI;
    if(LiquidMaterial){LiquidMaterial->SetVectorParameterValue(TEXT("PotionColor"),DisplayColor);LiquidMaterial->SetScalarParameterValue(TEXT("Agitation"),Tool==EAlchemyOp::Stir?FMath::Abs(State.Stir):State.Temperature>60?.35f:.04f);}
    if(WaterMaterial)
    {
        const float Activity=Active?FMath::Clamp((State.Temperature-45)/45.f,0.f,.5f)+(Tool==EAlchemyOp::Stir?.5f*FMath::Abs(State.Stir):0.f):0.f;
        if(!AppliedWaterColor.Equals(DisplayColor,.0001f))
        {
            WaterMaterial->SetVectorParameterValue(TEXT("WaterSurfaceTint"),DisplayColor*.1f);
            WaterMaterial->SetVectorParameterValue(TEXT("ScatteringPerCm"),FLinearColor(.0009f+DisplayColor.R*.012f,.0009f+DisplayColor.G*.012f,.0009f+DisplayColor.B*.012f));
            WaterMaterial->SetVectorParameterValue(TEXT("AbsorptionPerCm"),FLinearColor(.008f+(1-DisplayColor.R)*.03f,.008f+(1-DisplayColor.G)*.03f,.008f+(1-DisplayColor.B)*.03f));
            AppliedWaterColor=DisplayColor;
        }
        WaterMaterial->SetScalarParameterValue(TEXT("Immersion"),Activity);
        WaterRippleClock+=Dt;
        if(Active&&WaterRippleClock>1.1f&&Activity>.05f)
        {
            WaterMaterial->SetScalarParameterValue(TEXT("QuenchTime"),GetWorld()->GetTimeSeconds());
            WaterMaterial->SetVectorParameterValue(TEXT("QuenchPoint"),Tool==EAlchemyOp::Stir?FLinearColor(9*FMath::Cos(Motion),9*FMath::Sin(Motion),0):FLinearColor::Black);
            WaterRippleClock=0;
        }
        WaterObservedSerial=State.ActionSerial;
    }
    if(RuneMaterial)RuneMaterial->SetScalarParameterValue(TEXT("Glow"),Active?State.Heat*1.5f+.08f:.08f);
    const bool Bottling=Active&&Tool==EAlchemyOp::Bottle;
    FVector Pestle(47,-49,103);FRotator PestleQ(0,0,36);
    if(Active&&Tool==EAlchemyOp::Grind){Pestle+=FVector(1.3f*FMath::Cos(T*8),1.3f*FMath::Sin(T*8),.6f*FMath::Sin(T*16));PestleQ=FRotator(12*FMath::Sin(T*8),0,12*FMath::Cos(T*8));}
    Part(TEXT("Pestle"))->SetRelativeLocationAndRotation(Pestle,PestleQ);
    const FTransform StirRest(AlchemyLayout::ToolRestRotation,AlchemyLayout::StirrerRest);
    if(PreviousTool==EAlchemyOp::Stir&&Tool==EAlchemyOp::Stop){StirrerReturnFrom=Part(TEXT("Stirrer"))->GetRelativeTransform();StirrerReturnAt=VisualTime;bReturningStirrer=true;}
    if(Tool!=EAlchemyOp::Stop)bReturningStirrer=false;
    if(bReturningStirrer&&VisualTime-StirrerReturnAt>=.45f)bReturningStirrer=false;
    PreviousTool=Tool;
    const FTransform StirWork(FRotator(8,0,0),FVector(225+11*FMath::Cos(Motion),-106+11*FMath::Sin(Motion),SurfaceZ+18.5));
    Part(TEXT("Stirrer"))->SetRelativeTransform(Active&&Tool==EAlchemyOp::Stir?Carry(StirRest,StirWork,T/AlchemyLayout::StirPickupSeconds):bReturningStirrer?Carry(StirrerReturnFrom,StirRest,(VisualTime-StirrerReturnAt)/.45f):StirRest);
    AnimateBottling(T,SurfaceZ,Bottling);
    UpdateTransfer(T,SurfaceZ,Active);
    UpdateHoverProxies();
    const bool TurningGlass=Active&&Tool==EAlchemyOp::Timer&&T<.9f;
    const float Flip=TurningGlass?Smooth((T-.1f)/.6f):1.f;
    const float Angle=State.HourglassInverted?Flip*PI:(1-Flip)*PI;
    const FQuat GlassQ(FVector::YAxisVector,Angle);
    const FVector GlassCenter=AlchemyLayout::HourglassRest+FVector(0,0,7.5+(TurningGlass?6*FMath::Sin(PI*Smooth(T/.9f)):0));
    Part(TEXT("Hourglass"))->SetRelativeLocationAndRotation(GlassCenter-GlassQ.RotateVector(FVector(0,0,7.5)),GlassQ);
    const float Fraction=Active?State.TimerFraction:1.f;
    const float BottomSand=State.HourglassInverted?1-Fraction:Fraction;
    Part(TEXT("Sand"))->SetVisibility(BottomSand>.001f);UpperSand->SetVisibility(BottomSand<.999f);
    Part(TEXT("Sand"))->SetRelativeScale3D(FVector(1,1,FMath::Max(.001f,BottomSand)));
    UpperSand->SetRelativeScale3D(FVector(1,1,FMath::Max(.001f,1-BottomSand)));
    const float Warm=Active&&State.Fill>0?FMath::Clamp((State.Temperature-45)/35,0.f,1.f):0;
    if(GrindAudio){if(Active&&Tool==EAlchemyOp::Grind){if(!GrindAudio->IsPlaying())GrindAudio->Play();}else GrindAudio->Stop();}
    if(BoilAudio){BoilAudio->SetVolumeMultiplier(Warm*.5f);if(Warm>.1f){if(!BoilAudio->IsPlaying())BoilAudio->Play();}else BoilAudio->Stop();}
    auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0);const FVector Eye=Camera?Original->GetComponentTransform().InverseTransformPosition(Camera->GetCameraLocation()):FVector(180,-170,170);
    const bool Near=FVector::DistSquared(Eye,FVector(225,-106,120))<FMath::Square(1600.f);
    EffectsClock+=Dt;const bool UpdateEffects=EffectsClock>=1.f/30.f;if(UpdateEffects)EffectsClock=0;
    if(Steam)
    {
        Steam->SetVisibility(Warm>0&&Near);for(int32 I=0;I<12&&Warm>0&&Near&&UpdateEffects;++I)
        {
            const float Age=FMath::Fmod(VisualTime*.36f+I/12.f,1.f),A=I*2.4f;
            const FVector P(225+FMath::Cos(A)*11+FMath::Sin(A+Age*4)*Age*4,-106+FMath::Sin(A)*11,SurfaceZ+1+Age*32);
            const FQuat Q=FRotationMatrix::MakeFromZY((Eye-P).GetSafeNormal(),FVector::UpVector).ToQuat();const float Size=(8+Age*17)/100;
            Steam->UpdateInstanceTransform(I,FTransform(Q,P,FVector(Size,Size,1)),false,false,true);
            Steam->SetCustomDataValue(I,0,.1f*Warm*Smooth(Age/.15f)*(1-Smooth((Age-.45f)/.55f)),false);Steam->SetCustomDataValue(I,1,I*.071f,false);Steam->SetCustomDataValue(I,2,Age,false);
        }
        if(Warm>0&&Near&&UpdateEffects)Steam->MarkRenderStateDirty();
    }
    Bubbles->SetVisibility(Warm>.35f&&Near);
    for(int32 I=0;I<8&&Warm>.35f&&Near&&UpdateEffects;++I)
    {const float Age=FMath::Fmod(VisualTime*.8f+I*.13f,1.f),A=I*2.4f;Bubbles->UpdateInstanceTransform(I,FTransform(FQuat::Identity,FVector(225+FMath::Cos(A)*14,-106+FMath::Sin(A)*14,SurfaceZ+Age*.5f),FVector(.006f*FMath::Sin(Age*PI)*Warm)),false,false,true);}
    if(Warm>.35f&&Near&&UpdateEffects)Bubbles->MarkRenderStateDirty();
    if(!Active){SetHoverTarget({},false);if(!bReturningStirrer)SetComponentTickEnabled(false);}
}
void UPotionWorkbenchVisualComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(Loading)Loading->CancelHandle();if(Original)Original->SetVisibility(true,false);
    if(Steam)Steam->DestroyComponent();if(Bubbles)Bubbles->DestroyComponent();if(UpperSand)UpperSand->DestroyComponent();
    if(GrindAudio)GrindAudio->DestroyComponent();if(BoilAudio)BoilAudio->DestroyComponent();
    if(TemperatureReadout)TemperatureReadout->DestroyComponent();
    if(TransferDrops)TransferDrops->DestroyComponent();
    for(const auto& C:FlowSegments)if(C)C->DestroyComponent();FlowSegments.Reset();
    for(const auto& C:IngredientCaps)if(C)C->DestroyComponent();IngredientCaps.Reset();
    for(const auto& C:HoverProxies)if(C)C->DestroyComponent();HoverProxies.Reset();HoverSources.Reset();
    if(Manual)Manual->DestroyComponent();for(auto& Entry:Parts)if(Entry.Value)Entry.Value->DestroyComponent();Parts.Reset();
    for(const auto& C:IngredientParts)if(C)C->DestroyComponent();IngredientParts.Reset();IngredientAssets.Reset();
    Super::EndPlay(Reason);
}
