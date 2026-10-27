#include "FPSBodyPoseAnchorComponent.h"
#include "RenderingThread.h"
#include "SkeletalRenderPublic.h"

void UFPSBodyPoseAnchorComponent::CreateRenderState_Concurrent(FRegisterComponentContext* Context)
{
    // Explicit RecreateRenderState_Concurrent bypasses ShouldCreateRenderState.
    // Keep its component lifecycle valid without constructing a GPU skin object.
    if(PreviousMeshObject)
    {
        PreviousMeshObject->ReleaseResources();
        BeginCleanup(PreviousMeshObject);PreviousMeshObject=nullptr;
    }
    UPrimitiveComponent::CreateRenderState_Concurrent(Context);
}
