import time
import asyncio
import numpy as np
import re
from multiprocessing import Process, Pipe
from squidpy.utils import ask_socket, ask_pipe, read_pipe, set_logging_config
import asyncio
import inspect
import logging
import types
from squidpy import instruments as instruments_module

def instrument(class_name, *args, **kwargs):
    instrument_class = getattr(instruments_module, class_name)
    ins_proc = InstrumentDaemon(instrument_class, *args, **kwargs)
    ins = RemoteInstrument(ins_proc._pipe_out)
    return ins

def create_instruments_from_pipes(pipes):
    instruments = InstrumentList()
    for key in pipes:
        ins = RemoteInstrument(pipes[key], name=key)
        instruments.append(ins)
    return instruments

class Instrument(object):
    '''
    Instrument base class.
    '''
    def __init__(self, name, *args, **kwargs):
        super(Instrument, self).__init__()
        self._params = [a[0] for a in inspect.getmembers(type(self), lambda a: type(a)==property)]
        self._name = name
        self._functions = [f[0] for f in inspect.getmembers(type(self), lambda a:type(a) == types.FunctionType) if (not(f[0].startswith('_')) and not(f[0] == 'get_datapoint') and not(f[0] == 'refresh'))]

    def get_datapoint(self, params):
        datapoint = {}
        for param in params:
            datapoint['%s.%s' %(self._name, param)] = getattr(self, param)
        return datapoint

    def refresh(self):
        for param in self._params:
            getattr(self, param)
        return self
    
    def _repr_html_(self):
        '''
        Show a pretty HTML representation of the object for ipynb.
        '''
        html = ["<b>",self._name,"</b> - "]
        html.append(self.__doc__)
        html.append("<table>")
        html.append("<tr><td colspan=2><b>Parameters</b></td></tr>")
        for key in self._params:
            if key in self._units.keys():
                unit = self._units[key]
            else:
                unit = ''
            if hasattr(self, '_' + key):
                value = getattr(self,'_'+key)
            else:
                value = getattr(self, key)
            html.append("<tr>")
            html.append("<td>{0}</td>".format(key))
            html.append("<td>{0} {1}</td>".format(value, unit))
            html.append("</tr>")
        html.append("<tr><td colspan=2><b>Functions</b></td></tr>")
        for key in self._functions:
            html.append("<tr>")
            html.append("<td>{0}</td>".format(key))
            html.append("<td>{0}</td>".format(getattr(self,key).__doc__))
            html.append("</tr>")
        html.append("</table>")
        return ''.join(html)

class InstrumentDaemon(Process):
    '''Process that creates an instrument.'''
    instances = []

    def __init__(self, instrument_class, *args, **kwargs):
        super(InstrumentDaemon, self).__init__()
        self._instrument_class = instrument_class
        self._args = args
        self._kwargs = kwargs
        self._pipe = Pipe()
        self._pipe_out = self._pipe[1]
        self.daemon = True
        self.running = True
        self.start()
        InstrumentDaemon.instances.append(self)

    def run(self):
        # Create instrument
        instrument = self._instrument_class(*self._args, **self._kwargs)
        pipe = self._pipe[0]
        while self.running:
            while not pipe.poll():
                time.sleep(0.01)
            else:
                cmd = pipe.recv()
                if not cmd: break
                logging.debug(instrument._name + '.' + cmd)
                if cmd == 'close':
                    self.running = False
                    pipe.send('None')
                else:
                    try:
                        if '=' in cmd:
                            cmd = cmd.replace(' =','=')
                            cmd = cmd.replace('= ','=')
                            param, value = re.split('=',cmd)
                            if param in instrument._params:
                                setattr(instrument, param, eval(value))
                            else:
                                logging.warning('Instrument %s does not have attribute %s.' %(instrument._name, param))
                            response = 'True'
                        elif '(' in cmd:
                            response = eval('instrument.' + cmd)
                        else:
                            response = str(getattr(instrument, cmd))
                        pipe.send(response)
                    except Exception as e:
                        logging.warning('Command \'%s\' not recognized: %s' %(cmd, e))
                        pipe.send('None')

    def __del__(self):
        self._pipe[0].close()
        self.exitcode

class RemoteInstrument(Instrument):
    instances = []
    def __init__(self, pipe=None, socket=None, name=None):
        self._pipe = pipe
        self._socket = socket
        self._name = name
        self._params = self._get_param('_params')
        self._functions = self._get_param('_functions')
        self._units = self._get_param('_units')
        self.__doc__ = self._get_param('__doc__')
        self._repr_html_ = lambda: self._get_func('_repr_html_')
        for param in self._params:
            setattr(RemoteInstrument, param, property(fget=eval("lambda self: self._get_param('%s')" %param), fset=eval("lambda self, value: self._set_param('%s',value)" %param)))
        for func in self._functions:
            setattr(RemoteInstrument, func, eval("lambda self, *args, **kwargs: self._get_func('%s', *args, **kwargs)" %func))
        self.instances.append(self)

    @property
    def name(self):
        if self._name is None:
            import __main__
            self._name = [key for key in __main__.__dict__ if __main__.__dict__[key] is self][0]
        return self._name

    def _get_func(self, func, *args, **kwargs):
        cmd = '%s(' %func
        for arg in args:
            if type(arg) == str:
                cmd += "'%s'" %arg
            else:
                cmd += '%s' %arg
        cmd += ')'
        return self._ask(cmd)
    
    def _get_param(self, param):
        return self._ask(param)

    def _set_param(self, param, value):
        if type(value) == str:
            cmd = "%s = '%s'" %(param, value)
        else:
            cmd = '%s = %s' %(param, value)
        self._ask(cmd)

    def _ask(self, cmd):
        if self._pipe is not None:
            return ask_pipe(self._pipe, cmd)
        elif self._socket is not None:
            return ask_socket(self._socket, self._name + '.' + cmd)

class InstrumentList(list):
    '''
    Instrument list class. Show an overview of all instruments.
    '''
    def __init__(self, *instruments, socket=None):
        super(InstrumentList, self).__init__(instruments)
        self.set_attributes()
        if socket is not None:
            self.s = socket

    def set_attributes(self):
        self.todict = {ins.name: ins for ins in self}
        for key in self.todict:
            if key is not 'name':
                setattr(self, key, self.todict[key])

    def get_pipes(self):
        return {ins._name: ins._pipe for ins in self}

    def get_datapoint(self, params=None):
        '''
        Get datapoint by reading out all parameters as defined in params.
        '''
        if params is None:
            params = self.all()
        datapoint = {}
        for ins_name in params:
            for param_name in params[ins_name]:
                datapoint.update(self.get_parameter(ins_name, param_name))
        return datapoint

    def get_datapoint_async(self, params=None):
        '''
        Get datapoint by sending out requests to all instrument daemons.
        Only act asynchronous between instruments. Parameters per instrument are obtained synchronously.
        '''
        global datapoint
        if params is None:
            params = self.all()
        datapoint = {}
        loop = asyncio.get_event_loop()
        tasks = []
        for ins_name in params:
            tasks.append(asyncio.ensure_future(self.get_parameter_async(ins_name, params[ins_name])))
        loop.run_until_complete(asyncio.wait(tasks))
        return datapoint

    @asyncio.coroutine
    def get_parameter_async(self, ins, params):
        global datapoint
        pipe, cmd = self.get_pipe_and_cmd(ins, params)
        pipe.send(cmd)
        while not pipe.poll():
            yield from asyncio.sleep(0.01)
        datapoint.update(read_pipe(pipe))

    def get_parameter(self, ins_name, param_name):
        ins = self.todict[ins_name]
        return {'%s.%s' %(ins_name, param_name): getattr(ins, param_name)}

    def get_pipe_and_cmd(self, ins_name, params):
        ins = self.todict[ins_name]
        cmd = 'get_datapoint(%s)' %params
        return ins._pipe, cmd

    def all(self):
        '''Return all parameters per instrument in a dictionary.'''
        return {ins._name: ins._params for ins in self}

    def append(self, *args):
        super(InstrumentList, self).append(*args)
        self.set_attributes()

    def refresh(self):
        for ins in self:
            ins.refresh()
        return self
    
    def _repr_html_(self):
        html = [ins._name + '<br>' for ins in self]
        return ''.join(html)

    def close(self):
        for ins in self:
            ins._ask('close')