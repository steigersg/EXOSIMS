from EXOSIMS.Prototypes.SimulatedUniverse import SimulatedUniverse
import numpy as np
import astropy.units as u
from astropy.time import Time

class KnownRVPlanetsUniverse(SimulatedUniverse):
    """
    Simulated universe implementation inteded to work with the Known RV planet
    planetary population and target list implementations.
    
    Args: 
        specs: 
            user specified values
        
    """

    def __init__(self, **specs):
        
        SimulatedUniverse.__init__(self, **specs)
        
    def gen_physical_properties(self, missionStart=60634, **specs):
        """Generates the planetary systems' physical properties. Populates arrays 
        of the orbital elements, albedos, masses and radii of all planets, and 
        generates indices that map from planet to parent star.
        
        All parameters are generated by adding consistent error terms to the 
        catalog values for each planet.
        
        """
        
        PPop = self.PlanetPopulation
        PPMod = self.PlanetPhysicalModel
        TL = self.TargetList
        
        # Go through the target list and pick out the planets belonging to those hosts
        starinds = np.array([])
        planinds = np.array([])
        for j,name in enumerate(TL.Name):
            tmp = np.where(PPop.hostname == name)[0]
            planinds = np.hstack((planinds,tmp))
            starinds = np.hstack((starinds,[j]*len(tmp)))
        planinds = planinds.astype(int)
        starinds = starinds.astype(int)
        
        # map planets to stars in standard format
        self.plan2star = starinds
        self.sInds = np.unique(self.plan2star)
        self.nPlans = len(planinds)
        
        # populate parameters
        self.a = PPop.sma[planinds] +  np.random.normal(size=self.nPlans)\
                *PPop.smaerr[planinds]                      # semi-major axis
        # ensure sampling did not make it negative
        self.a[self.a <= 0] = PPop.sma[planinds][self.a <= 0]
        self.e = PPop.eccen[planinds] + np.random.normal(size=self.nPlans)\
                *PPop.eccenerr[planinds]                    # eccentricity
        self.e[self.e < 0.] = 0.
        self.e[self.e > 0.9] = 0.9
        Itmp, Otmp, self.w = PPop.gen_angles(self.nPlans)
        self.I = PPop.allplanetdata['pl_orbincl'][planinds] + np.random.normal\
                (size=self.nPlans)*PPop.allplanetdata['pl_orbinclerr1'][planinds] 
        self.I[self.I.mask] = Itmp[self.I.mask].to('deg').value
        self.I = self.I.data*u.deg                          # inclination
        
        lper = PPop.allplanetdata['pl_orblper'][planinds] + \
                np.random.normal(size=self.nPlans)*PPop.allplanetdata['pl_orblpererr1'][planinds] 
        self.O = lper.data*u.deg - self.w                   # longitude of ascending node
        self.O[np.isnan(self.O)] =  Otmp[np.isnan(self.O)]
        self.p = PPMod.calc_albedo_from_sma(self.a)         # albedo
        self.Mp = PPop.mass[planinds]                       # mass first!
        self.Rp = PPMod.calc_radius_from_mass(self.Mp)      # radius from mass
        self.Rmask = ~PPop.radiusmask[planinds]
        self.Rp[self.Rmask] = PPop.radius[planinds][self.Rmask]
        self.Rperr1 = PPop.radiuserr1[planinds][self.Rmask]
        self.Rperr2 = PPop.radiuserr2[planinds][self.Rmask]
        
        # calculate period
        missionStart = Time(float(missionStart), format='mjd', scale='tai')
        T = PPop.period[planinds] + np.random.normal(size=self.nPlans)\
                *PPop.perioderr[planinds]
        T[T <= 0] = PPop.period[planinds][T <= 0]
        # calculate initial mean anomaly
        tper = Time(PPop.tper[planinds].value + (np.random.normal(size=self.nPlans)\
                *PPop.tpererr[planinds]).to('day').value, format='jd', scale='tai')
        self.M0 = ((missionStart - tper)/T % 1)*360*u.deg