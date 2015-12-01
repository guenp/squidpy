from squidpy.experiment import Experiment
from squidpy.data import DataCollector
from squidpy.instrument import RemoteInstrument, InstrumentList
from squidpy.utils import ask_socket, set_logging_config
from multiprocessing import Process, Manager
import socket, select
import gc
import logging

def run_server(instruments, HOST='localhost', PORT=50007, verbose=False):
    server = Server(instruments, HOST, PORT, verbose)
    server.start()
    return server

def get_socket(HOST='localhost', PORT=50007):
    set_logging_config()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    return s

def get_instruments(s=None, HOST='localhost', PORT=50007):
    '''Create virtual instruments for remote operation.'''
    if s is None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
    ins_names = ask_socket(s,'[ins._name for ins in instruments]')
    instruments = []
    for ins_name in ins_names:
        instruments.append(RemoteInstrument(socket=s, name=ins_name))
    return InstrumentList(*instruments, socket = s)

class Server(Process):
    def __init__(self, instruments, host, port, verbose=False):
        self.experiments = {}
        self.instruments = instruments
        self.host = host
        self.port = port
        self.verbose = verbose
        set_logging_config()
        super(Server, self).__init__()

    def create_experiment(self, title, measlist):
        experiment = Experiment(title, self.instruments, measlist)
        stamp = experiment.output['stamp']
        self.experiments[stamp] = experiment
        logging.info('Created experiment with stamp %s' %stamp)
        return stamp

    def get_experiment(self, stamp):
        experiment = self.experiments[stamp]
        return experiment.title, experiment.measurement.measlist

    def get_data_length(self, stamp):
        return len(self.experiments[stamp].data.values)

    def get_columns(self, stamp):
        return list(self.experiments[stamp].data.columns.values)

    def get_dp(self, stamp, n):
        return list(self.experiments[stamp].data.values[n])

    def get_data(self, stamp):
        return [list(dp) for dp in self.experiments[stamp].data.values]

    def run(self):
        '''Run a measurement server for remote communication.'''
        instruments = self.instruments
        for ins in instruments:
            locals()[ins._name] = ins

        HOST = self.host                 # Symbolic name meaning all available interfaces
        PORT = self.port              # Arbitrary non-privileged port
        running = True
        while running:
            print('Starting socket at %s:%s...' %(HOST, PORT))
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s = s
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen(1)
            conn, addr = s.accept()
            print('Connected by %s' %str(addr))
            while True:
                cmd = conn.recv(1024)
                if not cmd: break
                if cmd==b'end':
                    running=False
                    break
                try:
                    if self.verbose: logging.info(cmd.decode())
                    if b'=' in cmd:
                        exec(cmd)
                        response = 'True'
                    else:
                        response = str(eval(cmd))
                    conn.sendall(response.encode())
                except Exception as e:
                    logging.warning('Exception in server process for command %s: %s' %(cmd,e))
                    conn.sendall(b'Command not recognized.')
                gc.collect()
            conn.close()
            if running:
                print('Connection closed. Restarting socket at port %s.' %PORT)
            else:
                print('End command received. Terminating server.')

class RemoteExperiment(Experiment):
    def __init__(self, socket, title='', measlist=[], stamp=None):
        self.manager = Manager()
        self.output = self.manager.dict()
        self.s = socket
        if stamp == None:
            self.title = title
            self.measlist = measlist
        else:
            self.title, self.measlist = self.get_experiment(stamp)
            self.stamp = stamp
        self.plots = []
        self.figs = []
        self._data = pd.DataFrame

    def get_experiment(self, stamp):
        return ask_socket(self.s, 'self.get_experiment(\'%s\')' %stamp)

    def new_file(self):
        return True

    @property
    def running(self):
        running = self.datacollector.is_alive()
        if not running:
            if len(self.plots)>0:
                if self.plots[0]['type'] is not 'pcolor':
                    display.clear_output(wait=True)
        return running

    def create_remote(self):
        self.stamp = ask_socket(self.s, 'self.create_experiment(\'%s\', %s)' %(self.title, self.measlist))

    def start_remote(self):
        ask_socket(self.s, 'self.experiments[\'%s\'].run()' %self.stamp)

    def set(self, *args, **kwargs):
        '''
        Add keyword argument as measurement type 
        to measurement list
        '''
        measlist = self.measlist.copy()
        for key in kwargs:
            measlist.append({'type':key, 'params': kwargs[key]})
        self.measlist = measlist

    def restart_datacollector(self):
        self.manager = Manager()
        self.output = self.manager.dict()
        if hasattr(self, 'datacollector'):
            if self.datacollector.is_alive():
                self.datacollector.terminate()
        self.datacollector = RemoteDataCollector(socket=self.s, title=self.title, output=self.output, stamp=self.stamp, save_data=False)
        # self.output['data'] = self._data
        self.datacollector.start()

    def run(self):
        if self.measlist is []:
            raise NameError('Measurement is not defined.')
        if 'measure' not in [meas['type'] for meas in self.measlist]:
            print('Warning: No \'measure\' command found.')
        self.create_remote()
        if hasattr(self, 'datacollector'):
            if self.datacollector.is_alive():
                self.datacollector.terminate()
        self.datacollector = RemoteDataCollector(socket=self.s, title=self.title, output=self.output, stamp=self.stamp, save_data=False)
        self.datacollector.start()
        self.start_remote()

    def __del__(self):
        self.manager.shutdown()
        if hasattr(self, 'datacollector'):
            if self.datacollector.is_alive():
                self.datacollector.terminate()
        self.datacollector.exitcode

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
