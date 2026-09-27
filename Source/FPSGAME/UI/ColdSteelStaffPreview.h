#pragma once
#include "CoreMinimal.h"
#include "../Weapons/Staff/StaffAssembly.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInterface.h"

// Shared by the workbench and inventory icon studio. Never bind to a live weapon.
namespace ColdSteelStaffPreview
{
inline const FSoftObjectPath& QuartzMaterialPath()
{
    static const FSoftObjectPath Path(TEXT("/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23.M_StaffQuartzPreviewV23"));
    return Path;
}

inline bool ApplyMaterials(UStaticMeshComponent* Root)
{
    auto* PreviewMaterial=Cast<UMaterialInterface>(QuartzMaterialPath().ResolveObject());
    if(!PreviewMaterial)return false;
    static const FSoftObjectPath WorldMaterial(TEXT("/Game/Weapons/ApprenticeStaff20260927/QuartzAimV22/Materials/M_Staff_QuartzDenseV22.M_Staff_QuartzDenseV22"));
    // Thin Translucent dual-source blending leaves inverse-coverage alpha intact.
    // This copy preserves the quartz appearance while writing the UI coverage.
    for(auto* Component:ColdSteelStaffAssembly::Components(Root))
        for(int32 Slot=0;Slot<Component->GetNumMaterials();++Slot)
            if(FSoftObjectPath(Component->GetMaterial(Slot))==WorldMaterial)
                Component->SetMaterial(Slot,PreviewMaterial);
    return true;
}
}
