# -*- coding: utf-8 -*-
from EXOSIMS.Prototypes.ZodiacalLight import ZodiacalLight
import numpy as np
from astropy import units as u

class LindlerZodiacalLight(ZodiacalLight):
    """Lindler Zodiacal Light class
    
    This class contains all variables and methods necessary to perform
    Zodiacal Light Module calculations in exoplanet mission simulation using
    the model from Lindler."""
                        
    def fzodi(self, Inds, I, targlist):
        """Returns exozodi levels for systems with planets 
        
        This method is called in __init__ of SimulatedUniverse.
        
        Args:
            Inds (ndarray):
                1D numpy ndarray of indicies referring back to target list stars
            I (ndarray):
                1D numpy ndarray or scalar value of inclination in degrees
            targlist (TargetList):
                TargetList class object
        
        Returns:
            fzodicurr (ndarray):
                1D numpy ndarray of exozodiacal light levels

        """
         
        # maximum V magnitude
        MV = targlist.MV 
        # ecliptic latitudes
        lats = self.eclip_lats(targlist.coords).value 
        
        i = np.where(I > 90.)
        if type(I) == np.ndarray:
            I[i] = 180. - I[i]
        
        if self.exozodiVar == 0:
            fzodicurr = self.fbeta(lats[Inds]) + \
            2.*self.exozodi*self.fbeta(I)*2.5**(4.78-MV[Inds])
        else:
            # assume log-normal distribution of variance
            mu = np.log(self.exozodi) - 0.5*np.log(1. + self.exozodiVar/self.exozodi**2)
            v = np.sqrt(np.log(self.exozodiVar/self.exozodi**2 + 1.))
            R = np.random.lognormal(mean=mu, sigma=v, size=(len(Inds),))
            fzodicurr = self.fbeta(lats[Inds]) + \
            2.*R*self.fbeta(I)*2.5**(4.78-MV[Inds])
        
        return fzodicurr
        
    def fbeta(self, beta):
        """Empirically derived variation of zodiacal light with viewing angle
        
        This method encodes the empirically derived formula for zodiacal light
        with viewing angle from Lindler.
        
        Args:
            beta (ndarray):
                angle in degrees
                
        Returns:
            f (ndarray):
                zodiacal light in zodi
        
        """
        
        f = 2.44 - 0.0403*beta + 0.000269*beta**2
        
        return f