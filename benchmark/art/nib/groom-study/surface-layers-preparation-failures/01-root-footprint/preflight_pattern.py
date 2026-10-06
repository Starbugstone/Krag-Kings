"""Lightweight exact-pattern checks, never a native/collision/appearance pass."""
import math,json,hashlib
from pathlib import Path
from cloth_pattern import point, segment_distance
P=Path(__file__).resolve().parent

def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a):return math.sqrt(dot(a,a))


N=160;M=49;grid=[[point(i/N*math.tau,j/(M-1))for i in range(N)]for j in range(M)]
areas=[];returns=[];separations=[]
for j in range(M-1):
    for i in range(N):
        a,b,c,d=grid[j][i],grid[j][(i+1)%N],grid[j+1][(i+1)%N],grid[j+1][i]
        areas.extend([norm(cross(sub(b,a),sub(c,a))),norm(cross(sub(c,a),sub(d,a)))])
for i in range(0,N,4):
    section=[point(i/N*math.tau,j/192)for j in range(193)]
    returns.append(sum(section[k+1][2]-section[k][2]>1e-5 for k in range(192)))
    for a in range(192):
        # Neighbouring arcs are continuously adjacent cloth; only compare
        # separated domains, skipping 8% of the width to detect fold crossings.
        for b in range(a+16,192):
            separations.append(segment_distance(section[a],section[a+1],section[b],section[b+1]))
report={'status':'Exact rest-pattern numerical preflight only; actual skin support and rendered drape pending',
 'vertices':N*M,'triangles':2*N*(M-1),'minimumDoubleTriangleAreaMetersSquared':min(areas),
 'minimumReturnedUpwardSamplesAcross40Sections':min(returns),'minimumNonadjacentSectionDistanceMeters':min(separations),
 'proposedThicknessMeters':.0013,'patternSha256':hashlib.sha256((P/'cloth_pattern.py').read_bytes()).hexdigest(),
 'blocked':[],'nativeGenerated':False,'artisticAcceptance':False}
if min(areas)<1e-12:report['blocked'].append('Degenerate rest pattern')
if min(returns)<8:report['blocked'].append('Returns erased')
if min(separations)<.0018:report['blocked'].append('Fold separation below thickness plus .5mm')
(P/'pattern-preflight.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
