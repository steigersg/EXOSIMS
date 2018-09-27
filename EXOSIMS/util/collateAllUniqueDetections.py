"""Collate All Unique Detections
For singleRunPostProcessing: The purpose of this script is to search through all pkl files in a given folder and produce NEIDinfo.txt
For multiRunPostProcessing:  

# To run from within IPython
# %run collateAllUniqueDetections.py --searchFolder '/full path to/' --outFolder '/outFolder to put csv file'
# 
# A specific example
# %run collateAllUniqueDetections.py --searchFolder '/home/dean/Documents/SIOSlab' --outFolder '/outFolder to put csv file/collatedData_collationDate.csv'


 
Written by Dean Keithly on 6/28/2018
"""

import os
import numpy as np
import argparse
import json
import re
import ntpath
import ast
import string
import copy
import datetime
from itertools import combinations
import shutil
import glob
try:
    import cPickle as pickle
except:
    import pickle
import astropy.units as u
from EXOSIMS.util.read_ipcluster_ensemble import gen_summary


class collateAllUniqueDetections(object):
    """Designed to meet NEID needs for sub-neptune characterizations
    """
    _modtype = 'util'

    def __init__(self, args):
        """
        Args:
            args is not used
        """
        pass

    def singleRunPostProcessing(self,PPoutpath,folder):
        """
        Args:
            PPoutpath (string) - output path to place data in
            folder (string) - full filepath to folder containing runs
        """
        out = self.collate_gen_summary(folder)

        #### Create Outstring
        outString = list()
        for i in range(len(out['Rps'])):
            outString.append(str(out['Rps'][i]) + ',' + str(out['detected'][i]) + ',' + str(out['Mps'][i]) + ',' +str(out['starinds'][i]) + ',' +str(out['smas'][i]) + ',' +str(out['ps'][i]) + ',' +str(out['es'][i]) + ',' +str(out['WAs'][i]) + ',' +str(out['SNRs'][i]) + ',' +str(out['fZs'][i]) + ',' +str(out['fEZs'][i]) + ',' + str(out['dMags'][i]) + ',' +str(out['rs'][i]) + '\n')
        outString = ''.join(outString)

        with open(os.path.join(folder,'NEIDinfo.txt'), 'a+') as g: #Write to file
            g.write(outString)

    def collate_gen_summary(self, run_dir, includeUniversePlanetPop=False):
        """
        Args:
        run_dir (string):
          path to run directory ex: '/my/path/to/the/dir/'
        includeUniversePlanetPop (boolean):
          A boolean flag dictating whether to include the universe planet population in the output or just the detected planets
          (default is false)
        Returns:
          out(dictionary)
        """
        pklfiles = glob.glob(os.path.join(run_dir,'*.pkl'))

        out = {'fname':[],
               'detected':[],
               #'fullspectra':[],
               #'partspectra':[],
               'Rps':[],
               'Mps':[],
               #'tottime':[],
               'starinds':[],
               'smas':[],
               'ps':[],
               'es':[],
               'WAs':[],
               'SNRs':[],
               'fZs':[],
               'fEZs':[],
               #'allsmas':[],
               #'allRps':[],
               #'allps':[],
               #'alles':[],
               #'allMps':[],
               'dMags':[],
               'rs':[],
               'starNames':[]}

        for counter,f in enumerate(pklfiles):
            print "%d/%d"%(counter,len(pklfiles))
            with open(f, 'rb') as g:
                res = pickle.load(g)

            out['fname'].append(f)
            dets = np.hstack([row['plan_inds'][row['det_status'] == 1]  for row in res['DRM']])
            out['detected'].append(dets)
            
            out['WAs'].append(np.hstack([row['det_params']['WA'][row['det_status'] == 1].to('arcsec').value for row in res['DRM']]))
            out['dMags'].append(np.hstack([row['det_params']['dMag'][row['det_status'] == 1] for row in res['DRM']]))
            out['rs'].append(np.hstack([row['det_params']['d'][row['det_status'] == 1].to('AU').value for row in res['DRM']]))
            out['fEZs'].append(np.hstack([row['det_params']['fEZ'][row['det_status'] == 1].value for row in res['DRM']]))
            out['fZs'].append(np.hstack([[row['det_fZ'].value]*len(np.where(row['det_status'] == 1)[0]) for row in res['DRM']]))
            #out['fullspectra'].append(np.hstack([row['plan_inds'][row['char_status'] == 1]  for row in res['DRM']]))
            #out['partspectra'].append(np.hstack([row['plan_inds'][row['char_status'] == -1]  for row in res['DRM']]))
            #out['tottime'].append(np.sum([row['det_time'].value+row['char_time'].value for row in res['DRM']]))
            out['SNRs'].append(np.hstack([row['det_SNR'][row['det_status'] == 1]  for row in res['DRM']]))
            out['Rps'].append((res['systems']['Rp'][dets]/u.R_earth).decompose().value)
            out['smas'].append(res['systems']['a'][dets].to(u.AU).value)
            out['ps'].append(res['systems']['p'][dets])
            out['es'].append(res['systems']['e'][dets])
            out['Mps'].append((res['systems']['Mp'][dets]/u.M_earth).decompose())
            out['starinds'].append(np.hstack([[row['star_ind']]*len(np.where(row['det_status'] == 1)[0]) for row in res['DRM']]))
            out['starNames'].append([res['systems']['star'][starind] for starind in out['starinds'][-1].astype(int).tolist()])
            # if includeUniversePlanetPop == True:
            #   out['allRps'].append((res['systems']['Rp']/u.R_earth).decompose().value)
            #   out['allMps'].append((res['systems']['Mp']/u.M_earth).decompose())
            #   out['allsmas'].append(res['systems']['a'].to(u.AU).value)
            #   out['allps'].append(res['systems']['p'])
            #   out['alles'].append(res['systems']['e'])
            
            
        return out

    def multiRunPostProcessing(self, PPoutpath, folders):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a set of scripts and a queue. all files are relocated to a new folder.")
    parser.add_argument('--searchFolder',nargs=1,type=str, help='Path to Folder to Search Through (string).')
    parser.add_argument('--outFolder',nargs=1,type=str, help='Path to Folder to Place collatedData_collationDate.csv (string).')
    args = parser.parse_args()


    searchFolder = args.searchFolder[0]
    outFolder = args.outFolder[0]

    #### Get List of All run_dir containing pkl files
    #searchFolder = '/home/dean/Documents/SIOSlab/'  
    searchFolder += '*/'
    pklfiles = glob.glob(os.path.join(searchFolder,'*.pkl'))
    pklfiles2 = list()
    for f in pklfiles:
        myStr = '/'.join(f.split('/')[0:-1])
        if not myStr in pklfiles2:#Ensures no duplicates added
            pklfiles2.append(myStr)
    ##########

    #### Get Date
    date = unicode(datetime.datetime.now())
    date = ''.join(c + '_' for c in re.split('-|:| ',date)[0:-1])#Removes seconds from date
    ####################################3

    #### Search Through All Files
    for f in pklfiles2:
        out = gen_summary(f, includeUniversePlanetPop=False)

        Rps = list()
        detected = list()       
        Mps = list()
        #tottime = list()
        starinds = list()
        smas = list()
        ps = list()
        es = list()
        WAs = list()
        SNRs = list()
        fZs = list()
        fEZs = list()
        dMags = list()
        rs = list()

        #Parse through out for planets with R<Rneptune
        for ind1 in range(len(out['detected'])):

            for ind2 in range(len(out['detected'][ind1])):
                if out['Rps'][ind1][ind2] < 24764.0/6371.0: #Radius of neptune in earth Radii
                    Rps.append(out['Rps'][ind1][ind2])
                    detected.append(out['detected'][ind1][ind2])
                    Mps.append(out['Mps'][ind1][ind2])
                    #tottime.append(out['tottime'][ind1][ind2])
                    starinds.append(out['starinds'][ind1][ind2])
                    smas.append(out['smas'][ind1][ind2])
                    ps.append(out['ps'][ind1][ind2])
                    es.append(out['es'][ind1][ind2])
                    WAs.append(out['WAs'][ind1][ind2])
                    SNRs.append(out['SNRs'][ind1][ind2])
                    fZs.append(out['fZs'][ind1][ind2])
                    fEZs.append(out['fEZs'][ind1][ind2])
                    dMags.append(out['dMags'][ind1][ind2])
                    rs.append(out['rs'][ind1][ind2])

        outString = list()
        for i in range(len(Rps)):
            outString.append(str(Rps[i]) + ',' + str(detected[i]) + ',' + str(Mps[i]) + ',' +str(starinds[i]) + ',' +str(smas[i]) + ',' +str(ps[i]) + ',' +str(es[i]) + ',' +str(WAs[i]) + ',' +str(SNRs[i]) + ',' +str(fZs[i]) + ',' +str(fEZs[i]) + ',' + str(dMags[i]) + ',' +str(rs[i]) + '\n')
        outString = ''.join(outString)

        with open(outFolder + 'NEIDinfo.txt', 'a+') as g:
            g.write(outString)