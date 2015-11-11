import pandas as pd
from multiprocessing import Process, Queue, Pipe
import time
import os
import signal
import pylab as pl
import asyncio
from IPython import display

def create_stamp():
    from datetime import datetime
    import time
    return datetime.fromtimestamp(time.time()).strftime('%Y%m%d_%H%M%S')   

class Data(pd.DataFrame):
    '''
    Data class based on pandas dataframe for saving data in tab-delimited files.
    '''
    def __init__(self, title='', folder='data', stamp = create_stamp(), *args, **kwargs):
        super(Data, self).__init__(*args, **kwargs)
        self.title = title
        self.stamp = stamp
        self.folder = folder
        self.plots = []
        if 'data' in kwargs.keys():
            self._data = kwargs.pop('data')
            super(Data, self).__init__(*args, **kwargs)
    
    def add_dp(self, dp):
        df = self.append(dp, ignore_index = True)
        self.__init__(self.title, self.folder, self.stamp, df)
        
    def save(self, filename=''):
        if filename=='':
            filename = '%s_%s.dat' %(self.stamp, self.title)
        if not os.path.exists(self.folder):
            os.mkdir(self.folder)
        self.to_csv(os.path.join(self.folder,filename), sep='\t')
        
    def plot(self, *args, **kwargs):
        title = '%s_%s' %(self.stamp, self.title)
        kwargs['title'] = title
        ax = super(Data, self).plot(*args, **kwargs)
        self.plots.append({'args': args, 'kwargs': kwargs, 'ax': ax})
    
    def update_plot(self):
        loop = asyncio.get_event_loop()
        tasks = []
        for plot in self.plots:
            x,y = plot['args'][0], plot['args'][1]
            ax = plot['ax']
            if type(y) == str:
                y = [y]
            for yname,line in zip(y,ax.lines):
                tasks.append(asyncio.ensure_future(self.update_line(ax, line, x, yname)))
        loop.run_until_complete(asyncio.wait(tasks))
        
        #pl.plt.draw()
        display.clear_output(wait=True)
        figs = tuple(set([plot['ax'].get_figure() for plot in self.plots]))
        display.display(*figs)
        time.sleep(0.1)
    
    @asyncio.coroutine
    def update_line(self, ax, hl, xname, yname):
        hl.set_xdata(self[xname])
        hl.set_ydata(self[yname])
        ax.relim()
        ax.autoscale()
        
class DataCollector(Process):
    '''
    DataCollector class for continuously storing incoming datapoints from queue.
    Also handles periodic data saving and plotting. Talks to the plotting instance in the main thread through a pipe.
    Returns the Data instance through a dict variable (output) created by a Manager.
    '''
    def __init__(self, output, title='Untitled', folder='data'):
        super(DataCollector, self).__init__()
        self.q = Queue()
        self.data = Data(title, folder)
        self.daemon = True
        self.output = output
        self.folder = folder
        
    def new_file(self, title=''):
        if title=='':
            title = self.title
        self.data = Data(title, self.folder)
    
    def save_data(self):
        self.output['data'] = self.data
        self.output['title'] = self.data.title
        self.output['folder'] = self.data.folder
        self.output['stamp'] = self.data.stamp
        self.data.save()

    def run(self):
        running = True
        while True:
            while not self.q.empty():
                dp = self.q.get()
                if dp is not None:
                    self.data.add_dp(dp)
                    self.save_data()
            time.sleep(0.1)