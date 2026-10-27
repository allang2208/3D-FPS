            UploadedHeadId=PendingUploadHeadId;UploadedHairId=PendingUploadHairId;bHasUploadedAppearance=true;
            bHasLastSent = true;
            LastUploadAt = Now;
            PendingUpload.Reset();
            DispatchCampfireAfterUpload();
            DispatchInventoryAfterUpload();
        }
    }
}
