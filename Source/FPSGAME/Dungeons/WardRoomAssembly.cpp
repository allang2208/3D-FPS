#include "WardRoomAssembly.h"
#include "WardBedScatter.h"
#include "WardBreakableGlass.h"
#include "DungeonBloodScatter.h"
#include "Components/BoxComponent.h"
#include "Components/DecalComponent.h"
#include "Components/PostProcessComponent.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"

namespace
{
    using J = TSharedPtr<FJsonObject>;
    FVector Vec(const J& O, const TCHAR* Key)
    {
        const auto& V=O->GetArrayField(Key);
        return FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());
    }
    FBox Box(const J& O) {return FBox(Vec(O,TEXT("min")),Vec(O,TEXT("max")));}
}

AActor* WardRoomAssembly::Spawn(UWorld* World,AActor* Owner,const J& S,
    const FTransform& Room,AActor* Frame,FName ReceiverTag,TFunctionRef<UObject*(const FString&)> Resolve)
{
    const FString Type=S->GetStringField(TEXT("type"));
    double Pitch=0,Roll=0;S->TryGetNumberField(TEXT("pitch"),Pitch);S->TryGetNumberField(TEXT("roll"),Roll);
    const FTransform At=FTransform(FRotator(Pitch,S->GetNumberField(TEXT("yaw")),Roll),Vec(S,TEXT("position")))*Room;
    AActor* Result=nullptr;
    UWardBreakableGlass* Pane=nullptr;
    if(Type==TEXT("glass_door"))
    {
        auto* Door=World->SpawnActorDeferred<AWardGlassDoor>(AWardGlassDoor::StaticClass(),At,Owner,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!Door)return nullptr;
        Door->ConfigureStandaloneLeaf(Cast<UStaticMesh>(Resolve(S->GetStringField(TEXT("leaf")))),
            S->GetBoolField(TEXT("positive_hinge")),S->GetNumberField(TEXT("open_seconds")),S->GetNumberField(TEXT("auto_close_seconds")));
        Result=Door;Pane=Door->GlassPane;
    }
    else if(Type==TEXT("glass_window"))
    {
        auto* Window=World->SpawnActorDeferred<AWardGlassWindow>(AWardGlassWindow::StaticClass(),At,Owner,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!Window)return nullptr;
        Result=Window;Pane=Window->GlassPane;
    }
    else if(Type==TEXT("beds"))
    {
        auto* Beds=World->SpawnActorDeferred<AWardBedScatter>(AWardBedScatter::StaticClass(),At,Owner,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!Beds)return nullptr;
        Beds->bGenerateOnBeginPlay=false;
        Beds->BedMesh=Cast<UStaticMesh>(Resolve(S->GetStringField(TEXT("mesh"))));
        Beds->MinBedsPerRoom=S->GetIntegerField(TEXT("min_beds_per_room"));
        Beds->MaxBedsPerRoom=S->GetIntegerField(TEXT("max_beds_per_room"));
        Beds->WallClearance=S->GetNumberField(TEXT("wall_clearance"));
        Beds->BedClearance=S->GetNumberField(TEXT("bed_clearance"));
        for(const auto& V:S->GetArrayField(TEXT("rooms")))
        {
            auto O=V->AsObject();FWardBedRoom R;
            R.RoomId=FName(*O->GetStringField(TEXT("id")));R.Bounds=Box(O);Beds->Rooms.Add(R);
        }
        for(const auto& V:S->GetArrayField(TEXT("poses")))
        {
            auto O=V->AsObject();FWardBedPose P;
            P.PoseId=FName(*O->GetStringField(TEXT("id")));
            P.Rotation=FRotator(O->GetNumberField(TEXT("pitch")),0,O->GetNumberField(TEXT("roll")));
            P.Bounds=Box(O);P.Weight=O->GetNumberField(TEXT("weight"));Beds->Poses.Add(P);
        }
        for(const auto& V:S->GetArrayField(TEXT("keep_clear")))Beds->KeepClear.Add(Box(V->AsObject()));
        for(const auto& V:S->GetArrayField(TEXT("room_props")))
        {
            auto O=V->AsObject();FWardRoomProp P;
            P.TypeId=FName(*O->GetStringField(TEXT("id")));P.Mesh=Cast<UStaticMesh>(Resolve(O->GetStringField(TEXT("mesh"))));
            P.MinPerRoom=O->GetIntegerField(TEXT("min_per_room"));P.MaxPerRoom=O->GetIntegerField(TEXT("max_per_room"));
            P.Clearance=O->GetNumberField(TEXT("clearance"));P.bBlocking=O->GetBoolField(TEXT("blocking"));Beds->RoomProps.Add(P);
        }
        Result=Beds;
    }
    else if(Type==TEXT("blood"))
    {
        auto* Blood=World->SpawnActorDeferred<ADungeonBloodScatter>(ADungeonBloodScatter::StaticClass(),At,Owner,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!Blood)return nullptr;
        Blood->bGenerateOnBeginPlay=false;Blood->ReceiverTag=ReceiverTag;
        Blood->BloodMaterial=Cast<UMaterialInterface>(Resolve(S->GetStringField(TEXT("material"))));
        Blood->FloorCount=S->GetIntegerField(TEXT("floor_count"));Blood->WallCount=S->GetIntegerField(TEXT("wall_count"));
        const auto& Range=S->GetArrayField(TEXT("scanned_size_range_cm"));
        Blood->ScannedSizeRangeCm=FVector2D(Range[0]->AsNumber(),Range[1]->AsNumber());
        Blood->FloorSizeScale=S->GetNumberField(TEXT("floor_size_scale"));
        for(const auto& V:S->GetArrayField(TEXT("surfaces")))
        {
            auto O=V->AsObject();FDungeonBloodSurface Surface;
            Surface.Center=Vec(O,TEXT("center"));Surface.Normal=Vec(O,TEXT("normal"));Surface.AxisU=Vec(O,TEXT("axis_u"));
            const auto& Half=O->GetArrayField(TEXT("half_size"));Surface.HalfSize=FVector2D(Half[0]->AsNumber(),Half[1]->AsNumber());
            Surface.bWall=O->GetBoolField(TEXT("wall"));Blood->Surfaces.Add(Surface);
        }
        Result=Blood;
    }
    else if(Type==TEXT("decal"))
    {
        Result=World->SpawnActorDeferred<AActor>(AActor::StaticClass(),At,Owner,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!Result)return nullptr;
        auto* Decal=NewObject<UDecalComponent>(Result,TEXT("AuthoredFloorMarking"));
        Result->AddInstanceComponent(Decal);Result->SetRootComponent(Decal);
        Decal->SetDecalMaterial(Cast<UMaterialInterface>(Resolve(S->GetStringField(TEXT("material")))));
        Decal->DecalSize=Vec(S,TEXT("decal_size"));Decal->SetSortOrder(S->GetIntegerField(TEXT("sort_order")));
        Decal->SetFadeScreenSize(S->GetNumberField(TEXT("fade_screen_size")));Decal->RegisterComponent();
    }
    else if(Type==TEXT("post_process"))
    {
        Result=World->SpawnActorDeferred<AActor>(AActor::StaticClass(),At,Owner,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!Result)return nullptr;
        auto* Bounds=NewObject<UBoxComponent>(Result,TEXT("RoomExposureBounds"));
        Result->AddInstanceComponent(Bounds);Result->SetRootComponent(Bounds);
        Bounds->SetBoxExtent(Vec(S,TEXT("extent")));Bounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Bounds->SetGenerateOverlapEvents(false);Bounds->SetHiddenInGame(true);Bounds->RegisterComponent();
        auto* Exposure=NewObject<UPostProcessComponent>(Result,TEXT("RoomExposure"));
        Result->AddInstanceComponent(Exposure);Exposure->SetupAttachment(Bounds);
        Exposure->bUnbound=false;Exposure->Priority=S->GetNumberField(TEXT("priority"));
        Exposure->BlendRadius=S->GetNumberField(TEXT("blend_radius"));Exposure->BlendWeight=1.f;
        auto& P=Exposure->Settings;
        P.bOverride_AutoExposureMinBrightness=P.bOverride_AutoExposureMaxBrightness=P.bOverride_AutoExposureBias=true;
        P.AutoExposureMinBrightness=P.AutoExposureMaxBrightness=S->GetNumberField(TEXT("exposure_ev"));
        P.AutoExposureBias=S->GetNumberField(TEXT("exposure_bias"));
        P.bOverride_IndirectLightingIntensity=true;P.IndirectLightingIntensity=S->GetNumberField(TEXT("indirect_intensity"));
        const float Sat=S->GetNumberField(TEXT("saturation")),Contrast=S->GetNumberField(TEXT("contrast"));
        P.bOverride_ColorSaturation=P.bOverride_ColorContrast=true;
        P.ColorSaturation=FVector4(Sat,Sat,Sat,1);P.ColorContrast=FVector4(Contrast,Contrast,Contrast,1);
        P.bOverride_VignetteIntensity=P.bOverride_BloomIntensity=true;
        P.VignetteIntensity=S->GetNumberField(TEXT("vignette"));P.BloomIntensity=S->GetNumberField(TEXT("bloom"));
        Exposure->RegisterComponent();
    }
    if(Pane)
    {
        Pane->SetStaticMesh(Cast<UStaticMesh>(Resolve(S->GetStringField(TEXT("pane")))));
        Pane->FractureMesh=Cast<UStaticMesh>(Resolve(S->GetStringField(TEXT("fracture"))));
        Pane->FractureMaterial=Cast<UMaterialInterface>(Resolve(S->GetStringField(TEXT("fracture_material"))));
        Pane->ImpactParticles=Cast<UNiagaraSystem>(Resolve(S->GetStringField(TEXT("impact_particles"))));
        Pane->BreakSound=Cast<USoundBase>(Resolve(S->GetStringField(TEXT("sound"))));
        Pane->PaneDimensions=Vec(S,TEXT("dimensions_cm"));
    }
    if(Result)
    {
        Result->FinishSpawning(At);
        if(Frame)Result->AttachToActor(Frame,FAttachmentTransformRules::KeepWorldTransform);
    }
    return Result;
}

void WardRoomAssembly::Populate(AActor* Actor,int32 Seed)
{
    if(auto* Beds=Cast<AWardBedScatter>(Actor))Beds->GenerateFromSeed(Seed);
    else if(auto* Blood=Cast<ADungeonBloodScatter>(Actor))Blood->GenerateFromSeed(Seed);
}
