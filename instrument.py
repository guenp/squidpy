import time
import asyncio
import numpy as np

#@asyncio.coroutine
def get_parameter(ins, param):
    '''
    Get instrument parameter and store in datapoint.
    '''
    global datapoint
    datapoint['%s.%s' %(ins.name, param)] = getattr(ins, param)

def get_datapoint(param_dict):
    '''
    Get datapoint by reading out all parameters as defined in param_dict.
    Eventually this should be done asynchronously. Note: figure out why eventloop gives error when executed within a multiprocessing.Process instance.
    '''
    global datapoint
    datapoint = {}
    #tasks = []
    #loop = asyncio.get_event_loop()
    for ins in param_dict.keys():
        for param in param_dict[ins].keys():
            get_parameter(ins, param)
            #tasks.append(asyncio.ensure_future(get_parameter(ins, param)))
    #loop.run_until_complete(asyncio.wait(tasks))
    #loop.close()
    return datapoint

def get_array(start, stop, step):
    if (stop-start)<0:
        step = -step
    return np.arange(start, stop+step, step)

class Instrument():
    '''
    Instrument base class.
    '''
    def __init__(self, name):
        self.name = name
        self.gpib_address = ''
        params = []
        for key in vars(self).keys():
            if key[0]=='_':
                params.append(key[1:])
        self.params = params
        
    def _repr_html_(self):
        '''
        Show a pretty HTML representation of the object for ipynb.
        '''
        html = [self.__doc__]
        html.append("<table width=100%>")
        for key in self.params:
            html.append("<tr>")
            html.append("<td>{0}</td>".format(key))
            html.append("<td>{0}</td>".format(getattr(self,key)))
            html.append("</tr>")
        html.append("</table>")
        return ''.join(html)

class InstrumentList(list):
    '''
    Instrument list class. Show an overview of all instruments.
    '''
    def __init__(self, *args):
        super(InstrumentList, self).__init__(args)
    
    def all(self):
        '''
        Return param_dict dictionary with all parameters.
        '''
        param_dict = {ins: {param:ins.units[param] for param in ins.params} for ins in self}
        return param_dict
    
    def _repr_html_(self):
        html = [self.__doc__]
        html.append("<table width=100%>")
        for ins in self:
            html.append("<tr>")
            html.append("<td>{0}</td>".format(ins.name))
            html.append("<td>{0}</td>".format(ins.params))
            html.append("</tr>")
        html.append("</table>")
        return ''.join(html)
    
class Timer():
    '''
    Basic time keeping instrument/stopwatch.
    '''
    def __init__(self):
        self.tstart = 0
        self.name = 'time'
    def get(self):
        if self.tstart==0:
            self.tstart = time.time()
        return time.time()-self.tstart
    def reset(self,tstart=0):
        self.tstart=tstart
    def set(self, *args):
        None
