from multiprocessing import Process, Pipe, Manager
from squidpy.instrument import get_datapoint
from squidpy.plotting import LivePlotter
from squidpy.data import DataCollector, Data
from pylab import pause
import time
import re

class Measurement(Process):
    '''
    Basic measurement class.
    '''
    def __init__(self, param_dict, q, *args, **kwargs):
        super(Measurement, self).__init__()
        self.param_dict = param_dict
        self.q = q
        for key in kwargs:
            setattr(self, key, kwargs[key])
        
    def get_dp(self):
        return get_datapoint(self.param_dict)
    
    def run(self):
        # Watch vs. time
        if hasattr(self,'watch'):
            t = time.time()
            while abs(time.time()-t) < self.watch:
                dp = self.get_dp()
                self.q.put(dp)
                pause(0.1)
            self.q.put(None)

class Experiment():
    '''
    Basic experiment class. This class creates the measurement, plot and data collector. It runs the measurement in a separate process, which drops datapoints in a queue.
    The datacollector, also in a separate process, is a daemon that collects all these datapoints in a Data (pd.Dataframe-like) object and saves the data periodically on-disk.
    It also drops the latest Data instance in a pipe for live plotting in the main thread.
    '''
    def __init__(self, title, param_dict):
        super(Experiment, self).__init__()
        self.title = title
        manager = Manager()
        self.output = manager.dict()
        self.datacollector = DataCollector(self.output, title)
        self.datacollector.start()
        self.param_dict = param_dict
        self.init_plot()
        
    def init_plot(self):
        self.plot = LivePlotter(self.title, self.param_dict, self.datacollector.plotter_pipe)
    
    def watch(self, t_max = 10):
        '''
        Watch the system until time reaches t_max (in s)
        '''
        self.t_max = t_max
        self.measurement = Measurement(self.param_dict, self.datacollector.q, watch = t_max)
        self.run()
    
    def run(self):
        if not hasattr(self,'measurement'):
            raise NameError('Measurement type is not defined.')
        elif not hasattr(self, 'param_dict'):
            raise NameError('Measurement parameters are not defined.')
        self.measurement.start()
        self.plot.run()
        self.data = self.output['data']
    
    def close(self):
        self.datacollector.terminate()