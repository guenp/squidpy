import pandas as pd
from multiprocessing import Process, Queue, Pipe
import time
from squidpy.plotting import *
import os

def create_stamp():
    from datetime import datetime
    import time
    return datetime.fromtimestamp(time.time()).strftime('%Y%m%d_%H%M%S')

class Data(pd.DataFrame):
    '''
    Data class based on pandas dataframe for saving data in tab-delimited files.
    '''
    def __init__(self, title='', folder='data'):
        super(Data, self).__init__()
        self.title = title
        self.stamp = create_stamp()
        self.folder = folder
    
    def add_dp(self, dp):
        df = self.append(dp, ignore_index = True)
        title, stamp = self.title, self.stamp
        super(Data, self).__init__(df)
        self.title, self.stamp = title, stamp
        
    def save(self, filename=''):
        if filename=='':
            filename = '%s_%s.dat' %(self.stamp, self.title)
        if not os.path.exists(self.folder):
            os.mkdir(self.folder)
        self.to_csv(os.path.join(self.folder,filename), sep='\t')
        
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
        plot_pipe, plotter_pipe = Pipe()
        self.plot_pipe = plot_pipe
        self.plotter_pipe = plotter_pipe
        self.plot_time = .1
        self.daemon = True
        self.output = output
        self.folder = folder
        
    def update_plot(self):
        self.plot_pipe.send(self.data)
    
    def finish_plot(self):
        self.plot_pipe.send(None)
        
    def new_file(self, title):
        self.data = Data(title, self.folder)
    
    def save_data(self):
        self.output['data'] = self.data
        self.data.save()
    
    def run(self):
        running = True
        while True:
            while not self.q.empty():
                dp = self.q.get()
                if dp is not None:
                    self.data.add_dp(dp)
                    running = True
                else:
                    self.finish_plot()
                    running = False
                    break
            if not self.data.empty and running:
                self.update_plot()
                self.save_data()
            time.sleep(0.1)