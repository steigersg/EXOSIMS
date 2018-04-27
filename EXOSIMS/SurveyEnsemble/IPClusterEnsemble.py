from __future__ import print_function

from ipyparallel import Client
from EXOSIMS.Prototypes.SurveyEnsemble import SurveyEnsemble 
from EXOSIMS.util.get_module import get_module
import time
from IPython.core.display import clear_output
import sys
from datetime import datetime, timedelta
import timeit


class IPClusterEnsemble(SurveyEnsemble):
    """Parallelized suvey ensemble based on IPython parallel (ipcluster)
    
    """

    def __init__(self, **specs):
        
        SurveyEnsemble.__init__(self, **specs)

        self.verb = specs.get('verbose', True)
        
        # access the cluster
        self.rc = Client()
        #BECOME DASK ################
        #self.rc.become_dask()
        #############################
        self.dview = self.rc[:]
        self.dview.block = True
        with self.dview.sync_imports(): import EXOSIMS, EXOSIMS.util.get_module, \
                os, os.path, time, random, cPickle, traceback
        if specs.has_key('logger'):
            specs.pop('logger')
        if specs.has_key('seed'):
            specs.pop('seed')
        self.dview.push(dict(specs=specs))
        res = self.dview.execute("SS = EXOSIMS.util.get_module.get_module(specs['modules'] \
                ['SurveySimulation'], 'SurveySimulation')(**specs)")

        self.vprint("Created SurveySimulation objects on %d engines."%len(self.rc.ids))
        #for row in res.stdout:
        #    self.vprint(row)

        self.lview = self.rc.load_balanced_view()

        self.maxNumEngines = len(self.rc.ids)

    def run_ensemble(self, sim, nb_run_sim, run_one=None, genNewPlanets=True,
            rewindPlanets=True, kwargs={}):
        
        t1 = time.time()
        async_res = []
        for j in range(nb_run_sim):
            ar = self.lview.apply_async(run_one, genNewPlanets=genNewPlanets,
                    rewindPlanets=rewindPlanets, **kwargs)
            async_res.append(ar)
        
        print("Submitted %d tasks."%len(async_res))
        
        runStartTime = timeit.timeit()#create job starting time
        runOnce = True
        avg_time_per_run = 0
        timeMark = 0
        tmplenoutstandingset = 5
        ar= self.rc._asyncresult_from_jobs(async_res)
        while not ar.ready():
            ar.wait(10.)
            clear_output(wait=True)
            if ar.progress > 0:
                timeleft = ar.elapsed/ar.progress * (nb_run_sim - ar.progress)
                if timeleft > 3600.:
                    timeleftstr = "%2.2f hours"%(timeleft/3600.)
                elif timeleft > 60.:
                    timeleftstr = "%2.2f minutes"%(timeleft/60.)
                else:
                    timeleftstr = "%2.2f seconds"%timeleft
            else:
                timeleftstr = "who knows"

            #Terminate hanging runs
            outstandingset = self.rc.outstanding#a set of msg_ids that have been submitted but resunts have not been received
            print('outstandingset')
            print(outstandingset)
            print('Outstanding set length is: ' + str(len(outstandingset)))

            if len(outstandingset) < 5:  # There are less than 5 runs remaining #nb_run_sim
                #we are making the general assumption that less than 5 runs will encounter a hang.
                if runOnce == True:
                    timeMark = timeit.timeit() # Create a marker to calculate the average amount of time spent on simulation runs
                    runOnce = False#set marker to False so it will not run again
                    avg_time_per_run = (timeMark - runStartTime)/(nb_run_sim - len(outstandingset))#compute average amount of time per run
                if len(outstandingset) < tmplenoutstandingset:
                    tmplenoutstandingset = len(outstandingset)
                    timeMark = timeit.timeit()
                
                if avg_time_per_run*3 < (timeit.timeit() - timeMark)/len(outstandingset):#*3 is some generic factor to ensure the runs have time to complete if they run over...
                    #Shutdown all running cores
                    print('Shutting down ' + str(len(self.rc.outstanding)) + 'qty engine processes')
                    #STOP THIS DOESN'T TECHNICALLY WORK. RC.OUTSTANDING ARE MSG_IDS NOT ENGINE IDS
                    #self.rc.shutdown(targets=list(self.rc.outstanding))
                    self.rc.abort()#by default should abort all outstanding jobs... #it is possible that this will not stop the jobs running


            # try:
            #     tmpDict = ar.result_status(outstandingset)
            #     pendingmsgIds = tmpDict['pending']
            # except:
            #     pass

            # #msgids = ar._msg_ids_from_jobs(jobs)
            # try:
            #     arResult = ar.get_result(list(outstandingset))
            #     print('arResult')
            #     print(arResult) 
            # except:
            #     pass
            # #didnt work ar.get_dict()
            # hourago = (datetime.now() - timedelta(1./24*(0.5)))#runs lasting longer than 30 minutes
            # print('hour ago')
            # print(hourago)
            # print('db_query Garbage')
            # try:
            #     print(self.rc.db_query({'started' : None}, keys=['msg_id', 'started', 'client_uuid', 'engine_uuid', 'submitted', 'header', 'date']))
            # except:
            #     pass
            # try:
            #     listofStarted = [x for x in self.rc.db_query({'started' : None}, keys=['msg_id', 'started', 'client_uuid', 'engine_uuid', 'submitted', 'header', 'date']) if not x['started'] == None]
            #     print('list of Started')
            #     print(listofStarted)
            # except:
            #     pass

            # try:
            #     rcRunningLong = self.rc.db_query({'started' : {'$lte' : hourago}}, keys=['msg_id', 'started', 'client_uuid', 'engine_uuid', 'submitted', 'header', 'date'])
            #     print('Something is $LTE')
            #     print(rcRunningLong)
            # except:
            #     pass

            # try:
            #     if ar.progress/(nb_run_sim+1) > 0.8 and rcRunningLong is not None:  # Over 90% of the runs have been completed and 
            #         print("rcRunningLong is: ")
            #         print(rcRunningLong)
            # except:
            #     pass

            # try:
            #     dir(ar)
            # except:
            #     pass

                #alternative rc.db_query({'completed' : None}, keys=['msg_id', 'started'])

            # We will try using Client().become_dask(targets='all',nanny=True)
            # following initialization of these clients to get them to run as dask distributed cluster... whatever that means
            # Can also try Client().become_distributed(targets='all',nanny=True)
            # supposedly the above two commands are equivalent according to the ICD
            # We would restart a process by calling executor.restart
            # I think we get an executor by calling
            # Client().executor(targets=[ids])
            # so the full command is 
            # Client().executor(targets=[ids]).restart
            # We should get ids from the rcRunningLong['msg_id'] but I am not certain if that is the right id



            print("%4i/%i tasks finished after %4i s. About %s to go." % (ar.progress, nb_run_sim, ar.elapsed, timeleftstr), end="")
            sys.stdout.flush()

        #self.rc.wait(async_res)
        #self.rc.wait_interactive(async_res)
        t2 = time.time()
        print("\nCompleted in %d sec" % (t2 - t1))
        
        res = [ar.get() for ar in async_res]
        
        return res
