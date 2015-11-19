from squidpy.experiment import Experiment
from squidpy.instrument import RemoteInstrument, InstrumentList
from squidpy.utils import ask_socket
from multiprocessing import Process, Manager
import socket, select
import gc
import logging

def run_server(instruments, verbose=False):
    manager = Manager()
    output = manager.dict()
    server = Server(instruments, output, verbose)
    server.start()
    return server, output

def get_socket(HOST='localhost', PORT=50007):
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
    def __init__(self, instruments, output, verbose=False):
        self.experiments = {}
        self.instruments = instruments
        self.verbose = verbose
        self.output = output
        self.output['stamps'] = []
        super(Server, self).__init__()

    def create_experiment(self, title, measlist):
        experiment = Experiment(title, self.instruments, measlist)
        stamp = experiment.output['stamp']
        self.experiments[stamp] = experiment
        logging.info('Created experiment with stamp %s' %stamp)
        self.output['stamps'] = self.output['stamps'].append(stamp)
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

        HOST = 'localhost'                 # Symbolic name meaning all available interfaces
        PORT = 50007              # Arbitrary non-privileged port
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
                    conn.sendall(str(eval(cmd)).encode())
                except Exception as e:
                    logging.warning('Exception in server process: %s' %e)
                    conn.sendall(b'Command not recognized.')
                gc.collect()
            conn.close()
            PORT += 1
            if running:
                print('Connection closed. Restarting socket at port %s.' %PORT)
            else:
                print('End command received. Terminating server.')