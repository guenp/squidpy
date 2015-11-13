import time
import asyncio
import numpy as np
import re
import select

def get_parameter(ins, param):
    '''
    Get instrument parameter and store in datapoint.
    '''
    global datapoint
    datapoint['%s.%s' %(ins.name, param)] = getattr(ins, param)

def get_datapoint(instruments, params=None):
    '''
    Get datapoint by reading out all parameters as defined in param_dict.
    Eventually this should be done asynchronously. Note: figure out why eventloop gives error when executed within a multiprocessing.Process instance.
    '''
    if params is None:
        params = instruments.all()
    datapoint = {}
    for param in params:
        ins_name, param_name = re.split('\.', param)
        datapoint[param] = getattr(instruments.dict()[ins_name], param_name)
    return datapoint

def get_array(start, stop, step):
    if (stop-start)<0:
        step = -step
    return np.arange(start, stop+step, step)

def ask_socket(s, cmd):
    '''query socket and return response'''
    #empty socket buffer
    inputready, o, e = select.select([s],[],[], 0.0)
    if len(inputready)>0:
        for s in inputready: s.recv(1)
    s.sendall(cmd.encode())
    data = s.recv(1024)
    try:
        ans = eval(data)
    except (IndentationError, SyntaxError):
        ans = data.decode()
    return ans

def get_instruments(s=None, HOST='localhost', PORT=50007):
    '''Create socket connection to instrument server and return virtual instruments.'''
    import socket
    if s is None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
    ins_names = ask_socket(s,'[ins.name for ins in instruments]')
    instruments = []
    for ins_name in ins_names:
        instruments.append(VirtualInstrument(s, ins_name))
    return InstrumentList(*instruments, s = s)

def run_instrument_server(instruments, verbose=False):
    '''Run an instrument server.'''
    import socket

    for ins in instruments:
        locals()[ins.name] = ins

    HOST = ''                 # Symbolic name meaning all available interfaces
    PORT = 50007              # Arbitrary non-privileged port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    conn, addr = s.accept()
    print('Connected by', addr)
    while True:
        cmd = conn.recv(1024)
        if not cmd: break
        try:
            if verbose: print(cmd.decode())
            conn.sendall(str(eval(cmd)).encode())
        except (SyntaxError, NameError, AttributeError):
            conn.sendall(b'Command not recognized.')
    conn.close()

class Instrument():
    '''
    Instrument base class.
    '''
    def __init__(self, name, *args, **kwargs):
        self.name = name
        params = []
        for key in vars(self).keys():
            if key[0]=='_':
                params.append(key[1:])
        self.params = params
        
    @property
    def idn(self):
        if hasattr(self, 'visa_handle'):
            return self.visa_handle.ask('*IDN?')
    
    def close(self):
        if hasattr(self, 'visa_handle'):
            self.visa_handle.close()
        
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

class VirtualInstrument(Instrument):
    def __init__(self, s, name):
        self.name = name
        self.s = s
        self.__doc__ = ask_socket(s, '%s.__doc__' %name)

    def __getattr__(self, attr):
        return ask_socket(self.s, '%s.%s' %(self.name, attr))

    def __setattr__(self, attr, value):
        if attr not in ['name', 's', '__doc__']:
            if attr in self.params:
                ask_socket(self.s, 'setattr(%s,\'%s\',%s)' %(self.name, attr, value))
        else:
            super(VirtualInstrument, self).__setattr__(attr, value)

class InstrumentList(list):
    '''
    Instrument list class. Show an overview of all instruments.
    '''
    def __init__(self, *args, **kwargs):
        super(InstrumentList, self).__init__(args)
        for key in self.dict():
            setattr(self, key, self.dict()[key])
        if 's' in kwargs:
            self.s = kwargs.pop('s')
        self.running = False

    def all(self):
        '''Return all parameters in a list.'''
        return ['%s.%s' %(ins.name, param) for ins in self for param in ins.params]

    def dict(self):
        return {ins.name: ins for ins in self}
    
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
