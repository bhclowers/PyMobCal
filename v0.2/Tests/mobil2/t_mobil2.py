'''
Test of mobil2

'''

import math
import numpy as np
import scipy
from scipy.spatial.transform import Rotation as R
import sys
import mobil2_f

class IntegratorState:
    '''
    Retains information about the integration method
    '''
    def __init__(self,dt):
        self.var=2.97013888888
        self.cvar=0.990972222222
        self.acst=0.332866152768
        self.a=np.array([0.50,0.292893218814,1.70710678118,0.1666666666667])
        self.b=np.array([2.0,1.0,1.0,2.0])
        self.c=np.array([-0.5,-0.292893218814,-1.70710678118,-0.5])
        self.ampc=np.array([-0.111059153612,0.672667757774,-1.70633621697,2.33387888707,-1.8524668225])
        self.amcc=np.array([0.0189208128941,-0.121233356692,0.337771548703,-0.55921513665])

        self.q=np.zeros(6)
        self.hvar=dt*self.var
        self.hcvar=dt*self.cvar
        self.Dt=0.5*dt
        self.array_f=np.zeros([6,6])
        self.l=0
        self.k=0
    
    def Reset(self,dt):
        self.q=np.zeros(6)
        self.hvar=dt*self.var
        self.hcvar=dt*self.cvar
        self.Dt=0.5*dt

    def GetStatus(self):
        return self.l

    def SetStatus(self,value):
        self.l=value

    def ComputeRKG(self,w,ion,coord,lj,chargeList,dipole,tim):
        self.k=0
        while True:
            for j in range(0,4):
                if ((-1)**(j+1))>0:
                    tim=tim+0.5*self.Dt
                dw,pot,dpotx,dpoty,dpotz,dmax=deriv(w,ion,coord,lj,chargeList,dipole)
                dw=self.Dt*dw
                r=self.a[j]*np.subtract(dw,self.b[j]*self.q)           
                w=w+r
                self.q=self.q+3*r+self.c[j]*dw
            dw,pot,dpotx,dpoty,dpotz,dmax=deriv(w,ion,coord,lj,chargeList,dipole)

            if self.k>0:
                break
            else:
                self.k=1
        
        if (self.l-6)>=0:
            self.l=-1
            self.Dt=2.0*self.Dt
            return w,self.Dt,tim,dw,pot,dpotx,dpoty,dpotz,dmax
        else:           
            self.array_f[self.l-1]=dw
            return w,self.Dt,tim,dw,pot,dpotx,dpoty,dpotz,dmax

    def ComputeAMpc(self,w,dw,ion,coord,lj,chargeList,dipole,tim):
        savw=w
        savdw=dw
        self.array_f[5]=savdw
        for j in range(6):
            for i in range(5):
                self.array_f[-1,j]=self.array_f[-1,j]+self.ampc[i]*self.array_f[i,j]
        w=self.array_f[-1]*self.hvar+w
        tim=tim+self.Dt
        dw,pot,dpotx,dpoty,dpotz,dmax=deriv(w,ion,coord,lj,chargeList,dipole)
        
        self.array_f[-1]=self.acst*dw
        for j in range(6):
            for i in range(4):
                self.array_f[i,j]=self.array_f[i+1,j]
                self.array_f[-1,j]=self.array_f[i,j]*self.amcc[i]+self.array_f[-1,j]
        self.array_f[4]=savdw
        w=savw+self.hcvar*np.add(self.array_f[4],self.array_f[-1])
        dw,pot,dpotx,dpoty,dpotz,dmax=deriv(w,ion,coord,lj,chargeList,dipole)
        return w,self.Dt,tim,dw,pot,dpotx,dpoty,dpotz,dmax


    
class AtomData:
    '''
    Contains information about each atom within the molecule
    '''
    def __init__(self,mass=[],charge=[],coord=[]):
        self.Mass=mass
        self.Charges=charge
        self.Coords=coord
    
    def UpdatePosition(self,coord=[]):
        self.Coords=coord

class molecule:
    '''
    Contains information about the molecules as a whole
    '''

    def __init__(self):
        self.TotalMass=0
        self.dipole=0
        self.totalCharge=0
        self.totalAbsoluteCharge=0
        self.mGas=0
        self.mu=0  #reduced mass
        self.mobility=0
        self.temperature=float(298)  #kelvin

    def SetMass(self,mass):
        self.TotalMass=mass

    def SetDipole(self,dipole):
        self.dipole=dipole

    def SetMobility(self,mobility):
        self.mobility=mobility

    def SetCharges(self,tcharge,acharge):
        self.totalCharge=tcharge
        self.totalAbsoluteCharge=acharge
    
    def SetMassGas(self,gasMass,scale=1):
        self.mGas=gasMass
        self.mu=((self.TotalMass*self.mGas)/(self.TotalMass+self.mGas))/(scale)

class infile:
    '''
    Information found in the input file. This is the class used within the code itself.
    Ideally, this software can read different types of input, but all of those will
    populate this class. 
    In this way, we make the "reading file" phase independent from its refernce within the code itself.
    '''
    def __init__(self,inList):
        self.atoms=inList["atoms"]
        self.icoord=inList["icoord"]
        self.units=inList["units"]
        self.charges=inList["charges"]
        self.cfact=inList["cfact"]
        self.label=inList["label"]
        
class atom:
    '''
    It contains information about the atoms in the periodic table (not within the molecule!!)
    Not all atoms of the periodic table are supported, as some properties have not been estimated yet
    '''
    def __init__(self,name,mass,e,s,rhs,id):
        self.name=name
        self.mass=mass
        self.epsilonLJ=e
        self.sigmaLJ=s
        self.rhs=rhs
        self.id=id
    
    def Unpack(self):
        return self.mass,self.epsilonLJ,self.sigmaLJ,self.rhs

class constants:
    '''
    Constants used within the code
    '''
    def __init__(self):
        self.pi=np.pi
        self.cang= 180/np.pi
        self.xe= 1.60217733e-19
        self.xk=1.380658e-23
        self.xn= 6.0221367e23
        self.xeo= 8.854187817e-12
        self.xmv=0.02241410
        self.eo=1.34e-03*self.xe
        self.ro=3.043e-10
        self.ro2=self.ro*self.ro
        self.ipr=1000
        self.inp=40   
        self.itn=10 
        self.imp=25
        self.cmin=0.0005
        self.sw1=0.00005
        self.sw2=0.005 
        self.dtsf1=0.5
        self.dtsf2=0.1
        self.inwr=1
        self.ifail=100
        self.ifailc=0              #This should probably be brought outside. It is changed by the code, so not a constant
        self.inum=250000
        self.inor=30
        self.v=2309.9              #
        self.b=1.5654e-10          #
        self.ntheta=33.3
        self.nphi=64.250
        self.ngamma=134.30
        self.ehsm=0
        self.tmm=0
        self.immmax=0
        self.immmin=self.inor
        self.traj_lost=30000        #DIFF: This was hard-coded into the function. I believe this is the right place
        self.vec_dim=100            #DIF: this is what is used within the FORTRAN function as dimension of arrays 


class printSwitch:
    '''
    Some switches used to turn on/off some debugging features.
    Unless you are modifying the code, keep defaults
    '''
    def __init__(self):
        self.ip=0
        self.it=0
        self.iu1=0
        self.iu2=0
        self.iu3=0
        self.iv=0
        self.im2=0
        self.im4=0
        self.igs=0
    
    def SetIt(self,value):
        self.it=value

    def SetIu2(self,value):
        self.iu2=value

    def SetIu3(self,value):
        self.iu3=value
    

class LennardJones:
    '''
    It contains some variable that are needed for the calculation.
    Instead of being evaluated over and over again, we compute them once and reuse
    '''
    def __init__(self,eolj,rolj):
        self.eolj=eolj
        self.rolj=rolj
        self.eox4=4*eolj
        self.ro2lj=np.square(rolj)
        self.ro6lj=np.power(self.ro2lj,3)
        self.ro12lj=np.square(self.ro6lj)
        self.dro6=6*self.ro6lj
        self.dro12=12*self.ro12lj
        self.romax=np.amax(rolj)

class HardSphere:
    '''
    Parameters used for the hard sphere model.
    '''
    def __init__(self,rhs):
        self.rhs=rhs
        self.rhs2=np.multiply(rhs,rhs)

def GetAtom(AtomList,ConstList,id):
    '''
    For the original file format of mobcal, the atoms is identifyed by its mass
    This function comapares the mass found in teh file with the database and set all
    the internal variable for that atom.
    If the atom is NOT in the database it is defaulted to a carbon atom and a warning is issued.
    Whether using a carbon atom as default is a good idea or not, I will let you decide
    '''
    for element in AtomList:
        if element.id==id:
            return element.Unpack()
    else:
        print("****** WARNING   WARNING   WARNING ******")
        print("One of the atoms listed is unknown, assuming carbon")
        print("****** WARNING   WARNING   WARNING ******")
        default=atom('Carbon',12.01,1.34e-3*ConstList.xe,3.043e-10,2.7e-10,12)
        return default.Unpack()

def rotate(vector,theta,phi,gamma,ConstList,switch,fout):
    '''
    Rotates the vector(s) provided
    '''
    if switch.iu2==1 or switch.iu3==1:  
        print('\n\n coordinates rotated by ROTATE\n\n theta={0: .4E} phi={1: .4E} gamma={2: .4E}\n'.format(theta*ConstList.cang,phi*ConstList.cang,gamma*ConstList.cang),file=fout)

    rz=R.from_rotvec(theta*np.array([0,0,1]))
    rx=R.from_rotvec(-phi*np.array([1,0,0]))
    rzb=R.from_rotvec(gamma*np.array([0,0,1]))
    newVector=rzb.apply(rx.apply(rz.apply(vector)))

    if switch.iu2==1:
        x=' '  
        print(9*x+"initial coordinates"+24*x+"new coordinates\n",file=fout)
        for v,rotv in zip(vector,newVector):
            print(' {: .4E} {: .4E} {: .4E}      {: .4E} {: .4E} {: .4E}'.format(v[0],v[1],v[2],rotv[0],rotv[1],rotv[2]),file=fout)    

    return newVector

def fcoord(fileIN,fileOUT,parmList,AtomList,switch):
    '''
    Read the input file. The format is the original mobcal format
    '''
    inList={
    "atoms": 0,
    "icoord": 0,
    "units": " ",
    "charges": " ",
    "cfact" :0,
    "label":" "
    }
    
    ion=molecule()

    #check the files are actually there
    try:
        fin=open(fileIN,"r")
    except IOError as e:
        print("Couldn't open file (%s)." % e)
        #return 0

    try:
        fout=open(fileOUT,"w")
    except IOError as e:
        print("Couldn't open file (%s)." % e)
        #return 0

    print("input file name = ",fileIN,file=fout)
    tmp=fin.readline()
    inList["label"]=tmp
    print("input file label =",tmp,file=fout,end="")
    tmp=fin.readline()
    inList["icoord"]=int(tmp)
    print("number of coordinate sets=", tmp,file=fout,end="")
    tmp=fin.readline()
    inList["atoms"]=int(tmp)
    print("number of atoms=",tmp,file=fout,end="")
    
    tmp=fin.readline()
    x=tmp.split()
    inList["units"]=x[0]
    if x[0]=='au':
        fout.write("coordinates in atomic units\n")
    elif x[0]=='ang':
        fout.write("coordinates in angstroms\n")
    else:
        fout.write("Coordinates selected not supported\n")
        #return 0

    tmp=fin.readline()
    x=tmp.split()
    inList["charges"]=x[0]
    if x[0]=='equal':
        fout.write("using a uniform charge distribution\n")
    elif x[0]=='calc':
        fout.write("using a calculated (non-uniform) charge distribution\n")
    elif x[0]=='none':
        fout.write("using no charge - only LJ interactions\n")
    else:
        fout.write("Charges model selected not supported\n")
        fin.close()
        fout.close()
        sys.exit(0)
        #return 0

    # DIFF: the following line is swicthed with the previous line  inthe original code
    tmp=fin.readline()
    inList["cfact"]=float(tmp)
    print("correction factor for coordinates = ", tmp,file=fout,end="")

    #Setting up some arrays before reading coords. Try to be consistent with original code as well as optimize a bit
    fx=np.zeros(inList["atoms"])
    fy=np.zeros(inList["atoms"])
    fz=np.zeros(inList["atoms"])
    imass=np.zeros(inList["atoms"],dtype=int)
    if inList["charges"]=='equal':
        pcharges=np.full(inList["atoms"],1/inList["atoms"])
    else:
        pcharges=np.zeros(inList["atoms"])
    xmass=np.zeros(inList["atoms"])
    eolj=np.zeros(inList["atoms"])
    rolj=np.zeros(inList["atoms"])
    rhs=np.zeros(inList["atoms"])

    #Reading atom coordinates starts here:
    for i in range(inList["atoms"]):
        tmp=fin.readline()
        x=tmp.split()
        fx[i]=float(x[0])
        fy[i]=float(x[1])
        fz[i]=float(x[2])
        imass[i]=int(np.rint(float(x[3])))
        if inList["charges"]=='calc':
            pcharges[i]=float(x[4])

    if inList["units"]=='au':
        fx=fx*0.52917706
        fy=fy*0.52917706
        fz=fz*0.52917706

    tcharge=np.sum(pcharges) #total charge
    acharge=np.sum(np.abs(pcharges)) #total absolute charge
    #DIFF: Original code only prints the charges is model==calc (see next 2 lines). I prefer always: helps catching bugs
    # if inList["charges"]=='calc':
    #     print("total charge = ",tcharge,"\ntotal absolute charge =",acharge,file=fout)
    print("total charge = ",tcharge,"\ntotal absolute charge =",acharge,file=fout)
    ion.SetCharges(tcharge,acharge)

    for i in range(inList["atoms"]):
        xmass[i],eolj[i],rolj[i],rhs[i]=GetAtom(AtomList,parmList,imass[i])
    tMass=np.sum(xmass)
    print("mass of ion = ",tMass,file=fout)
    ion.SetMass(tMass)
    
    lj=LennardJones(eolj,rolj)
    hs=HardSphere(rhs)

    if switch.iu1==1:
        print('initial coordinates \t\t\t mass \t  charge \t\t\t LJ parameters',file=fout)
    
    #The center of mass is used as origin of the reference frame
    fxo=np.sum(np.multiply(fx,xmass))/tMass
    fyo=np.sum(np.multiply(fy,xmass))/tMass
    fzo=np.sum(np.multiply(fz,xmass))/tMass
    print('center of mass coordinates = ',fxo,' ',fyo,' ',fzo,file=fout)

    Oxyz=np.zeros([inList["atoms"],3])   # original coordinates vector
    for i in range(inList["atoms"]):
        Oxyz[i][0]=(fx[i]-fxo)*1.e-10*inList["cfact"]
        Oxyz[i][1]=(fy[i]-fyo)*1.e-10*inList["cfact"]
        Oxyz[i][2]=(fz[i]-fzo)*1.e-10*inList["cfact"]

    if switch.iu1==1:
        for i in range(inList["atoms"]):
            print(fx[i],fy[i],fz[i],imass[i],pcharges[i],eolj[i]/parmList.xe,rolj[i]*1e+10,file=fout)
        print("\n")
    
    if inList["icoord"]==1:
        fin.close()

#    determine structural asymmetry parameter
    theta=0
    asymp=0

    for igamma in range(0,360,2):
        for iphi in range(0,180,2):
            xyzsum=0
            yzsum=0
            gamma=float(igamma/parmList.cang)
            phi=float(iphi/parmList.cang)
            rotVector=rotate(Oxyz,theta,phi,gamma,parmList,switch,fout)
            for ivec in rotVector:
                xyzsum=xyzsum+np.linalg.norm(ivec)
                yzsum=yzsum+np.linalg.norm(ivec[1:])
            hold=((parmList.pi/4)*xyzsum)/yzsum
            if(hold>asymp):
                asymp=hold

    InputData=infile(inList)
    atoms=AtomData(xmass,pcharges,Oxyz)
    return atoms,ion,InputData,asymp,lj,hs,fin,fout

def ncoord(fin,fout,parmList,AtomList,switch,ion,inputList):
    '''
    Read coordinates after the first set (if any). The format is the original mobcal format
    '''
    
    fx=np.zeros(inputList.atoms)
    fy=np.zeros(inputList.atoms)
    fz=np.zeros(inputList.atoms)
    imass=np.zeros(inputList.atoms)
    xmass=np.zeros(inputList.atoms)

    tmp=fin.readline()   #unused line

    #Reading atoms coordinates starts here:
    for i in range(inputList.atoms):
        tmp=fin.readline()
        x=tmp.split()
        fx[i]=float(x[0])
        fy[i]=float(x[1])
        fz[i]=float(x[2])
        imass[i]=int(np.rint(float(x[3])))

    if inputList.units=='au':
        fx=fx*0.52917706
        fy=fy*0.52917706
        fz=fz*0.52917706

    for i in range(inputList.atoms):
        xmass[i],eolj,rolj,rhs=GetAtom(AtomList,parmList,imass[i])
    
    tMass=np.sum(xmass)
    if tMass!=ion.TotalMass:
        print('masses do not add up')
        fin.close()
        fout.close()
        sys.exit(0)    
    
    #The center of mass is used as origin of the reference frame
    fxo=np.sum(np.multiply(fx,xmass))/tMass
    fyo=np.sum(np.multiply(fy,xmass))/tMass
    fzo=np.sum(np.multiply(fz,xmass))/tMass

    Oxyz=np.zeros([inputList.atoms,3])   # original coordinates vector
    for i in range(inputList.atoms):
        Oxyz[i][0]=(fx[i]-fxo)*1.e-10*inputList.cfact
        Oxyz[i][1]=(fy[i]-fyo)*1.e-10*inputList.cfact
        Oxyz[i][2]=(fz[i]-fzo)*1.e-10*inputList.cfact

#    determine structural asymmetry parameter
    theta=0
    asymp=0

    for igamma in range(0,360,2):
        for iphi in range(0,180,2):
            xyzsum=0
            yzsum=0
            gamma=float(igamma/parmList.cang)
            phi=float(iphi/parmList.cang)
            rotVector=rotate(Oxyz,theta,phi,gamma,parmList,switch,fout)
            for ivec in rotVector:
                xyzsum=xyzsum+np.linalg.norm(ivec)
                yzsum=yzsum+np.linalg.norm(ivec[1:])
            hold=((parmList.pi/4)*xyzsum)/yzsum
            if(hold>asymp):
                asymp=hold

    return Oxyz,asymp,fin,fout


def dljpot(x,y,z,vector,lj,charge,dipol):
    rx=0.0
    ry=0.0
    rz=0.0
    e00=0.0
    de00x=0.0
    de00y=0.0
    de00z=0.0
    sum1=0.0
    sum2=0.0
    sum3=0.0
    sum4=0.0
    sum5=0.0
    sum6=0.0
    dmax=2*lj.romax

    for ivec,ie,ir12,ir6,dr6,dr12,q in zip(vector,lj.eox4,lj.ro12lj,lj.ro6lj,lj.dro6,lj.dro12,charge):
        xx=x-ivec[0]
        xx2=xx*xx
        yy=y-ivec[1]
        yy2=yy*yy
        zz=z-ivec[2]
        zz2=zz*zz
        rxyz2=xx2+yy2+zz2
        rxyz=np.sqrt(rxyz2)
        if rxyz<dmax:
            dmax=rxyz
        rxyz3=rxyz2*rxyz
        rxyz5=rxyz3*rxyz2
        rxyz6=rxyz5*rxyz
        rxyz8=rxyz5*rxyz3
        rxyz12=rxyz6*rxyz6
        rxyz14=rxyz12*rxyz2
    #     LJ potential 
        e00=e00+(ie*((ir12/rxyz12)-(ir6/rxyz6)))
    #     LJ derivative
        de00=ie*((dr6/rxyz8)-(dr12/rxyz14))
        de00x=de00x+(de00*xx)
        de00y=de00y+(de00*yy)
        de00z=de00z+(de00*zz)
    #     ion-induced dipole potential
        if(q==0):
            continue
        rxyz3i=q/rxyz3
        rxyz5i=-3*q/rxyz5
        rx=rx+(xx*rxyz3i)
        ry=ry+(yy*rxyz3i)
        rz=rz+(zz*rxyz3i)
    #     ion-induced dipole derivative
        sum1=sum1+(rxyz3i+(xx2*rxyz5i))
        sum2=sum2+(xx*yy*rxyz5i)
        sum3=sum3+(xx*zz*rxyz5i)
        sum4=sum4+(rxyz3i+(yy2*rxyz5i))
        sum5=sum5+(yy*zz*rxyz5i)
        sum6=sum6+(rxyz3i+(zz2*rxyz5i))

    pot=e00-(dipol*((rx*rx)+(ry*ry)+(rz*rz)))
    dpotx=de00x-(dipol*((2.0*rx*sum1)+(2.*ry*sum2)+(2.*rz*sum3)))
    dpoty=de00y-(dipol*((2.0*rx*sum2)+(2.*ry*sum4)+(2.*rz*sum5)))
    dpotz=de00z-(dipol*((2.0*rx*sum3)+(2.*ry*sum5)+(2.*rz*sum6)))

    return pot,dpotx,dpoty,dpotz,dmax

def diffeq(tim,dt,w,parmList,ion,coord,lj,chargeList,dipole,Integrator,dw):
    '''
c     Integration subroutine - uses 5th order runge-kutta-gill to 
c     initiate and 5th order adams-moulton predictor-corrector to 
c     propagate. Parameter l is initially set to zero and then 
c     incremented to tell the subroutine when to switch between 
c     integration methods. DIFFEQ calls subroutine DERIV to define 
c     the equations of motion to be integrated.
    '''

    l=Integrator.GetStatus()

    if l==0:
        Integrator.Reset(dt)
    
    if l>=0:
        l=l+1
        Integrator.SetStatus(l)
#     This is the runge-kutta-gill part...the steps are broken up into
#     half steps to improve accuracy.
        w,dt,tim,dw,pot,dpotx,dpoty,dpotz,dmax=Integrator.ComputeRKG(w,ion,coord,lj,chargeList,dipole,tim)

#     This is the adams-moulton predictor-corrector part.
    if l<0:
        w,dt,tim,dw,pot,dpotx,dpoty,dpotz,dmax=Integrator.ComputeAMpc(w,dw,ion,coord,lj,chargeList,dipole,tim)

    return w,dt,tim,dw,pot,dpotx,dpoty,dpotz,dmax

def deriv(w,ion,coord,lj,chargeList,dipole):
    '''
c     Defines Hamilton's equations of motion as the time derivatives 
c     of the coordinates and momenta.
    '''
    dw=np.zeros(6)

#     From Hamilton's equations, the time derivatives of the coordinates
#     are the conjugates divided by the mass.
    dw[0]=w[1]/ion.mu
    dw[2]=w[3]/ion.mu
    dw[4]=w[5]/ion.mu

#     Hamilton's equations for the time derivatives of the momenta
#     evaluated by using the coordinate derivatives together with the
#     chain rule.
    x=w[0]
    y=w[2]
    z=w[4]
#    These are analytical derivatives.
    pot,dpotx,dpoty,dpotz,dmax=dljpot(x,y,z,coord,lj,chargeList,dipole)
    dw[1]=-dpotx
    dw[3]=-dpoty
    dw[5]=-dpotz

    return dw,pot,dpotx,dpoty,dpotz,dmax


def gsang(coord,theta,phi,gamma,chargeList,dipole,lj,v,b,switch,fout,ion,parmList):
    vy=-v
    vx=0.0
    vz=0.0
    d1=0.0
    istep=0
    vxyz=np.abs(vy)       ##NOTE: not used?
    if switch.it==1:
        print("\n specific trajectory parameters\n\n v ={0: .4E}    b ={1: 0.4E}".format(v,b),file=fout)
#     determine time step
    
    top=(v/95.2381)-0.5
    if v>=1000:
        top=10.0
    if v>=2000:
        top=10.0-((v-2000)*7.5e-3)
    if v>=3000:
        top=2.5
    dt1=top*parmList.dtsf1*1.0e-11/v
    dt2=dt1*parmList.dtsf2
    dt=dt1
    if switch.it==1:
        print(' time steps, dt1 ={0: .4E} dt2 ={1: .4E}'.format(dt1,dt2),file=fout)
    
#     determine trajectory start position
    e0=0.5*ion.mu*v*v
    x=b
    z=0.0
#    ymin=0.0
#    ymax=0.0
    ymax=np.amax(coord[:,1])
    ymin=np.amin(coord[:,1])
    ymax=ymax*1e10
    ymin=ymin*1e10
    iymin=np.trunc(ymin)-1
    iymax=np.trunc(ymax)+1
    id2=iymax
    y=float(id2)*1.0e-10
    pot,dpotx,dpoty,dpotz,dmax=dljpot(x,y,z,coord,lj,chargeList,dipole)

    if np.abs(pot/e0)<=parmList.sw1:
        while True:
            id2=id2-1
            y=float(id2)*1.0e-10
            pot,dpotx,dpoty,dpotz,dmax=dljpot(x,y,z,coord,lj,chargeList,dipole)
            if id2<iymin:
                if switch.it==1:
                    print(' trajectory not started - potential too small',file=fout)
                ang=0.0
                erat=1.0
                return ang,erat,d1,istep
            y=float(id2)*1.0e-10
            pot,dpotx,dpoty,dpotz,dmax=dljpot(x,y,z,coord,lj,chargeList,dipole)
            if np.abs(pot/e0)>=parmList.sw1:
                break
    else:    
        while True:
            id2=id2+10
            y=float(id2)*1.0e-10
            pot,dpotx,dpoty,dpotz,dmax=dljpot(x,y,z,coord,lj,chargeList,dipole)
            if np.abs(pot/e0)<=parmList.sw1:
                break
        
        while True:
            id2=id2-1
            y=float(id2)*1.0e-10
            pot,dpotx,dpoty,dpotz,dmax=dljpot(x,y,z,coord,lj,chargeList,dipole)
            if np.abs(pot/e0)>=parmList.sw1:
                break

    y=float(id2)*1.0e-10
    etot=e0+pot
    if switch.it==1:
        print(' trajectory start position ={0: .4E}'.format(y*1e10),file=fout)
    d1=y
#     initial coordinates and momenta
    w=np.zeros(6)
    w[0]=x
    w[1]=vx*ion.mu
    w[2]=y
    w[3]=vy*ion.mu
    w[4]=z
    w[5]=vz*ion.mu
    tim=0.0
    if switch.it==1:
        x=' '
        print('\n\n trajectory ns, x,  y,  z,  kin e, dt,    tot e',file=fout)
        print(16*x+'vx, vy, vz, pot e, pot/e0\n',file=fout)    
    
    #     initialize the time derivatives of the coordinates and momenta
    dw,pot,dpotx,dpoty,dpotz,dmax=deriv(w,ion,coord,lj,chargeList,dipole)
    ns=0
    nw=0
    ang=0.
    erat=0.0
    #l=0
    #print(dw)
    Integrator=IntegratorState(dt)
    while True:
        while True:
            while True:
                while True:
                    w,dt,tim,dw,pot,dpotx,dpoty,dpotz,dmax=diffeq(tim,dt,w,parmList,ion,coord,lj,chargeList,dipole,Integrator,dw)
                    nw=nw+1
                    if nw==parmList.inwr:
                        break
                ns=ns+nw
                nw=0
            #     print out the trajectory coordinates and velocities
                if switch.it==1:
                    e=w[1]**2/(2.0*ion.mu)+w[3]**2/(2.0*ion.mu)+w[5]**2/(2.0*ion.mu)
                    x=' '
                    #print(" {:5d}".format(ns)," {: 11.4E}".format(w[0])," {: .4e}".format(w[2])," {: .4e}".format(w[4])," {: .4e}".format(e)," {: .4e}".format(dt)," {: .4e}".format(pot+e),file=fout)
                    print(" {:5d} {: .4E} {: .4E} {: .4E} {: .4E} {: .4E} {: .4E}".format(ns,w[0],w[2],w[4],e,dt,pot+e),file=fout)
                    print(7*x+"{: .4E} {: .4E} {: .4E} {: .4E} {: .4E}".format(dw[0],dw[2],dw[4],pot,np.abs(pot/e0)),file=fout)

            #     check if trajectory has become "lost" (too many steps)

                if ns>parmList.traj_lost:
                    print(' trajectory lost: b ={0: .4E} v={1: .4E}'.format(b,v),file=fout)
                    ang=parmList.pi/2.0
                    e=0.5*ion.mu*(dw[0]**2+dw[2]**2+dw[4]**2)
                    erat=(e+pot)/etot
                    istep=ns
                    return ang,erat,d1,istep

            #     check if the trajectory is finished
                if dmax>=lj.romax:
                    break
            if np.abs(pot/e0)>parmList.sw2 and dt==dt1:
                dt=dt2
                Integrator.SetStatus(0)
            if np.abs(pot/e0)<parmList.sw2 and dt==dt2:
                dt=dt1
                Integrator.SetStatus(0)
            if np.abs(pot/e0)<=parmList.sw1:
                break
        if ns>=50:
            break
    istep=ns
    #     determine scattering angle 
    if(dw[0]>0.0):        
        num=dw[2]*(-v)
        den=v*np.sqrt(dw[0]**2+dw[2]**2+dw[4]**2)
        ang=np.arccos(num/den)

    if(dw[0]<0.0):
        num=dw[2]*(-v)
        den=v*np.sqrt(dw[0]**2+dw[2]**2+dw[4]**2)
        ang=-1*np.arccos(num/den)
    
    #     check for energy conservation
    e=0.5*ion.mu*(dw[0]**2+dw[2]**2+dw[4]**2)
    erat=(e+pot)/etot
    if erat<1.01 and erat>0.99:
        return ang,erat,d1,istep  #ang
    print('\n energy not conserved: e ratio ={0: .4E} v ={1: .4E} b ={2: .4E}'.format(erat,v,b),file=fout)
    print(' gst2 ={0: .4E} theta ={1: .4E} phi ={2: .4E} gamma ={3: .4E}'.format(0.5*ion.mu*v*v/parmList.eo,theta*parmList.cang,phi*parmList.cang,gamma*parmList.cang),file=fout)
    if switch.ip==1:
        print('')
    parmList.ifailc=parmList.ifailc+1   ## make ifailc external to list
    if parmList.ifailc==parmList.ifail:
        fout.close()
        print('Energy not conserved')
        sys.exit(0)
    return ang,erat,d1,istep

def rantate(vector,parmList,switch,fout,RngGen):
    '''
c     Rotates the cluster/molecule to a random orientation.  
    NOTE: here I have used rando_py generated by the script.
    '''

    rnt=RngGen.rand()
    rnp=RngGen.rand()
    rng=RngGen.rand()

    theta=rnt*2.0*parmList.pi
    phi=np.arcsin((rnp*2.0)-1.0)+(parmList.pi/2.0)
    gamma=rng*2.0*parmList.pi
    newVector=rotate(vector,theta,phi,gamma,parmList,switch,fout)
    return newVector,theta,phi,gamma


def mobil2(coordList,chargeList,fout,parmList,switch,lj,dipole,ion,mconst,iic,RngGen):
    if switch.im2==0:
        print('\n mobility calculation by MOBIL2 (trajectory method)\n',file=fout)
        print(' global trajectory parameters\n\n sw1 ={: .4E}       sw2 ={: .4E}'.format(parmList.sw1,parmList.sw2),file=fout)
        print(' dtsf1 ={: .4E}     dtsf2 ={: .4E}'.format(parmList.dtsf1,parmList.dtsf2),file=fout)
        print(' inwr ={: 3d}              ifail ={: 5d}'.format(parmList.inwr,parmList.ifail),file=fout)

    switch.SetIt(0)
    switch.SetIu2(0)

    #     determine maximum extent and orient along x axis
    
    if switch.im2==0:
        print('\n maximum extent orientated along x axis',file=fout)

    rmax=0
    count=0
    ihold=0
    for ivec in coordList:
        tmp=np.linalg.norm(ivec)
        if tmp>rmax:
            rmax=tmp
            vector=ivec
            ihold=count
        count=count+1
    
    rzy=np.sqrt(vector[2]**2+vector[1]**2)
    phi=np.arccos(vector[2]/rzy)
    phi=phi+(0.5*parmList.pi)  # I want to make the z component =0, thus shit to y-axis
    if vector[1]<0:
        phi=(2*parmList.pi)-phi
    phi=(2.*parmList.pi)-phi
    theta=0.0 
    gamma=0.0
    
    newVector=rotate(coordList,theta,phi,gamma,parmList,switch,fout)
    rotVector=newVector[ihold]
    rxy=np.sqrt(rotVector[0]**2+rotVector[1]**2)
    gamma=np.arccos(rotVector[0]/rxy)
    if rotVector[1]<0:
        gamma=(2*parmList.pi)-gamma
    gamma=(2.*parmList.pi)-gamma

    if(switch.im2==0):
        switch.SetIu3(1)
    if(switch.ip==1):
        switch.SetIu2(1)

    newVector=rotate(coordList,theta,phi,gamma,parmList,switch,fout)
    switch.SetIu3(0)
    switch.SetIu2(0)
    rotVector=newVector[ihold]
    hold=rotVector[0]/rmax

    if hold<0.9999999999 or hold>1.0000000001 or rotVector[1]>1.0e-20 or rotVector[2]>1.0e-20 or rotVector[1]<-1.0e-20 or rotVector[2]<-1.0e-20:
        print('\n Problem orientating along x axis\n',file=fout)
        for ivec in newVector:
            print(ivec[0],ivec[1],ivec[2],np.linalg.norm(ivec),file=fout)

    
    #     determine rmax, emax, and r00 along x, y, and z directions    
    if switch.ip==1:
        print("\n",file=fout)
    irn=1000
    ddd=(rmax+lj.romax)/float(irn)

    y=0.0
    z=0.0
    emaxx=0.0
    for ir in range(irn):
        x=rmax+lj.romax-(float(ir)*ddd)
        pot,dpotx,dpoty,dpotz,dmax=dljpot(x,y,z,newVector,lj,chargeList,dipole)
        if pot>0:
            break
        r00x=x
        if  pot<emaxx:
            rmaxx=x
            emaxx=pot
    if switch.im2==0:
        print(' along x axis emax ={: .4E}eV rmax ={: .4E}A r00 ={: .4E}A'.format(emaxx/parmList.xe,rmaxx*1.0e10,r00x*1.0e10),file=fout)
    
    x=0.0
    z=0.0
    emaxy=0.0
    for ir in range(irn):
        y=rmax+lj.romax-(float(ir)*ddd)
        pot,dpotx,dpoty,dpotz,dmax=dljpot(x,y,z,newVector,lj,chargeList,dipole)
        if pot>0:
            break
        r00y=y
        if  pot<emaxy:
            rmaxy=y
            emaxy=pot
    if switch.im2==0:
        print(' along y axis emax ={: .4E}eV rmax ={: .4E}A r00 ={: .4E}A'.format(emaxy/parmList.xe,rmaxy*1.0e10,r00y*1.0e10),file=fout)

    x=0.0
    y=0.0
    emaxz=0.0
    for ir in range(irn):
        z=rmax+lj.romax-(float(ir)*ddd)
        pot,dpotx,dpoty,dpotz,dmax=dljpot(x,y,z,newVector,lj,chargeList,dipole)
        if pot>0:
            break
        r00z=z
        if  pot<emaxz:
            rmaxz=z
            emaxz=pot
    if switch.im2==0:
        print(' along z axis emax ={: .4E}eV rmax ={: .4E}A r00 ={: .4E}A\n'.format(emaxz/parmList.xe,rmaxz*1.0e10,r00z*1.0e10),file=fout)

#     set-up integration over gst
    tst=parmList.xk*ion.temperature/parmList.eo
    if switch.im2==0:
        print('\n t*={: .4E}'.format(tst),file=fout)
    tst3=tst*tst*tst
    dgst=5e-7*6*np.sqrt(tst)
    gst=dgst
    sum=0.0
    sum2=0.0
    sum1=np.sum(np.sqrt(np.arange(1,parmList.inp+1)))
    if switch.im2==0:
        x=' '
        print('\n\n set-up gst integration - integration over velocity',file=fout)
        print('\n     pgst'+8*x+'wgst'+9*x+'v'+9*x+'ke/kt'+7*x+'gst^5*'+5*x+'frac of\n'+48*x+'exp(gst^2/tst)'+3*x+'sum\n',file=fout)
    
    wgst=np.zeros(parmList.vec_dim)
    pgst=np.zeros(parmList.vec_dim)
    #count=0
    for i in np.arange(1,parmList.inp+1):
        hold1=np.sqrt(float(i))
        hold2=np.sqrt(float(i-1))
        sum2=sum2+hold2
        wgst[i-1]=hold1/sum1      # CAREFUL if number. python is 0-based, but fortran is 1-based
        gstt=tst3*(sum2+(hold1/2))/sum1

        while True:
            sum=sum+(np.exp(-gst*gst/tst)*gst*gst*gst*gst*gst*dgst)
            gst=gst+dgst
            if sum>gstt:
                pgst[i-1]=gst-(dgst/2.0)
                break
            if sum==gstt:
                break

        hold1=np.sqrt((pgst[i-1]*pgst[i-1]*parmList.eo)/(0.5*ion.mu))
        hold2=0.5*ion.mu*hold1*hold1/(parmList.xk*ion.temperature)
        hold3=np.exp(-pgst[i-1]*pgst[i-1]/tst)*pgst[i-1]**5

        if switch.im2==0:
            print(' {: .4E} {: .4E} {: .4E} {: .4E} {: .4E} {: .4E}'.format(pgst[i-1],wgst[i-1],hold1,hold2,hold3,sum/tst3),file=fout)            
            # print(count,"-",pgst[i-1],wgst[i-1],hold1,hold2,hold3,sum/tst3)
            # count=count+1

#     determine b2max
    b2max=np.zeros(parmList.vec_dim)
    cosx=np.zeros(500)
    dbst2=1.0
    dbst22=dbst2/10.0
    cmin=0.0005
    if switch.im2==0:
        print('\n\n set up b2 integration - integration over impact parameter\n\n minimum value of (1-cosX) ={: .4E}\n'.format(cmin),file=fout)
    gst2=np.square(pgst)
    vList=np.sqrt((gst2*parmList.eo)/(0.5*ion.mu))
    for ig in range(parmList.inp-1,-1,-1):
        ibst=np.trunc(rmaxx/parmList.ro)-6
        if ig<parmList.inp-1:
            ibst=int(np.trunc(b2max[ig+1]/dbst2))-6
        if ibst<0:
            ibst=0
        if switch.ip==1:
            x=' '
            print('\n gst2 ={: .4E} v ={: .4E}'.format(gst2[ig],vList[ig])+'\n'+6*x+'b'+10*x+'bst2'+7*x+'X ang'+7*x+'cos(X)'+6*x+'e ratio',file=fout)
        while True:        
            bst2=dbst2*float(ibst)
            b=parmList.ro*np.sqrt(bst2)
            
            ang,erat,d1,istep=gsang(newVector,theta,phi,gamma,chargeList,dipole,lj,vList[ig],b,switch,fout,ion,parmList)
            #print (ibst,b,ang,np.cos(ang))
            cosx[ibst]=1.0-np.cos(ang)
            if(switch.ip==1):
                print(' {: .4E} {: .4E} {: .4E} {: .4E} {: .4E}'.format(b,bst2,ang,cosx[ibst],erat),file=fout)

            if ibst<5 or ( ibst>=5 and (not (cosx[ibst]<cmin and cosx[ibst-1]<cmin and cosx[ibst-2] < cmin and cosx[ibst-3]<cmin and cosx[ibst-4]<cmin))):
                ibst=ibst+1
                if ibst>=500:
                    print(' ibst greater than 500')
                    fout.close()
                    sys.exit(0)
            else:
                break
        b2max[ig]=float(ibst-5)*dbst2
        while True:
            b2max[ig]=b2max[ig]+dbst22
            b=parmList.ro*np.sqrt(b2max[ig])
            
            ang,erat,d1,istep=gsang(newVector,theta,phi,gamma,chargeList,dipole,lj,vList[ig],b,switch,fout,ion,parmList)
            if (1.0-np.cos(ang)<=cmin):
                break
    if switch.im2==0:
        x=' '
        print('\n'+5*x+'gst'+11*x+'b2max/ro2'+9*x+'b/A\n',file=fout)
        for ig in range(parmList.inp):
            print(' {: .4E}     {: .4E}     {: .4E}'.format(pgst[ig],b2max[ig],parmList.ro*np.sqrt(b2max[ig])*1.0e10),file=fout)
            

#     Calculate Omega(1,1)*, Omega(1,2)*, Omega(1,3)*, and Omega(2,2)*
#     by integrating Q(1)* or Q(2)* over all orientations, and initial 
#     relative velocities.
    if(switch.im2==0):
        print('\n\n number of complete cycles (itn) ={:6d}'.format(parmList.itn),file=fout)
        print(' number of velocity points (inp) ={:6d}'.format(parmList.inp),file=fout)
        print(' number of random points (imp) ={:6d}'.format(parmList.imp),file=fout)
        print(' total number of points ={:7d}\n'.format(parmList.itn*parmList.inp*parmList.imp),file=fout)
    if switch.ip==1:
        print(' start mobility calculation',file=fout)
    
    q1st=np.zeros(parmList.inp)
    q2st=np.zeros(parmList.inp)
    om11st=np.zeros(parmList.itn)
    om12st=np.zeros(parmList.itn)
    om13st=np.zeros(parmList.itn)
    om22st=np.zeros(parmList.itn)

    for ic in range(parmList.itn):
        if switch.ip==1:
            print('\n cycle number, ic ={:3d}'.format(ic+1),file=fout)
        # DIFF : next 2 lines unecessary in original code? The are only useful if switch.ip=1. So I added those there
        #   gst2=pgst(ig)*pgst(ig)
        #   v=dsqrt((gst2*eo)/(0.5d0*mu))
        for ig in range(parmList.inp):
            if switch.ip==1:
                # gst2=pgst[ig]*pgst[ig]
                # v=np.sqrt((gst2*parmList.eo)/(0.5*ion.mu))
                print('\n ic ={:3d} ig ={:4d} gst2 ={: .4E} v ={: .4E}'.format(ic+1,ig+1,gst2[ig],vList[ig]),file=fout)
            temp1=0.0
            temp2=0.0
            for im in range(parmList.imp):
                if switch.ip==1 and im==0:
                    x=' '
                    print('\n'+5*x+'b/A'+8*x+'ang'+6*x+'(1-cosX)'+4*x+'e ratio'+4*x+'theta'+7*x+'phi'+7*x+'gamma',file=fout)
                rnb=RngGen.rand()
                newVector,theta,phi,gamma=rantate(coordList,parmList,switch,fout,RngGen)
                bst2=rnb*b2max[ig]
                b=parmList.ro*np.sqrt(bst2)
                if switch.igs==1:
                    ftemp=open('hold_py',"w")
                    print(iic,ic+1,ig+1,im+1,file=ftemp)
                    print(vList[ig],b,file=ftemp)
                    print(theta*parmList.cang,phi*parmList.cang,gamma*parmList.cang,file=ftemp)
                    ftemp.close()
                ang,erat,d1,istep=gsang(newVector,theta,phi,gamma,chargeList,dipole,lj,vList[ig],b,switch,fout,ion,parmList)
                #print("ang:",ang)
                hold1=1.0-np.cos(ang)
                hold2=np.sin(ang)*np.sin(ang)
                if switch.ip==1:
                    print(' {: .4E}{: .4E}{: .4E}{: .4E}{: .4E}{: .4E}{: .4E}'.format(b*1.e10,ang*parmList.cang,hold1,erat,theta*parmList.cang,phi*parmList.cang,gamma*parmList.cang),file=fout)
                temp1=temp1+(hold1*b2max[ig]/float(parmList.imp))
                temp2=temp2+(1.5*hold2*b2max[ig]/float(parmList.imp))
            om11st[ic]=om11st[ic]+(temp1*wgst[ig])
            om12st[ic]=om12st[ic]+(temp1*pgst[ig]*pgst[ig]*wgst[ig]*(1.0/(3.0*tst)))
            om13st[ic]=om13st[ic]+(temp1*(pgst[ig]**4)*wgst[ig]*(1.0/(12.0*tst*tst)))
            om22st[ic]=om22st[ic]+(temp2*pgst[ig]*pgst[ig]*wgst[ig]*(1.0/(3.0*tst)))
            q1st[ig]=q1st[ig]+temp1
            q2st[ig]=q2st[ig]+temp2
            if switch.ip==1:
                print('\n v ={: .4E}     q1st ={: .4E}\n'.format(vList[ig],q1st[ig]),file=fout)
        if switch.ip==1:
            print('\n OMEGA(1,1)*={: .4E}\n'.format(om11st[ic]),file=fout)

    #     calculate running averages
    temp=1.0/(mconst/(np.sqrt(ion.temperature)*om11st*parmList.pi*parmList.ro2))
    hold1=np.cumsum(om11st)
    hold2=np.cumsum(temp)

    if switch.im2==0:
        x=' '
        print('\n summary of mobility calculations\n\n cycle'+5*x+'cs/A^2'+6*x+'avge cs/A^2'+8*x+'Ko^-1'+7*x+'avge Ko^-1',file=fout)
        for icc in range(1,parmList.itn+1):
            print(' {: 3d}    {: .4E}    {: .4E}    {: .4E}    {: .4E}'.format(icc,om11st[icc-1]*parmList.pi*parmList.ro2*1.e20,hold1[icc-1]*parmList.pi*parmList.ro2*1e20/float(icc),temp[icc-1],hold2[icc-1]/float(icc)),file=fout)
        print('\n\n average values for q1st\n\n'+5*x+'gst2'+8*x+'wgst'+8*x+'q1st',file=fout)
        for ig in range(parmList.inp):
            print(' {: .4E} {: .4E} {: .4E}'.format(pgst[ig]*pgst[ig],wgst[ig],q1st[ig]/float(parmList.inp)),file=fout)
    
    mom11st=np.sum(om11st)
    mom12st=np.sum(om12st)
    mom13st=np.sum(om13st)
    mom22st=np.sum(om22st)
    mom11st=mom11st/float(parmList.itn)
    mom12st=mom12st/float(parmList.itn)
    mom13st=mom13st/float(parmList.itn)
    mom22st=mom22st/float(parmList.itn)
    sdom11st=0.0
    for item in om11st:
        hold=mom11st-item
        sdom11st=sdom11st+(hold*hold)
    sdom11st=np.sqrt(sdom11st/float(parmList.itn))
    sterr=sdom11st/np.sqrt(float(parmList.itn))

    if switch.im2==0:
        print('\n\n mean OMEGA*(1,1) ={: .4E}\n standard deviation ={: .4E}\n standard error of mean ={: .4E}'.format(mom11st,sdom11st,sterr),file=fout)
    cs=mom11st*parmList.pi*parmList.ro2
    sdevpc=100.0*sdom11st/mom11st
    
    #     Use omegas to obtain higher order correction factor to mobility

    ayst=mom22st/mom11st
    best=((5.0*mom12st)-(4.0*mom13st))/mom11st
    cest=mom12st/mom11st
    term=((4.0*ayst)/(15.0))+(.50*((ion.TotalMass-ion.mGas)**2.0)/(ion.mGas*ion.TotalMass))
    u2=term-(.083330*(2.40*best+1.0)*(ion.mGas/ion.TotalMass))
    w=(ion.mGas/ion.TotalMass)
    delta=((((6.0*cest)-5.0)**2.0)*w)/(60.0*(1.0+u2))
    f=1.0/(1.0-delta)
    if switch.im2==0:
        x=' '
        print('\n\n f value for second order correction={: .4E}'.format(f),file=fout)
        print(' (integrations for second order correction are not',file=fout)
        print(' accurate, check if correction becomes significant)',file=fout)
        print('\n omega*12 ={: .4E}  omega*13 ={: .4E}  omega*22 ={: .4E}'.format(mom12st,mom13st,mom22st),file=fout)
        print(7*x+'u2 ={: .4E}         w ={: .4E}     delta ={: .4E}'.format(u2,w,delta),file=fout)
    mob=(mconst*f)/(np.sqrt(ion.temperature)*cs)
    print('\n\n average (second order) TM mobility ={: .4E}'.format(mob),file=fout)
    print(' inverse average (second order) TM mobility ={: .4E}'.format(1.0/mob),file=fout)
    print(' average TM cross section ={: .4E}'.format(cs*1.e20),file=fout)

    return mob,cs,sdevpc

    
def MapCommonsConstants(f_pack,switch,constants,mu,M,dipol,mobility,cfact,inatom,icoord,iic,lj):
    '''
    Set the common blocks /constants/,/printswitch/ and /trajectory/
    from the corresponding python data structures
    '''
    f_pack.printswitch.ip=switch.ip
    f_pack.printswitch.it=switch.it
    f_pack.printswitch.iu1=switch.iu1
    f_pack.printswitch.iu2=switch.iu2
    f_pack.printswitch.iu3=switch.iu3
    f_pack.printswitch.iv=switch.iv
    f_pack.printswitch.im2=switch.im2
    f_pack.printswitch.im4=switch.im4
    f_pack.printswitch.igs=switch.igs
    f_pack.constants.mu=mu
    f_pack.constants.ro=constants.ro
    f_pack.constants.eo=constants.eo
    f_pack.constants.pi=constants.pi
    f_pack.constants.cang=constants.cang
    f_pack.constants.ro2=constants.ro2
    f_pack.constants.dipol=dipol
    f_pack.constants.emax=None             # Only used in the function potent() that however is NOT used in "vanilla" Mobcal
    f_pack.constants.m1=4.0026       
    f_pack.constants.m2=M                 # This is the mass of the ion
    f_pack.constants.xe=constants.xe
    f_pack.constants.xk=constants.xk
    f_pack.constants.xn=constants.xn
    f_pack.constants.xeo=constants.xeo
    f_pack.constants.xmv=constants.xmv
    f_pack.constants.mconst=mobility
    f_pack.constants.correct=cfact
    f_pack.constants.romax=lj.romax
    f_pack.constants.inatom=inatom
    f_pack.constants.icoord=icoord
    f_pack.constants.iic=iic
    f_pack.trajectory.sw1=constants.sw1
    f_pack.trajectory.sw2=constants.sw2
    f_pack.trajectory.dtsf1=constants.dtsf1
    f_pack.trajectory.dtsf2=constants.dtsf2
    f_pack.trajectory.cmin=constants.cmin
    f_pack.trajectory.ifail=constants.ifail
    f_pack.trajectory.ifailc=constants.ifailc
    f_pack.trajectory.inwr=constants.inwr

def MapLJConstants(f_pack,lj):
    '''
    Set the common block /ljparameters/from the corresponding python data structures
    Fortran has a fixed size for arrays = 1000
    '''
    f_pack.ljparameters.eolj=np.zeros(1000)
    f_pack.ljparameters.rolj=np.zeros(1000)
    f_pack.ljparameters.eox4=np.zeros(1000)
    f_pack.ljparameters.ro6lj=np.zeros(1000)
    f_pack.ljparameters.ro12lj=np.zeros(1000)
    f_pack.ljparameters.dro6=np.zeros(1000)
    f_pack.ljparameters.dro12=np.zeros(1000)
        
    for c,i in enumerate(lj.eolj):
        f_pack.ljparameters.eolj[c]=lj.eolj[c]
        f_pack.ljparameters.rolj[c]=lj.rolj[c]
        f_pack.ljparameters.eox4[c]=lj.eox4[c]
        f_pack.ljparameters.ro6lj[c]=lj.ro6lj[c]
        f_pack.ljparameters.ro12lj[c]=lj.ro12lj[c]
        f_pack.ljparameters.dro6[c]=lj.dro6[c]
        f_pack.ljparameters.dro12[c]=lj.dro12[c]

def MapCoords(f_pack,coords):
    for c,i in enumerate(coords):
        f_pack.coordinates.ox[c]=i[0]
        f_pack.coordinates.oy[c]=i[1]
        f_pack.coordinates.oz[c]=i[2]

def MapCharges(f_pack,charges):
    for c,i in enumerate(charges):
        f_pack.charge.pcharge[c]=i

#############################    
##           MAIN          ##
#############################
inFileName="a10A1.mfj"
outFileName="a10A1_py.out"
Rseed=43

ConstList=constants()
printDebug=printSwitch()
#id is used to associated atom type to atom "mass" in input file. In mobcal atoms are identified by their mass and not symbol
AtomList=(
    atom('Hydrogen',1.008,0.65e-03*ConstList.xe,2.38e-10,2.2e-10,1),
    atom('Carbon',12.01,1.34e-3*ConstList.xe,3.043e-10,2.7e-10,12),
    atom('Nitrogen',14.01,1.34e-3*ConstList.xe,3.043e-10,2.7e-10,14),
    atom('Oxygen',16.00,1.34e-3*ConstList.xe,3.043e-10,2.7e-10,16),
    atom('Sodium',22.99,0.0278e-3*ConstList.xe,(3.97/1.12246)*1e-10,2.853e-10,23),
    atom('Silicon',28.09,1.35e-3*ConstList.xe,3.5e-10,2.95e-10,28),
    atom('Sulfur',32.06,1.35e-3*ConstList.xe,3.5e-10,3.5e-10,32),
    atom('Iron',55.85,1.35e-3*ConstList.xe,3.5e-10,3.5e-10,56)
)

# LJ scaling parameters
atoms,ion,InputData,tmp_asymp,lj,hs,fin,fout=fcoord(inFileName,outFileName,ConstList,AtomList,printDebug)

print(' Lennard-Jones scaling parameters: eo={: .4E} ro={: .4E}'.format(ConstList.eo/ConstList.xe,ConstList.ro*1e+10),file=fout)


    #  Constant for ion-induced dipole potential

    #  Polarizability of helium = 0.204956d-30 m3
    #  xeo is permitivity of vacuum, 8.854187817d-12 F.m-1

dipole=ConstList.xe**2*0.204956e-30/(8*ConstList.pi*ConstList.xeo)
ion.SetDipole(dipole)
print(' dipole constant ={: .4E}'.format(ion.dipole),file=fout)

    # Mass constants
ion.SetMassGas(4.0026,ConstList.xn*1000)

    # Mobility constant

mconst=np.sqrt(18*ConstList.pi)/16
mconst=mconst*np.sqrt(ConstList.xn*1000)*np.sqrt((1/ion.mGas)+(1/ion.TotalMass))
mconst=mconst*ConstList.xe/np.sqrt(ConstList.xk)
dens=ConstList.xn/ConstList.xmv
mconst=mconst/dens
ion.SetMobility(mconst)
print(' mobility constant ={: .4E}'.format(ion.mobility),file=fout)
print(' temperature ={: .4E}'.format(ion.temperature),file=fout)


#DIFF: In the original code follows an initialization of the random number generator.
# Here I am using numpy, so that section is unnecessary

RngGen=np.random.RandomState(seed=Rseed)

#tmm=np.zeros(InputData.icoord)
#tmc=np.zeros(InputData.icoord)
asympp=np.zeros(InputData.icoord)
ehsc=np.zeros(InputData.icoord)
ehsm=np.zeros(InputData.icoord)
pac=np.zeros(InputData.icoord)
pam=np.zeros(InputData.icoord)
asympp[0]=tmp_asymp

####
imm=0
tmmob=0
immmin=0
immmax=0
###
###########################
## Set Python parameters ##
###########################
InputData.icoord=1
ConstList.ipr=2
ConstList.inp=2
ConstList.itn=2
ConstList.imp=2
fout_t_py=open("out.python.dat","w") # file with the result for python
printDebug.ip=1
printDebug.igs=1
###########################
## Set Fortran parameters ##
###########################
rando_f=np.random.RandomState(seed=43)
mobil2_f.xrand=rando_f.rand
MapCommonsConstants(mobil2_f,printDebug,ConstList,ion.mu,ion.TotalMass,dipole,ion.mobility,InputData.cfact,InputData.atoms,InputData.icoord,1,lj)
MapLJConstants(mobil2_f,lj)
MapCoords(mobil2_f,atoms.Coords)
MapCharges(mobil2_f,atoms.Charges)
#tmm_f=np.zeros(InputData.icoord)
#tmc_f=np.zeros(InputData.icoord)

fout_py=open("python_file.dat","w") # file with the result for python
fout_f=open("fortran_file.dat","w") # file with the result for fortran
fout_diff=open("diff_file.dat","w") # file with the difference of the two files above


for iic in range(InputData.icoord):
    print("",file=fout)
    if InputData.icoord > 0:
        print('\n coordinate set ={:5d}'.format(iic+1),file=fout)
    print('\n structural asymmetry parameter ={: .4E}'.format(asympp[iic]),file=fout)

    mobil2_f.constants.iic=iic
    tmm,tmc,sdevpc=mobil2(atoms.Coords,atoms.Charges,fout_t_py,ConstList,printDebug,lj,ion.dipole,ion,mconst,iic,RngGen)
    print(tmm,tmc,sdevpc,file=fout_py)
    tmm_f,tmc_f,sdevpc_f=mobil2_f.mobil2(ion.temperature,ConstList.itn,ConstList.inp,ConstList.imp)
    print(tmm_f,tmc_f,sdevpc_f,file=fout_f)
    print(tmm_f-tmm,tmc_f-tmc,sdevpc_f-sdevpc,file=fout_diff)

    if(imm<immmin):
        immmin=imm
    if(imm>immmax):
        immmax=imm  
   
    if iic<InputData.icoord-1:
        Oxyz,asympp[iic+1],fin,fout=ncoord(fin,fout,ConstList,AtomList,printDebug,ion,InputData)
        atoms.UpdatePosition(Oxyz)
        MapCoords(mobil2_f,atoms.Coords)
    printDebug.im2=1
    printDebug.im4=1

if not fin.closed:
    fin.close()

fout.close()
fout_t_py.close()
fout_py.close()
fout_f.close()
fout_diff.close()
