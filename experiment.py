from multiprocessing import Process, Pipe, Manager, get_context, Queue
from squidpy.utils import get_array, ask_socket, read_pipe
from squidpy.instrument import create_instruments_from_pipes, RemoteInstrument, InstrumentList
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
import logging
import asyncio
import gc
ctx = get_context('spawn') # Get Windows-style multiprocessing behavior

class Measurement(ctx.Process):
    '''
    Basic measurement class.
    '''
    def __init__(self, instruments, measlist = [], *args, **kwargs):
        super(Measurement, self).__init__()
        self.pipe = Pipe() # data pipe
        self.instrument_pipes = instruments.get_pipes()
        self.measlist = measlist
    
    def set(self, *args, **kwargs):
        '''
        Add keyword argument as measurement type 
        to measurement list
        '''
        measlist = self.measlist.copy()
        for key in kwargs:
            measlist.append({'type':key, 'params': kwargs[key]})
        self.measlist = measlist

    def get_dp(self, params=None):
        try:
            return self.instruments.get_datapoint_async(params)
        except Exception as e:
            logging.debug('Exception: %s' %e)
            return self.instruments.get_datapoint(params)
    
    def do_measurement(self, measlist):
        if len(measlist)>0:
            meas = measlist.pop(0)
            if meas['type']=='do':
                do_func, args = meas['params']
                if hasattr(self.instruments, 's'):
                    ask_socket(self.instruments.s, '%s(*%s)' %(do_func, args))
                else:
                    eval('%s(*%s)' %(do_func, args))
                self.do_measurement(measlist.copy())
            if meas['type']=='sweep':
                self.recursive_sweep(measlist.copy(), *meas['params'])
            if meas['type']=='sweep_custom':
                self.recursive_sweep_custom(measlist.copy(), *meas['params'])
            if meas['type']=='do_while':
                clause = 'self.instruments.' + meas['params']
                while eval(clause):
                    self.do_measurement(measlist.copy())
            if meas['type']=='measure':
                dp = self.get_dp(meas['params'])
                self.pipe[0].send(dp)
                self.do_measurement(measlist.copy())
    
    def recursive_sweep_custom(self, measlist, ins, param, arr):
        [self.set_param_and_run_next(measlist, ins, param, val) for val in arr]

    def recursive_sweep(self, measlist, ins, param, start, stop, step):
        [self.set_param_and_run_next(measlist, ins, param, val) for val in get_array(start, stop, step)]

    def set_param_and_run_next(self, measlist, ins, param, val):
        setattr(self.instruments.todict[ins], param, val)
        self.do_measurement(measlist.copy())
    
    def end_measurement(self):
        self.pipe[0].send(None)
        [pipe.close() for pipe in self.pipe]

    def run(self):
        self.instruments = create_instruments_from_pipes(self.instrument_pipes)
        self.do_measurement(self.measlist.copy())
        self.end_measurement()

class Sweep(object):
        def __init__(self, experiment, ins, param, arr = []):
            self.ins = ins
            self.param = param
            self.experiment = experiment
            if len(arr)>0:
                self.experiment.set(sweep_custom = (self.ins, self.param, arr))

        def __getitem__(self, s):
            self.experiment.set(sweep = (self.ins, self.param, 
                                 s.start, s.stop, s.step))

class Experiment():
    '''
    Basic experiment class. This class creates the measurement, plot and data collector. It runs the measurement in a separate process, which drops datapoints in a queue.
    The datacollector, also in a separate process, is a daemon that collects all these datapoints in a Data (pd.Dataframe-like) object and saves the data periodically on-disk.
    It also drops the latest Data instance in a pipe for live plotting in the main thread.
    '''
    def __init__(self, title, measlist=[]):
        self.title = title
        self.instruments = InstrumentList(*RemoteInstrument.instances)
        self.manager = Manager()
        self.output = self.manager.dict()
        self.plots = []
        self.figs = []
        self._data = pd.DataFrame()
        self.measurement = Measurement(self.instruments, measlist)
        self.datacollector = DataCollector(self.measurement.pipe[1], self.output, self.title)
        self._user_interrupt = False
    
    @property
    def data(self):
        if 'data' in self.output.keys():
            if hasattr(self, '_data'):
                del self._data
            gc.collect()
            self._data = Data(**self.output)
        return self._data

    def new_file(self):
        '''Create new data file'''
        self.output.clear()
    
    @property
    def running(self):
        try:
            running = self.measurement.is_alive() and (not self._user_interrupt)
            if not running:
                if len(self.plots)>0:
                    if self.plots[0]['type'] is not 'pcolor':
                        display.clear_output(wait=True)
            return running
        except KeyboardInterrupt:
            return False

    @running.setter
    def running(self, value):
        if value is False:
            self.measurement.terminate()
            self.measurement.end_measurement()
    
    def wait_and_get_title(self, timeout=2, tsleep=0):
        '''Wait for data file to fill and return title.'''
        while self.data.empty:
            time.sleep(0.01)
            tsleep+=.01
            if tsleep>timeout:
                raise Exception('Timeout for graph: no data received.')
        title = '%s_%s' %(self._data.stamp, self._data.title)
        return title
    
    def plot(self, *args, **kwargs):
        kwargs['title'] = self.wait_and_get_title()
        ax = self.data.plot(*args, **kwargs)
        self.plots.append({'type': 'plot', 'args': args, 'kwargs': kwargs, 'ax': ax})
        if ax.get_figure() not in self.figs:
            self.figs.append(ax.get_figure())
        self._user_interrupt = False

    def clear_plot(self):
        for fig in self.figs:
            fig.clf()
            pl.close()
        self.figs = []
        self.plots = []
        gc.collect()

    def update_plot(self):
        try:
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
        except KeyboardInterrupt:
            loop.run_until_complete(asyncio.wait(tasks))
            display.clear_output(wait=True)
            display.display(*self.figs)
            self._user_interrupt = True
    
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
        del hl._xorig, hl._yorig
        hl.set_xdata(self._data[xname])
        hl.set_ydata(self._data[yname])
        ax.relim()
        ax.autoscale()
        gc.collect()
    
    def set(self, **kwargs):
        self.measurement.set(**kwargs)

    def sweep(self, sweep_param, arr=[]):
        ins, param = re.split('\.', sweep_param)
        return Sweep(self, ins, param, arr)

    def do_while(self, clause):
        self.set(do_while = clause)
    
    def do(self, func, *args):
        self.set(do = (func, args))
    
    def measure(self, params=None):
        self.set(measure = params)
    
    def run(self):
        if self.measurement.measlist is []:
            raise NameError('Measurement is not defined.')
        if 'measure' not in [meas['type'] for meas in self.measurement.measlist]:
            print('Warning: No \'measure\' command found.')
        if self.measurement.pid is not None:
            measlist = self.measurement.measlist
            self.measurement = Measurement(self.instruments,
                                            measlist)
            if self.datacollector.is_alive():
                self.datacollector.terminate()
            self.datacollector = DataCollector(self.measurement.pipe[1],
                                                self.output,
                                                self.title)
        if not self.datacollector.is_alive():
            self.datacollector.start()
        if not self.measurement.is_alive():
            self.measurement.start()
    
    def __del__(self):
        self.manager.shutdown()
        if self.datacollector.is_alive():
            self.datacollector.terminate()
        self.datacollector.exitcode
        self.measurement.exitcode