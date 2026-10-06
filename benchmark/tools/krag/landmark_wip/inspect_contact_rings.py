from pathlib import Path
import sys,json,numpy as np
ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'benchmark/art/krag/landmarks-v9nc'
sys.path.insert(0,str(ROOT/'benchmark/tools/nib/v5_wip'))
from analyze_orbital_rings import analyze
c=np.load(OUT/'actual-neutral-surface.npz');r=analyze(c['Head_reference'],c['Head_world'],c['Head_triangles'],c['Head_triangle_sets'],c['Head_edges'])
for side,d in r.items():
 print(side,[(x['stepsFromTaggedCavityBoundary'],x['sourceMeanProjectedRadius'],x['fittedBoundsMin'],x['fittedBoundsMax']) for x in d['layers'] if x['singleClosedCycle']]);print('picked',d['candidateTightClosedRing'])
(OUT/'contact-ring-topology.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
