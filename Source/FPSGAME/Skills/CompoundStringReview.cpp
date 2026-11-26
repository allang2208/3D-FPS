#include "BowSkillTrainingAuditCommandlet.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/Bow/BowArmsMeshComponent.h"
#include "../Weapons/Bow/BowPartComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInterface.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/ScopeExit.h"

int32 UBowSkillTrainingAuditCommandlet::RunCompoundStringReview(const FString& Params)
{
    FString Report;
    if (!FParse::Value(*Params, TEXT("BowStringReport="), Report)) return 2;
    const FString Original = FCommandLine::Get();
    const FString Profile = TEXT("BowSkillAudit_") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("BowSkillTrainingAudit -ColdSteelProfile=") + Profile));
    ON_SCOPE_EXIT { FCommandLine::Set(*Original); };
    UGameInstance* GI = NewObject<UGameInstance>(GEngine);
    GI->AddToRoot();
    GI->InitializeStandalone(TEXT("CompoundStringReview"));
    UWorld* World = GI->GetWorld();
    ON_SCOPE_EXIT {
        GI->Shutdown();
        if (World) { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); }
        GI->RemoveFromRoot();
    };
    if (!World) return 2;
    auto* Model = GI->GetSubsystem<UColdSteelStatusModel>();
    if (!Model || !Model->IsAudit() || Model->ProfileSlot() != TEXT("ColdSteel_") + Profile) return 2;

    auto Item = Model->CreateItem(TEXT("bow_frontier_compound"));
    FGunsmithParts Parts = {{TEXT("riser"), TEXT("frontier_eclipse")}, {TEXT("sight"), TEXT("bow_farwatch_4x")},
        {TEXT("string"), TEXT("highland_mountain_echo")}, {TEXT("arrow_rest"), TEXT("open_quick_rest")},
        {TEXT("stabilizer"), TEXT("shade_compact")}};
    Item = GI->GetSubsystem<UGunsmithSystem>()->ResolveBowVisual(Item, &Parts);
    Item.Place = 1; Item.Cell = 6;
    Model->Current.Items = {Item};
    Model->Current.ActiveWeaponSlot = 6;
    Model->Current.ActiveProductionTool.Reset();
    auto* Pawn = World->SpawnActor<AFPSGAMECharacter>();
    auto* PC = World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();
    PC->Possess(Pawn);
    auto* Bow = Pawn->FindComponentByClass<UBowWeaponComponent>();
    auto* Delay = IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"));
    if (Delay) Delay->Set(0, ECVF_SetByCode);
    Bow->RefreshEquipment(Model);
    if (Bow->LoadHandle) Bow->LoadHandle->WaitUntilComplete();
    if (!Bow->bPresentationReady || !Bow->UsesCompoundOptic())
    {
        UE_LOG(LogTemp, Error, TEXT("Compound string fixture did not load"));
        return 2;
    }
    auto* Riser = Bow->Part(TEXT("riser"));
    auto* String = Bow->Part(TEXT("string"));
    auto* UpperRod = String->RodVisual(0);
    auto* LowerRod = String->RodVisual(1);
    const FName LightMaterial(TEXT("M_Highland_BeamString_Light"));
    for (auto* Rod : {UpperRod, LowerRod})
        if (!Rod || !Rod->GetStaticMesh() || !Rod->GetMaterial(0) || Rod->GetMaterial(0)->GetFName() != LightMaterial) return 2;
    TArray<FString> Rows = {TEXT("stage,frame,ads,draw,point,eye_x,eye_y,eye_z,local_x,local_y,local_z")};
    int32 Inversions = 0;
    int32 Detached = 0;
    auto Sample = [&](const TCHAR* Stage, int32 Frame)
    {
        Bow->SampleArms();
        Bow->UpdatePoseLayers();
        Bow->UpdateBowGeometry();
        const FTransform& Eye = Bow->Camera->GetComponentTransform();
        const FTransform& Mount = Riser->GetComponentTransform();
        auto Point = [&](const TCHAR* Label, const FVector& WorldPoint)
        {
            const FVector E = Eye.InverseTransformPosition(WorldPoint), L = Mount.InverseTransformPosition(WorldPoint);
            Rows.Add(FString::Printf(TEXT("%s,%d,%.5f,%.5f,%s,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f"),
                Stage, Frame, Bow->AimProgress, Bow->DrawFraction(), Label, E.X, E.Y, E.Z, L.X, L.Y, L.Z));
            return E;
        };
        FVector Upper = Bow->UpperTipCM, Lower = Bow->LowerTipCM;
        Riser->FlexTips(Upper, Lower);
        const FVector U = Point(TEXT("upper"), Mount.TransformPosition(Upper));
        const FVector N = Point(TEXT("nock"), Mount.TransformPosition(Bow->NockPoint()));
        const FVector L = Point(TEXT("lower"), Mount.TransformPosition(Lower));
        for (auto* Rod : {UpperRod,LowerRod})
        {
            const FBox Box = Rod->GetStaticMesh()->GetBoundingBox();
            const FVector End = Point(Rod == UpperRod ? TEXT("upperA") : TEXT("lowerA"), Rod->GetComponentTransform().TransformPosition(FVector(0,0,Box.Min.Z)));
            const FVector Serving = Point(Rod == UpperRod ? TEXT("upperB") : TEXT("lowerB"), Rod->GetComponentTransform().TransformPosition(FVector(0,0,Box.Max.Z)));
            // The luminous spans terminate inside the 1.15 cm ferrules and at most 3.93 cm from the arrow nock.
            if (!Rod->IsVisible() || FVector::Distance(End, Rod == UpperRod ? U : L) > 1.2 || FVector::Distance(Serving,N) > 4.) ++Detached;
        }
        if (N.X <= 0. || U.Z*N.X < N.Z*U.X || N.Z*L.X < L.Z*N.X) ++Inversions;
    };
    Bow->bArrowNocked = true;
    for (const float Draw : {0.f,.25f,.50f,.75f,1.f})
    {
        Bow->Stage = Draw == 0.f ? EBowStage::Ready : Draw < 1.f ? EBowStage::Drawing : EBowStage::Holding;
        Bow->Elapsed = Draw * Bow->DrawSeconds;
        Bow->HipAimProgress = 1.f;
        Bow->Viewmodel->AdvanceEntry(1.f);
        for (int32 I = 0; I <= 24; ++I)
        {
            Bow->AimProgress = I / 24.f;
            Bow->VisualTime += 1.f/60.f;
            Bow->Viewmodel->AdvanceEntry(1.f/60.f);
            Sample(Draw == 0.f ? TEXT("ready") : Draw < 1.f ? TEXT("drawing") : TEXT("holding"), I);
        }
    }
    // Follow the manual pickup into loaded idle, then reverse ADS during both carry loops.
    Bow->bArrowNocked = false;
    Bow->SetStage(EBowStage::Nocking,Bow->NockSeconds);
    for (int32 I=0; I<=36; ++I)
    {
        Bow->Elapsed = Bow->NockSeconds * I / 36.f;
        Bow->AimProgress = I / 36.f;
        Bow->Viewmodel->AdvanceEntry(1.f/60.f);
        Sample(TEXT("nocking"),I);
    }
    Bow->bArrowNocked = true;
    Bow->SetStage(EBowStage::Ready,0.f);
    for (int32 Run=0; Run<2; ++Run)
    {
        Bow->GaitWeight = 1.f;
        Bow->SprintBlend = float(Run);
        for (int32 I=0; I<=48; ++I)
        {
            Bow->GaitPhase = I / 48.f;
            Bow->AimProgress = FMath::Abs(24-I) / 24.f;
            Bow->VisualTime += 1.f / 60.f;
            Bow->Viewmodel->AdvanceEntry(1.f/60.f);
            Sample(Run ? TEXT("loaded_run") : TEXT("loaded_walk"), I);
        }
    }
    UE_LOG(LogTemp, Display, TEXT("COMPOUND_STRING_REVIEW inverted=%d detached=%d"), Inversions, Detached);
    if (!FFileHelper::SaveStringArrayToFile(Rows, *Report)) return 2;
    return Inversions || Detached ? 1 : 0;
}
