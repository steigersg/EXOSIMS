from EXOSIMS.Prototypes.PlanetPopulation import PlanetPopulation
#from EXOSIMS.PlanetPopulation.EarthTwinHabZone1 import EarthTwinHabZone1
import numpy as np
import astropy.units as u

class JupiterTwin(PlanetPopulation):
    """
    Population of Jupiter twins (11.209 R_Earth, 317.83 M_Eearth, 1 p_Earth)
    On eccentric orbits (0.7 to 1.5 AU)*5.204.
    Numbers pulled from nssdc.gsfc.nasa.gov/planetary/factsheet/jupiterfact.html
    
    This implementation is intended to enforce this population regardless
    of JSON inputs.  The only inputs that will not be disregarded are erange
    and constrainOrbits.
    """

    def __init__(self, eta=1, erange=[0.,0.9], constrainOrbits=True, **specs):
        #eta is probability of planet occurance in a system. I set this to 1
        specs['erange'] = erange
        specs['constrainOrbits'] = constrainOrbits
        aJtoE = 5.204
        RpJtoE = 11.209
        MpJtoE = 317.83
        pJ = 0.538
        # specs being modified in JupiterTwin
        specs['eta'] = eta
        specs['arange'] = [0.7*aJtoE, 1.5*aJtoE]
        specs['Rprange'] = [1*RpJtoE,1*RpJtoE]
        specs['Mprange'] = [1*MpJtoE,1*MpJtoE]
        specs['prange'] = [pJ,pJ]
        specs['scaleOrbits'] = True
        
        PlanetPopulation.__init__(self, **specs)
        
    def gen_plan_params(self, n):
        """Generate semi-major axis (AU), eccentricity, geometric albedo, and
        planetary radius (earthRad)
        
        Semi-major axis and eccentricity are uniformly distributed with all
        other parameters constant.
        
        Args:
            n (integer):
                Number of samples to generate
        
        Returns:
            a (astropy Quantity array):
                Semi-major axis in units of AU
            e (float ndarray):
                Eccentricity
            p (float ndarray):
                Geometric albedo
            Rp (astropy Quantity array):
                Planetary radius in units of earthRad
        
        """
        n = self.gen_input_check(n)
        # generate samples of semi-major axis
        ar = self.arange.to('AU').value
        # check if constrainOrbits == True for eccentricity
        if self.constrainOrbits:
            # restrict semi-major axis limits
            arcon = np.array([ar[0]/(1.-self.erange[0]), ar[1]/(1.+self.erange[0])])
            a = np.random.uniform(low=arcon[0], high=arcon[1], size=n)*u.AU
            tmpa = a.to('AU').value

            # upper limit for eccentricity given sma
            elim = np.zeros(len(a))
            amean = np.mean(ar)
            elim[tmpa <= amean] = 1. - ar[0]/tmpa[tmpa <= amean]
            elim[tmpa > amean] = ar[1]/tmpa[tmpa>amean] - 1.
            elim[elim > self.erange[1]] = self.erange[1]
            elim[elim < self.erange[0]] = self.erange[0]
        
            # uniform distribution
            e = np.random.uniform(low=self.erange[0], high=elim, size=n)
        else:
            a = np.random.uniform(low=ar[0], high=ar[1], size=n)*u.AU
            e = np.random.uniform(low=self.erange[0], high=self.erange[1], size=n)
        # generate geometric albedo
        pJ = 0.538# 0.538 from nssdc.gsfc.nasa.gov
        p = pJ*np.ones((n,))
        # generate planetary radius
        Rp = np.ones((n,))*u.earthRad
        
        return a, e, p, Rp
