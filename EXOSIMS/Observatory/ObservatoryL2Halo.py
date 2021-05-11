from EXOSIMS.Prototypes.Observatory import Observatory
import astropy.units as u
from astropy.time import Time
import numpy as np
import os, inspect
import scipy.interpolate as interpolate
import scipy.integrate as itg
try:
    import cPickle as pickle
except:
    import pickle
from scipy.io import loadmat

class ObservatoryL2Halo(Observatory):
    """ Observatory at L2 implementation. 
    The orbit method from the Observatory prototype is overloaded to implement
    a space telescope on a halo orbit about the Sun-Earth L2 point. This class

    Orbit is stored in pickled dictionary on disk (generated by MATLAB
    code adapted from E. Kolemen (2008).  Describes approx. 6 month halo
    which is then patched for the entire mission duration).
    
    """

    def __init__(self, equinox=60575.25, haloStartTime=0, SRP=True, orbit_datapath=None, **specs):
    
        # run prototype constructor __init__ 
        Observatory.__init__(self,**specs)
        # orbit_datapath = 'D:/EXOSIMS/EXOSIMS/Observatory/haloPath/L2_halo_orbit_six_month.p'
        self.SRP = SRP
        self.haloStartTime = haloStartTime*u.d
        
        # set equinox value
        if isinstance(equinox,Time):
            self.equinox = equinox
        else:
            self.equinox = Time(np.array(equinox, ndmin=1, dtype=float),
                    format='mjd', scale='tai')
        
        needToUpdate = False
        keysHalo = ['te','t','state','x_lpoint','mu']
        
        # find and load halo orbit data in heliocentric ecliptic frame
        if orbit_datapath is None:
            self.vprint('    orbitdatapath none')
            filename = 'L2_halo_orbit_six_month.p'
            orbit_datapath = os.path.join(self.cachedir, filename)
            
        if os.path.exists(orbit_datapath):
            self.vprint('    orbitdatapath exists')
            try:
                with open(orbit_datapath, "rb") as ff:
                    halo = pickle.load(ff)
            except UnicodeDecodeError:
                with open(orbit_datapath, "rb") as ff:
                    halo = pickle.load(ff,encoding='latin1')
            try:
                for x in keysHalo: halo[x]
            except:
                self.vprint("Relevant keys not found, updating pickle file.")
                needToUpdate = True
            
        if not os.path.exists(orbit_datapath) or needToUpdate:
            self.vprint('    orbitdatapath need to update')
            orbit_datapath = os.path.join(self.cachedir, filename)
            matname = 'L2_halo_orbit_six_month.mat'
            classpath = os.path.split(inspect.getfile(self.__class__))[0]
            mat_datapath = os.path.join(classpath, matname)
            if not os.path.exists(mat_datapath):
                raise Exception("Orbit data file not found.")
            else:
                halo = loadmat(mat_datapath)
                with open(orbit_datapath, 'wb') as ff:
                    pickle.dump(halo, ff)
        self.vprint(orbit_datapath)
        # unpack orbit properties in heliocentric ecliptic frame 
        self.mu = halo['mu'][0][0]
        self.m1 = float(1-self.mu)
        self.m2 = self.mu
        self.period_halo = halo['te'][0,0]/(2.*np.pi)
        self.t_halo = halo['t'][:,0]/(2*np.pi)*u.year # 2\pi = 1 sideral year
        self.r_halo = halo['state'][:,0:3]*u.AU
        self.v_halo = halo['state'][:,3:6]*u.AU/u.year*(2.*np.pi)
        # position wrt Earth
        self.r_halo[:,0] -= 1.*u.AU
        
        # create interpolant for position (years & AU units)
        self.r_halo_interp = interpolate.interp1d(self.t_halo.value,
                self.r_halo.value.T, kind='linear')
        # create interpolant for orbital velocity (years & AU/yr units)
        self.v_halo_interp = interpolate.interp1d(self.t_halo.value,
                self.v_halo.value.T, kind='linear')
                
        # orbital properties used in Circular Restricted 3 Body Problem
        self.L2_dist = halo['x_lpoint'][0][0]*u.AU
        self.r_halo_L2 = halo['state'][:,0:3]*u.AU
        # position wrt L2
        self.r_halo_L2[:,0] -= self.L2_dist 
        
        # create new interpolant for CR3BP (years & AU units)
        self.r_halo_interp_L2 = interpolate.interp1d(self.t_halo.value,
                self.r_halo_L2.value.T, kind='linear')

        #update outspec with unique elements
        self._outspec['equinox'] = self.equinox.value[0]
        self._outspec['orbit_datapath'] = orbit_datapath


    def orbit(self, currentTime, eclip=False):
        """Finds observatory orbit positions vector in heliocentric equatorial (default)
        or ecliptic frame for current time (MJD).
        
        This method returns the telescope L2 Halo orbit position vector.
        
        Args:
            currentTime (astropy Time array):
                Current absolute mission time in MJD
            eclip (boolean):
                Boolean used to switch to heliocentric ecliptic frame. Defaults to 
                False, corresponding to heliocentric equatorial frame.
        
        Returns:
            r_obs (astropy Quantity nx3 array):
                Observatory orbit positions vector in heliocentric equatorial (default)
                or ecliptic frame in units of AU
        
        Note: Use eclip=True to get ecliptic coordinates.
        
        """
        
        t0 = self.haloStartTime
        
        # find time from Earth equinox and interpolated position
        dt = (currentTime - self.equinox + t0).to('yr').value
        t_halo = dt % self.period_halo
        r_halo = self.r_halo_interp(t_halo).T
        # find Earth positions in heliocentric ecliptic frame
        r_Earth = self.solarSystem_body_position(currentTime, 'Earth',
                eclip=True).to('AU').value
        # adding Earth-Sun distances (projected in ecliptic plane)
        r_Earth_norm = np.linalg.norm(r_Earth[:,0:2], axis=1)
        r_halo[:,0] = r_halo[:,0] + r_Earth_norm
        # Earth ecliptic longitudes
        lon = np.sign(r_Earth[:,1])*np.arccos(r_Earth[:,0]/r_Earth_norm)
        # observatory positions vector in heliocentric ecliptic frame
        r_obs = np.array([np.dot(self.rot(-lon[x], 3), 
                r_halo[x,:]) for x in range(currentTime.size)])*u.AU
        
        assert np.all(np.isfinite(r_obs)), \
                "Observatory positions vector r_obs has infinite value."
        
        if not eclip:
            # observatory positions vector in heliocentric equatorial frame
            r_obs = self.eclip2equat(r_obs, currentTime)
        
        return r_obs
    
    def haloPosition(self,currentTime):
        """Finds orbit positions of spacecraft in a halo orbit in rotating frame
        
        This method returns the telescope L2 Halo orbit position vector in an ecliptic, 
        rotating frame as dictated by the Circular Restricted Three Body-Problem. 
        The origin of this frame is the centroid of the Sun and Earth-Moon system.
        
        Args:
            currentTime (astropy Time array):
                Current absolute mission time in MJD

        Returns:
            r_halo (astropy Quantity nx3 array):
                Observatory orbit positions vector in an ecliptic, rotating frame 
                in units of AU
        
        """
        t0 = self.haloStartTime
        
        # Find the time between Earth equinox and current time(s)
        dt = (currentTime - self.equinox + t0).to('yr').value
        t_halo = dt % self.period_halo
        
        # Interpolate to find correct observatory position(s)
        r_halo = self.r_halo_interp_L2(t_halo).T*u.AU
        
        return r_halo

    def haloVelocity(self,currentTime):
        """Finds orbit velocity of spacecraft in a halo orbit in rotating frame
        
        This method returns the telescope L2 Halo orbit velocity vector in an ecliptic, 
        rotating frame as dictated by the Circular Restricted Three Body-Problem. 
        
        Args:
            currentTime (astropy Time array):
                Current absolute mission time in MJD

        Returns:
            v_halo (astropy Quantity nx3 array):
                Observatory orbit velocity vector in an ecliptic, rotating frame 
                in units of AU/year
        
        """
        t0 = self.haloStartTime
        
        # Find the time between Earth equinox and current time(s)
        
        dt = (currentTime - self.equinox + t0).to('yr').value
        t_halo = dt % self.period_halo
        
        # Interpolate to find correct observatory velocity(-ies)
        v_halo = self.v_halo_interp(t_halo).T
        v_halo = v_halo*u.au/u.year
        
        return v_halo
    
    def equationsOfMotion_CRTBP(self,t,state):
        """Equations of motion of the CRTBP with Solar Radiation Pressure
        
        Equations of motion for the Circular Restricted Three Body 
        Problem (CRTBP). First order form of the equations for integration, 
        returns 3 velocities and 3 accelerations in (x,y,z) rotating frame.
        All parameters are normalized so that time = 2*pi sidereal year.
        Distances are normalized to 1AU. Coordinates are taken in a rotating 
        frame centered at the center of mass of the two primary bodies. Pitch
        angle of the starshade with respect to the Sun is assumed to be 60 
        degrees, meaning the 1/2 of the starshade cross sectional area is 
        always facing the Sun on average
        
        Args:
            t (float):
                Times in normalized units
            state (float 6xn array):
                State vector consisting of stacked position and velocity vectors
                in normalized units

        Returns:
            ds (integer Quantity 6xn array):
                First derivative of the state vector consisting of stacked 
                velocity and acceleration vectors in normalized units
        """
        
        mu = self.mu
        m1 = self.m1
        m2 = self.m2
        
        # conversions from SI to normalized units in CRTBP
        TU = (2.*np.pi)/(1.*u.yr).to('s')        #time unit
        DU = (1.*u.AU).to('m')                  #distance unit
        MU = 5.97e24*(1.+ 1./81.0)*u.kg/self.mu  #mass unit = m1+m2

        x,y,z,dx,dy,dz = state
        
        rM1   = np.array([[-m2,0,0]])            #position of M1 rel 0
        rS_M1 = np.array([x,y,z]) - rM1.T        #position of starshade rel M1
        u1 = rS_M1/np.linalg.norm(rS_M1,axis=0)  #radial unit vector along sun-line
        u2 = np.array([u1[1,:],-u1[0,:],np.zeros(len(u1.T))])
        u2 = u2/np.linalg.norm(u2,axis=0)   #tangential unit vector to starshade
        
        Fsrp = np.zeros(u1.shape)
        
        if self.SRP:
            # pre-defined constants for a non-perfectly reflecting surface
            P = (4.473*u.uN/u.m**2.).to('kg/(m*s**2)') * DU / TU**2. / MU #solar radiation pressure at L2
            A = np.pi*(36.*u.m)**2.       #starshade cross-sectional area
            Bf = 0.038                  #non-Lambertian coefficient (front)
            Bb = 0.004                  #non-Lambertian coefficient (back)
            s  = 0.975                  #specular reflection factor
            p  = 0.999                  #nreflection coefficient
            ef = 0.8                    #emission coefficient (front)
            eb = 0.2                    #emission coefficient (back)
            
            # optical coefficients
            b1 = 0.5*(1.-s*p)
            b2 = s*p
            b3 = 0.5*(Bf*(1.-s)*p + (1.-p)*(ef*Bf - eb*Bb) / (ef + eb) ) 
        
            Fsrp_R = 0.25*P*A*(b1 + 0.25*b2 + 0.5*b3)  #radial component assuming 0.5*A
            Fsrp_T = (np.sqrt(3)*0.25)*P*A*(b2+2.*b3)   #tangential component assuming 0.5*A
    
            Fsrp = Fsrp_R.value*u1 + Fsrp_T.value*u2  #total SRP force
        
        #occulter distance from each of the two other bodies
        r1 = np.sqrt( (x + mu)**2. + y**2. + z**2. )
        r2 = np.sqrt( (1. - mu - x)**2. + y**2. + z**2. )
        
        #equations of motion
        ds1 = x + 2.*dy + m1*(-mu-x)/r1**3. + m2*(1.-mu-x)/r2**3.
        ds2 = y - 2.*dx - m1*y/r1**3. - m2*y/r2**3.
        ds3 = -m1*z/r1**3. - m2*z/r2**3.
        
        dr  = [dx,dy,dz]
        ddr = [ds1+Fsrp[0],ds2+Fsrp[1],ds3+Fsrp[2]]
        
        ds = np.vstack([dr,ddr])
        
        return ds
    
    def jacobian_CRTBP(self,t,s):
        """Equations of motion of the CRTBP
        
        Equations of motion for the Circular Restricted Three Body 
        Problem (CRTBP). First order form of the equations for integration, 
        returns 3 velocities and 3 accelerations in (x,y,z) rotating frame.
        All parameters are normalized so that time = 2*pi sidereal year.
        Distances are normalized to 1AU. Coordinates are taken in a rotating 
        frame centered at the center of mass of the two primary bodies
        
        Args:
            t (float):
                Times in normalized units
            s (float nx6 array):
                State vector consisting of stacked position and velocity vectors
                in normalized units

        Returns:
            Jacobian (integer Quantity nx6 array):
                Jacobian matrix of the state vector in normalized units
        """
        
        mu = self.mu
        m1 = self.m1
        m2 = self.m2
        
        # unpack components from state vector
        x,y,z,dx,dy,dz = s
        
        # determine shape of state vector (n = 6, m = size of t)
        n, m = s.shape
        
        # breaking up some of the calculations for the jacobian
        a8 = (mu + x - 1.)**2. + y**2. + z**2.
        a9 = (mu - x)**2. + y**2. + z**2.
        a1 = 2.*mu + 2.*x - 2.
        a2 = 2.*mu - 2.*x
        a3 = m2/a8**(1.5)
        a4 = m1/a9**(1.5)
        a5 = 3.*m1*y*z/a9**(2.5) + 3.*m2*y*z/a8**(2.5)
        a6 = 2.*a8
        a7 = 2.*a9
        
        #Calculating the different elements jacobian matrix
        
        # ddx,ddy,ddz wrt to x,y,z
        # this part of the jacobian has size 3 x 3 x m
        J1x = 3.*m2*a1*(mu + x -1.)/a6 - a3 - a4 - 3.*m1*a2*(mu+x)/a7 + 1.
        J1y = 3.*m1*y*(mu+x)/a9**(2.5) + 3.*m2*y*(mu+x-1.)/a8**(2.5)
        J1z = 3.*m1*z*(mu+x)/a9**(2.5) + 3.*m2*z*(mu+x-1.)/a8**(2.5)
        J2x = 3.*m2*y*a1/a6 - 3.*m1*y*a2/a7
        J2y = 3.*m1*y**2./a9**(2.5) - a3 - a4 + 3.*m2*y**2./a8**(2.5) + 1.
        J2z = a5
        J3x = 3.*m2*z*a1/a6 - 2.*m1*z*a2/a7
        J3y = a5
        J3z = 3.*m1*z**2./a9**(2.5) - a3 - a4 + 3.*m2*z**2./a8**(2.5)
        
        J = np.array([[ J1x,  J1y,  J1z],
                      [ J2x , J2y,  J2z],
                      [ J3x , J3y,  J3z]])
        
        # dx,dy,dz wrt to x,y,z
        # this part of the jacobian has size 3 x 3 x m
        Z = np.zeros([3,3,m])
        
        # dx,dy,dz wrt to dx,dy,dz
        # this part of the jacobian has size 3 x 3 x m
        E = np.full_like(Z,np.eye(3).reshape(3,3,1))

        # ddx,ddy,ddz wrt to dx,dy,dz
        # this part of the jacobian has size 3 x 3 x m
        w = np.array([[ 0. , 2. , 0.],
                      [-2. , 0. , 0.],
                      [ 0. , 0. , 0.]])

        W = np.full_like(Z,w.reshape(3,3,1))
        
        # stacking the different matrix blocks into a matrix 6 x 6 x m
        row1 = np.hstack( [ Z , E ])
        row2 = np.hstack( [ J , W ])

        jacobian = np.vstack( [ row1, row2 ])
        
        return jacobian
    
    def rot2inertV(self,rR,vR,t_norm):
        if rR.shape[0] == 3 and len(rR.shape) == 1:
            At  = self.rot(t_norm,3).T
            drR = np.array([-rR[1],rR[0],0])
            vI = np.dot(At,vR.T) + np.dot(At,drR.T)
        else:
            vI = np.zeros([len(rR),3])
            for t in range(len(rR)):
                At  = self.rot(t_norm,3).T
                drR = np.array([-rR[t,1],rR[t,0],0])
                vI[t,:] = np.dot(At,vR[t,:].T) + np.dot(At,drR.T)
        return vI
    
    def inert2rotV(self,rR,vI,t_norm):
        if t_norm.size is 1:
            t_norm  = np.array([t_norm])
        vR = np.zeros([len(t_norm),3])
        for t in range(len(t_norm)):
           At = self.rot(t_norm[t],3)
           vR[t,:] = np.dot(At,vI[t,:].T) + np.array([rR[t,1],-rR[t,0],0]).T
        return vR

    
    def lookVectors(self,TL,N1,N2,tA,tB):
        """Finds star angular separations relative to the halo orbit positions 
        
        This method returns the angular separation relative to the telescope on its
        halo orbit in the rotating frame of the CRTBP problem. 
        
        Args:
            TL (TargetList module):
                TargetList class object
            N1 (integer):
                Integer index of the most recently observed star
            N2 (integer):
                Integer index of the next star of interest
            tA (astropy Time):
                Current absolute mission time in MJD
            tB (astropy Time array):
                Time at which next star observation begins in MJD

        Returns:
            angle (integer):
                Angular separation between two target stars 
        """
        
        t = np.linspace(tA.value,tB.value,2)    #discretizing time
        t = Time(t,format='mjd')                #converting time to modified julian date
        
        #position of telescope at the given times in rotating frame
        r_halo = self.haloPosition(t).to('au')
        r_tscp = (r_halo + np.array([1,0,0])*self.L2_dist).value
        
        #position of stars wrt to telescope
        star1 = self.eclip2rot(TL,N1,tA).value
        star2 = self.eclip2rot(TL,N2,tB).value
        
        star1_tscp = star1 - r_tscp[ 0]
        star2_tscp = star2 - r_tscp[-1]
        
        #corresponding unit vectors pointing tscp -> Target Star
        u1 = star1_tscp / np.linalg.norm(star1_tscp)
        u2 = star2_tscp / np.linalg.norm(star2_tscp)
        
        angle = (np.arccos(np.dot(u1[0],u2[0].T))*u.rad).to('deg')
        
        return angle,u1,u2,r_tscp
    
    def eclip2rot(self,TL,sInd,currentTime):
        """Rotates star position vectors from ecliptic to rotating frame in CRTBP
        
        This method returns a star's position vector in the rotating frame of 
        the Circular Restricted Three Body Problem.  
        
        Args:
            TL (TargetList module):
                TargetList class object
            sInd (integer):
                Integer index of the star of interest
            currentTime (astropy Time):
                Current absolute mission time in MJD

        Returns:
            star_rot (astropy Quantity 1x3 array):
                Star position vector in rotating frame in units of AU
        """
        
        star_pos = TL.starprop(sInd,currentTime).to('au')
        theta    = (np.mod(currentTime.value,self.equinox.value[0])*u.d).to('yr') / u.yr * (2.*np.pi) * u.rad
        
        if currentTime.size == 1:
            star_rot = np.array([np.dot(self.rot(theta, 3), 
                star_pos[x,:].to('AU').value) for x in range(len(star_pos))])[0]*u.AU
        else:
            star_rot = np.array([np.dot(self.rot(theta[x], 3), 
                star_pos[x,:].to('AU').value) for x in range(len(star_pos))])*u.AU

        return star_rot
    
    def integrate(self,s0,t):
        """Integrates motion in the CRTBP given initial conditions
        
        This method returns a star's position vector in the rotating frame of 
        the Circular Restricted Three Body Problem.  
        
        Args:
            s0 (integer 1x6 array):
                Initial state vector consisting of stacked position and velocity vectors
                in normalized units
            t (integer):
                Times in normalized units

        Returns:
            s (integer nx6 array):
                State vector consisting of stacked position and velocity vectors
                in normalized units
        """
        
        EoM = lambda s,t: self.equationsOfMotion_CRTBP(t,s)
             
        s = itg.odeint(EoM, s0, t, full_output = 0,rtol=2.5e-14,atol=1e-22)
        
        return s
