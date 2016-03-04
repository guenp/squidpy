from squidpy.instrument import Instrument
from squidpy.utils import ask_socket, connect_socket

class MontanaCryostation(Instrument):
    '''
    For remote operation of the Montana Cryostation
    '''
    def __init__(self, host, port=7773, name='cryostation'):
        self._s = connect_socket(host, port)
        self._units = {'temperature': 'K', 'temperature_setpoint': 'K'}
        super(MontanaCryostation, self).__init__(name)

    @property
    def temperature(self):
        self._temperature = self._ask('GPT')
        return self._temperature

    @property
    def temperature_stability(self):
        self._temperature_stability = self._ask('GPS')
        return self._temperature_stability
    
    @property
    def temperature_setpoint(self):
        self._temperature = self._ask('GTSP')
        return self._temperature
    
    @temperature.setter
    def temperature_setpoint(self, value):
        self._temperature = self._ask('STSP%s' %value)

    @property
    def chamber_pressure(self):
        self._chamber_pressure = self._ask('GCP')
        return self._chamber_pressure
    
    def stop(self):
        self._ask('STP')

    def start_cooldown(self):
        self._ask('SCD')

    def start_warmup(self):
        self._ask('SWU')

    def _ask(self, cmd):
        return ask_socket(self._s, '0%s%s' %(len(cmd), cmd), 2)