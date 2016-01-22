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
        filename = '%s_%s.dat' %(self.stamp, self.title)
        if not os.path.exists(self.folder):
            os.mkdir(self.folder)
        self.filename = os.path.join(self.folder,filename)
        self.len = 0
    
    def add_dp(self, dp):
        proc_seqf = open(self.filename,'a')
        if self.len == 0:
            proc_seqf.write(("{}\t"*len(dp) + "\n").format(*sorted(dp.keys())))
        sorted_values = [dp[key] for key in sorted(dp.keys())]
        proc_seqf.write(("{}\t"*len(dp) + "\n").format(*sorted_values))
        proc_seqf.close()
        self.len += 1
        
    def save(self, filename=''):
        if filename != '':
            self.filename = filename
        self.to_csv(self.filename, columns=sorted(self.keys()), sep='\t')
        
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
        data = Data(**self.output)
        while running:
            while self.pipe.poll():
                dp = self.pipe.recv()
                if dp is not None:
                    self.output['data'] = self.output['data'].append(dp, ignore_index = True)
                    if self.save_data:
                        try:
                            data.add_dp(dp)
                        except:
                            pass
                else:
                    running = False
                    break
            time.sleep(0.01)