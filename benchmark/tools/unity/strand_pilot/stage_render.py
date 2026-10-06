"""Stage the fixture renderer into the already verified isolated Unity project."""
from pathlib import Path
import json,shutil
REPO=Path(__file__).resolve().parents[4]
BASE=REPO/'benchmark/local/unity-strand-hair-pilot'
project=BASE/'project';output=project/'Assets/NativeGroom'
if output.exists():raise RuntimeError('Preserve existing native-groom pilot assets')
output.mkdir()
shutil.copytree(BASE/'prepared-fixture',output/'Fixture')
shutil.copy2(BASE/'prepared-shader/NativeFurPhysical.shadergraph',output/'NativeFurPhysical.shadergraph')
# This fixture asset provider is editor-only for now. The real runtime pilot
# must put its provider in a runtime assembly before building a player.
for name in ('NativeCurveProvider.cs','RenderProbe.cs'):
 shutil.copy2(Path(__file__).with_name(name),project/'Assets/Editor'/name)
asm=project/'Assets/Editor/StrandPilot.Editor.asmdef';data=json.loads(asm.read_text())
data['references']+=['Unity.Collections'];data['allowUnsafeCode']=True
asm.write_text(json.dumps(data,indent=2)+'\n')
print('NATIVE_RENDER_STAGED')
