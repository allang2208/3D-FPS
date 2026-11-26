#pragma once
#include "CoreMinimal.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "ChapelNavigationGeometry.generated.h"

// Navigation-only representations. The original render meshes and gameplay collision stay on these components.
UCLASS()
class UChapelFoundationNavMesh : public UInstancedStaticMeshComponent
{
    GENERATED_BODY()
public:
    virtual bool DoCustomNavigableGeometryExport(FNavigableGeometryExport& Export) const override;
protected:
    virtual void OnRegister() override;
private:
    UPROPERTY(Transient) TObjectPtr<class UBodySetup> NavigationBody;
};

UCLASS()
class UChapelStatueNavMesh : public UStaticMeshComponent
{
    GENERATED_BODY()
public:
    virtual bool DoCustomNavigableGeometryExport(FNavigableGeometryExport& Export) const override;
};
