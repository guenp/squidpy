from multiprocessing import Process, Pipe, Manager
from squidpy.instrument import get_datapoint, get_array, get_instruments
from squidpy.data import DataCollector, Data
from IPython import display
from pylab import pause
import time
import re
import pylab as pl
import numpy as np
import seaborn as sns
import asyncio
from IPython import display
import pandas as pd

class Measurement(Process):
    '''
    Basic measurement class.
    '''
    def __init__(self, param_dict, q, s, *args, **kwargs):
        super(Measurement, self).__init__()
        self.q = q
        self.s = s
        self.measlist = []
        self.param_dict = param_dict
    
    def set(self, *args, **kwargs):
        '''
        Add keyword argument as measurement type 
        to measurement list
        '''
        for key in kwargs:
            self.measlist.append({'type':key, 'params': kwargs[key]})
    
    def get_dp(self):
        return get_datapoint(self.instruments, self.param_dict)
    
    def do_measurement(self, measlist):
        if len(measlist)>0:
            meas = measlist.pop(0)
            if meas['type']=='sweep':
                self.recursive_sweep(measlist.copy(), *meas['params'])
            if meas['type']=='watch':
                t = time.time()
                while abs(time.time()-t) <= meas['params']:
                    self.do_measurement(measlist.copy())
            if meas['type']=='measure':
                dp = self.get_dp()
                self.q.put(dp)
                self.do_measurement(measlist.copy())
    
    def recursive_sweep(self, measlist, ins, param, start, stop, step):
        [self.set_param_and_run_next(measlist, ins, param, val) for val in get_array(start, stop, step)]

    def set_param_and_run_next(self, measlist, ins, param, val):
        setattr(self.instruments.dict()[ins], param, val)
        self.do_measurement(measlist.copy())
    
    def run(self):
        self.instruments = get_instruments(self.s)
        self.do_measurement(self.measlist.copy())
        self.q.put(None) #end measurement

class Experiment():
    '''
    Basic experiment class. This class creates the measurement, plot and data collector. It runs the measurement in a separate process, which drops datapoints in a queue.
    The datacollector, also in a separate process, is a daemon that collects all these datapoints in a Data (pd.Dataframe-like) object and saves the data periodically on-disk.
    It also drops the latest Data instance in a pipe for live plotting in the main thread.
    '''
    def __init__(self, title, instruments, param_dict=None):
        self.title = title
        manager = Manager()
        self.output = manager.dict()
        self.plots = []
        self.figs = []
        self.datacollector = DataCollector(self.output, title)
        self.datacollector.start()
        self._data = pd.DataFrame()
        self.param_dict = param_dict
        self.measurement = Measurement(self.param_dict, 
                                       self.datacollector.q,
                                       instruments.s)
    
    @property
    def data(self):
        if 'data' in self.output.keys():
            self._data = Data(**self.output)
        return self._data
    
    @property
    def running(self):
        running = self.measurement.is_alive()
        if not running:
            if self.plots[0]['type'] is not 'pcolor':
                display.clear_output(wait=True)
        return running
    
    def wait_and_get_title(self):
        '''Wait for data file to fill and return title.'''
        while self.data.empty:
            time.sleep(0.1)
        title = '%s_%s' %(self._data.stamp, self._data.title)
        return title
    
    def plot(self, *args, **kwargs):
        kwargs['title'] = self.wait_and_get_title()
        ax = self.data.plot(*args, **kwargs)
        self.plots.append({'type': 'plot', 'args': args, 'kwargs': kwargs, 'ax': ax})
        if ax.get_figure() not in self.figs:
            self.figs.append(ax.get_figure())
    
    def pcolor(self, xname, yname, zname, *args, **kwargs):
        title = self.wait_and_get_title()
        x,y,z = self._data[xname], self._data[yname], self._data[zname]
        shape = (len(y.unique()), len(x.unique()))
        diff = shape[0]*shape[1] - len(z)
        Z = np.concatenate((z.values, np.zeros(diff))).reshape(shape)
        df = pd.DataFrame(Z, index=y.unique(), columns=x.unique())
        ax = sns.heatmap(df)
        pl.title(title)
        pl.xlabel(xname)
        pl.ylabel(yname)
        ax.invert_yaxis()
        pl.plt.show()
        self.plots.append({'type': 'pcolor', 'x':xname, 'y':yname, 'z':zname, 'args':args, 'kwargs':kwargs, 'ax':ax})
        if ax.get_figure() not in self.figs:
            self.figs.append(ax.get_figure())
    
    def update_plot(self):
        loop = asyncio.get_event_loop()
        tasks = []
        self.data
        for plot in self.plots:
            ax = plot['ax']
            if plot['type']=='plot':
                x,y = plot['args'][0], plot['args'][1]
                if type(y) == str:
                    y = [y]
                for yname,line in zip(y,ax.lines):
                    tasks.append(asyncio.ensure_future(self.update_line(ax, line, x, yname)))
            if plot['type']=='pcolor':
                x,y,z = plot['x'], plot['y'], plot['z']
                tasks.append(asyncio.ensure_future(self.update_pcolor(ax, x, y, z)))
        loop.run_until_complete(asyncio.wait(tasks))
        
        display.clear_output(wait=True)
        display.display(*self.figs)
        time.sleep(0.1)
    
    @asyncio.coroutine
    def update_pcolor(self, ax, xname, yname, zname):
        x,y,z = self._data[xname], self._data[yname], self._data[zname]
        shape = (len(y.unique()), len(x.unique()))
        diff = shape[0]*shape[1] - len(z)
        Z = np.concatenate((z.values, np.zeros(diff))).reshape(shape)
        df = pd.DataFrame(Z, index=y.unique(), columns=x.unique())
        cbar_ax = ax.get_figure().axes[1]
        sns.heatmap(df, ax=ax, cbar_ax=cbar_ax)
        ax.set_xlabel(xname)
        ax.set_ylabel(yname)
        ax.invert_yaxis()
    
    @asyncio.coroutine
    def update_line(self, ax, hl, xname, yname):
        hl.set_xdata(self._data[xname])
        hl.set_ydata(self._data[yname])
        ax.relim()
        ax.autoscale()
    
    def watch(self, t_max = 10, param_dict=None):
        '''
        Watch the system until time reaches t_max (in s)
        '''
        if param_dict is None:
            param_dict = self.param_dict
        self.t_max = t_max
        self.measurement.set(watch = t_max)
        self.measure(param_dict)
    
    def sweep(self, ins, sweep_param):
        self.ins = ins
        self.sweep_param = sweep_param
        return self
    
    def do(self, func):
        self.measurement.set(do = func)
    
    def measure(self, param_dict=None):
        if param_dict is None:
            param_dict = self.param_dict
        self.measurement.set(measure = param_dict)
        
    def __getitem__(self, s):
        self.measurement.set(sweep = (self.ins, self.sweep_param, 
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
    
    def close(self):
        self.datacollector.terminate()