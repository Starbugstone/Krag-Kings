# Actual saved-PBR material failure

The saved structural snapshot passes the 79-bone, seven-action, sampled-pose and mesh-payload comparisons. All three original-source renders completed and were inspected. The first actual **reopened baked render is magenta**: Blender reports 98 missing texture files under the old socket-source folder. This is a material-packaging failure, not an artistic acceptance or engine result.

The bake set `//textures/...` while the original source was active, then saved a new file with default relative-path remapping. The default preserved the old root rather than the intended candidate root. After the first failed image, only the owned review process was stopped; native exit -1 / shell 255 is deliberate and retained. The original source, baked file and map bytes remain unchanged.

The prepared correction disables this remapping, reopens the saved derivative and checks every connected texture's actual path, SHA-256, color space and decoded dimensions. A separate path-only derivative will reuse the 98 byte-identical maps. Its actual execution and matched render parity remain pending. The underlying facial/anatomical/groom defects remain open.
