# Actual Krag coat restoration — limited material pass

The shader-only derivative `b3106c35…` restores the authored eye coat lost in the prior four-map bake. Actual native readback proves the original baked Amber Face, EyeWhite Face and Amber BionicEye materials had coat weight 0, roughness 0.03 and IOR 1.5. They now preserve the source values 1, 0.065 and 1.376. Both guarded jobs complete with native/guard exit 0 and fresh markers.

All 104 texture files remain byte-identical. Reopening the saved derivative verifies the complete material graph apart from the three intended sockets, and exact rig, geometry, point fields, corrective drivers and action data. The original failed PBR and original comparison images remain intact.

Both new Head/Eyes views and their preserved source counterparts were individually inspected: the missing wet-eye reflection returns. Camera, lights and color management match. This is a sampled material-transfer pass, not pixel equality or character approval; face proportions, tusks, cowl, anatomy and other art still fail. Small baked relief differences remain. The bionic-eye constants are verified numerically but that variant is not shown here.

The new full five-variant/seven-clip export plan is prepared, not executed. Manifest coat parameters and Unreal ClearCoat wiring are source-only; native UE compilation/import and actual engine eye review remain pending. Both runtime adapters have a documented coat IOR approximation (1.5 versus source 1.376). Unity HDRP Lit also fixes coat roughness. Shared assets and current game packages are unchanged.
