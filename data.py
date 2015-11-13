import pandas as pd
from multiprocessing import Process, Queue, Pipe
import time
import os

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
    
    def add_dp(self, dp):
        title, folder, stamp = self.title, self.folder, self.stamp
        df = self.append(dp, ignore_index = True)
        self.__init__(title, folder, stamp, df)
        
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
        self.title = title
        self.folder = folder
        self.daemon = True
        self.output = output
        self.output['title'] = title
        self.output['folder'] = folder
        self.output['stamp'] = create_stamp()

    def run(self):
        running = True
        df = pd.DataFrame()
        while True:
            while not self.q.empty():
                dp = self.q.get()
                if dp is not None:
                    df = df.append(dp, ignore_index = True)
                    self.output['data'] = df
                    Data(**self.output).save()
            time.sleep(0.1)