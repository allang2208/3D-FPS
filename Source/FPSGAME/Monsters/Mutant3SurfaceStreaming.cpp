#include "Mutant3.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "TimerManager.h"

void AMutant3::InitializeSurfaceStreaming()
{
    if (GetNetMode() == NM_DedicatedServer) return;
    auto* BodyMesh = GetMesh();
    // Keep normal distance-based streaming, with modest extra headroom for
    // the small face/hand UV islands. This does not enlarge the mesh bounds.
    BodyMesh->StreamingDistanceMultiplier = 1.5f;
    SurfaceStreamingTextures.Reset();
    auto* Surface = BodyMesh->GetMaterial(0);
    if (!Surface) return;
    // Read the saved instance overrides directly. Shader readiness must not
    // decide whether the textures are cached on the first BeginPlay frame.
    static const FName Parameters[] = {TEXT("BaseColor"), TEXT("Normal"), TEXT("ORM"), TEXT("TissueMasks")};
    for (const FName Parameter : Parameters)
    {
        UTexture* Texture = nullptr;
        Surface->GetTextureParameterValue(FHashedMaterialParameterInfo(Parameter), Texture);
        auto* Texture2D = Cast<UTexture2D>(Texture);
        if (Texture2D && Texture2D->GetPathName().StartsWith(TEXT("/Game/Monsters/Mutant3Meshy/SurfacePolish/Textures/")))
            SurfaceStreamingTextures.AddUnique(Texture2D);
    }
    if (SurfaceStreamingTextures.IsEmpty()) return;
    RequestNearbySurfaceMips();
    GetWorldTimerManager().SetTimer(SurfaceStreamingTimer, this, &ThisClass::RequestNearbySurfaceMips, .75f, true);
}

void AMutant3::RequestNearbySurfaceMips()
{
    if (IsHidden() || !GetMesh()->IsVisible()) return;
    bool bNearLocalView = false;
    for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        auto* PC = It->Get();
        if (!PC || !PC->IsLocalController()) continue;
        FVector ViewLocation;
        FRotator ViewRotation;
        PC->GetPlayerViewPoint(ViewLocation, ViewRotation);
        if (FVector::DistSquared(ViewLocation, GetMesh()->Bounds.Origin) <= FMath::Square(1200.f))
        {
            bNearLocalView = true;
            break;
        }
    }
    if (!bNearLocalView) return;
    // Four shared, capped textures (2K colour/normal; 1K ORM/masks). The
    // request is asynchronous and expires two seconds after leaving range.
    // Avoid PrestreamTextures: in editor builds it waits for compilation.
    for (const auto& Texture : SurfaceStreamingTextures)
        if (auto* Asset = Texture.Get()) Asset->SetForceMipLevelsToBeResident(2.f);
}
