"""Proposed complete Krag right-leg replacement, to integrate after natural hero review.
Uses the same hip/knee/ankle chain; anatomical trouser removal must be wired before enabling.
"""
import math

def geometry(c):
    ball,tube,cyl,torus,box=c['uvball'],c['tube'],c['cyl'],c['torus'],c['box']
    steel,brass,paint,copper,dark=c['steel'],c['brass'],c['paint'],c['copper'],c['dark'];g='BionicThigh_R_Full';bone='Thigh_R'
    # Broad hip socket houses the rotary bearing and transfers load to a boxed femoral spar.
    ball('Full leg hip bearing housing',(-.166,.018,.999),(.105,.093,.104),steel,g,bone,seg=40,rings=28)
    cyl('Hip rotary axle',(-.166,-.090,1.007),(-.166,.105,1.007),.068,brass,g,bone,n=36)
    torus('Hip front retaining rim',(-.166,-.098,1.007),.069,.008,steel,g,bone)
    for j in range(12):
        a=2*math.pi*j/12;ball('Hip bearing lock bolt',(-.166+.079*math.cos(a),-.098,1.007+.079*math.sin(a)),(.006,.004,.006),brass,g,bone,seg=12,rings=8)
    beam=box('Femoral load beam',(-.178,.025,.804),(.093,.085,.287),steel,g,bone,bevel=.010);beam.rotation_euler.y=-.028
    # Opposed telescopic cylinders have separate barrels, bright rods and rod-end clevises.
    for side,xx,yy in [('front outside',-.245,-.042),('rear inside',-.122,.067)]:
        cyl('Full leg '+side+' hydraulic barrel',(xx,yy,.933),(xx-.010,yy,.749),.028,brass,g,bone,n=32)
        cyl('Full leg '+side+' polished ram',(xx-.010,yy,.778),(xx-.018,yy,.628),.014,steel,g,bone,n=28)
        for zz in [.926,.757]:torus('Cylinder machined gland',(xx,yy,zz),.029,.004,steel,g,bone,rot=(0,0,0))
        ball('Hydraulic rod end',(xx-.018,yy,.632),(.025,.024,.030),steel,g,bone,seg=24,rings=16)
        cyl('Rod end cross pin',(xx-.046,yy,.632),(xx+.010,yy,.632),.010,brass,g,bone,n=20)
    # Faceted removable plates leave a deliberate service gap exposing the pistons.
    for sign in [-1,1]:
        plate=box('Thigh service shield '+str(sign),(-.179+sign*.062,-.080,.817),(.066,.025,.228),paint,g,bone,bevel=.012);plate.rotation_euler.y=sign*.06
        for dz in [-.088,.085]:ball('Thigh plate captive bolt',(-.179+sign*.062,-.097,.817+dz),(.008,.004,.008),brass,g,bone,seg=12,rings=8)
    box('Upper thigh socket flange',(-.167,.019,.962),(.183,.170,.038),steel,g,bone,bevel=.013)
    box('Lower thigh clevis',(-.187,.011,.630),(.173,.153,.050),steel,g,bone,bevel=.012)
    cyl('Full knee load axle',(-.187,-.103,.589),(-.187,.104,.589),.064,steel,g,bone,n=40)
    torus('Full knee bearing face',(-.187,-.110,.589),.050,.009,brass,g,bone)
    # Guarded pressure hose follows the back so the knee can bend without an exposed front snag.
    points=[]
    for j in range(28):
        u=j/27;points.append((-.235+.026*u,.067+.035*math.sin(math.pi*u),.977-.324*u))
    tube('Thigh protected hydraulic line',points,.009,copper,g,bone,n=12)
    for j in range(2,26,4):ball('Thigh hose clamp',points[j],(.012,.011,.006),steel,g,bone,seg=12,rings=8)
    box('Thigh service identification recess',(-.180,-.102,.862),(.035,.005,.048),dark,g,bone,bevel=.003)
    for j in range(3):box('Thigh service witness mark',(-.182,-.106,.846+j*.011),(.024,.002,.003),brass,g,bone,bevel=.0005)
    return g
