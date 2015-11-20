from squidpy.utils import ask_socket, create_stamp
import pandas as pd
from multiprocessing import Process, Queue, Pipe
import time
import os
import select

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
    DataCollector class for continuously storing incoming datapoints from pipe.
    Also handles periodic data saving and plotting.
    Returns the Data instance through a dict variable (output) created by a Manager.
    '''
    def __init__(self, pipe=None, output=None, title='Untitled', folder='data', stamp=None, save_data=True):
        super(DataCollector, self).__init__()
        self.pipe = pipe
        if stamp is None:
            stamp = create_stamp()
        self.title = title
        self.folder = folder
        self.daemon = True
        self.output = output
        self.save_data = save_data
        if self.output.keys() == []:
            self.output['title'] = title
            self.output['folder'] = folder
            self.output['stamp'] = stamp
            self.output['data'] = pd.DataFrame()

    def run(self):
        running = True
        while running:
            while self.pipe.poll():
                dp = self.pipe.recv()
                if dp is not None:
                    self.output['data'] = self.output['data'].append(dp, ignore_index = True)
                    if self.save_data:
                        Data(**self.output).save()
                else:
                    running = False
                    break
            time.sleep(0.01)

class RemoteDataCollector(DataCollector):
    def __init__(self, socket, stamp, timeout = 3, *args, **kwargs):
        super(RemoteDataCollector, self).__init__(*args, **kwargs)
        self.socket = socket
        self.stamp = stamp
        self.lines = 0
        self._columns = []
        self._data_length = 0
        self.timeout = timeout

    @property
    def data_length(self):
        data_length = ask_socket(self.socket, 'self.get_data_length(\'%s\')' %self.stamp)
        if data_length is not None:
            self._data_length = data_length
        return self._data_length

    @property
    def columns(self):
        if self._columns == []:
            self._columns = ask_socket(self.socket, 'self.get_columns(\'%s\')' %self.stamp)
        return self._columns

    def get_dp(self, n=None):
        dp = ask_socket(self.socket, 'self.get_dp(\'%s\', %s)' %(self.stamp, str(n)))
        dp = {key: val for key, val in zip(self.columns, dp)}
        return dp if dp != {} else None

    def get_data(self):
        data = ask_socket(self.socket, 'self.get_data(\'%s\')' %(self.stamp))
        return pd.DataFrame(data, columns = self.columns)

    def run(self):
        running = True
        n = 0
        timeout = 0
        time.sleep(.1)
        if self.data_length>0:
            self.output['data'] = self.get_data()
            n = len(self.output['data'])
        while running and (timeout<self.timeout):
            while self.data_length > n:
                dp = self.get_dp(n)
                if dp is not None:
                    self.output['data'] = self.output['data'].append(dp, ignore_index = True)
                    timeout = 0
                    if self.save_data:
                        Data(**self.output).save()
                else:
                    running = False
                    break
                n+=1
            time.sleep(0.2)
            timeout += 0.2
