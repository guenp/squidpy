from multiprocessing import Process, Pipe, Manager
from squidpy.instrument import get_datapoint, get_array
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
        self.ins_dict = {ins.name: ins for ins in param_dict.keys()}
        self.q = q
        self.measlist = []
    
    def set(self, *args, **kwargs):
        '''
        Add keyword argument as measurement type to measurement list
        '''
        for key in kwargs:
            self.measlist.append({'type':key, 'params': kwargs[key]})
    
    def get_dp(self):
        return get_datapoint(self.param_dict)
    
    def set_param(self, param_name, val):
        # print('setting %s = %s' %(param_name, val))
        ins, param = re.split('\.',param_name)
        setattr(self.ins_dict[ins], param, val)
    
    def do_measurement(self, measlist):
        if len(measlist)>0:
            meas = measlist.pop(0)
            if meas['type']=='sweep':
                self.recursive_sweep(measlist.copy(), *meas['params'])
            if meas['type']=='watch':
                t = time.time()
                while abs(time.time()-t) < meas['params']:
                    self.do_measurement(measlist.copy())
            if meas['type']=='measure':
                dp = self.get_dp()
                self.q.put(dp)
                pause(0.1)
                self.do_measurement(measlist.copy())
    
    def recursive_sweep(self, measlist, sweep_param, start, stop, step):
        [self.set_param_and_run_next(measlist, sweep_param, val) for val in get_array(start, stop, step)]

    def set_param_and_run_next(self, measlist, sweep_param, val):
        self.set_param(sweep_param, val)
        self.do_measurement(measlist.copy())
    
    def run(self):
        self.do_measurement(self.measlist.copy())
        self.q.put(None) #end measurement

class Experiment(Process):
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
        self.measurement = Measurement(self.param_dict, 
                                       self.datacollector.q)
        self.liveplot = LivePlotter(self.title, 
                                    self.param_dict, 
                                    self.datacollector.plotter_pipe)
        
    def plot(self, x, y, *args, **kwargs):
        self.liveplot.add_line(x, y, *args, **kwargs)
        
    def add_line(self, x, y, *args, **kwargs):
        self.liveplot.add_line(x, y, *args, **kwargs)
    
    def watch(self, t_max = 10, param_dict=None):
        '''
        Watch the system until time reaches t_max (in s)
        '''
        if param_dict is None:
            param_dict = self.param_dict
        self.t_max = t_max
        self.measurement.set(watch = t_max)
        self.measure(param_dict)
    
    def sweep(self, sweep_param):
        self.sweep_param = sweep_param
        return self
    
    def measure(self, param_dict=None):
        if param_dict is None:
            param_dict = self.param_dict
        self.measurement.set(measure = param_dict)
        
    def __getitem__(self, s):
        self.measurement.set(sweep = (self.sweep_param, 
                             s.start, s.stop, s.step))
    
    def run(self):
        if self.measurement.measlist is []:
            raise NameError('Measurement is not defined.')
        elif not hasattr(self, 'param_dict'):
            raise NameError('Measurement parameters are not defined.')
        if self.measurement.pid is not None:
            measlist = self.measurement.measlist
            self.measurement = Measurement(self.param_dict, 
                                       self.datacollector.q)
            self.measurement.measlist = measlist
        self.measurement.start()
        self.liveplot.run()
        self.data = self.output['data']
    
    def close(self):
        self.datacollector.terminate()