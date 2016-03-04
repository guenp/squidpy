from squidpy.instrument import Instrument
from squidpy.utils import ask_socket, connect_socket

class PPMS(Instrument):
    '''
    For remote operation of the Quantum Design PPMS.
    Make sure to run PyQDInstrument.run_server() in an IronPython console on a machine that can connect to the PPMS control PC's QDInstrument_Server.exe program.
    Attributes represent the system control parameters:
    'temperature', 'temperature_rate', 'temperature_approach', 'field', 'field_rate', 'field_approach', 'field_mode', 'temperature_status', 'field_status', 'chamber'
    '''
    def __init__(self, host, port, s=None, name='ppms'):
        self._name = name
        if s == None:
            self._s = connect_socket(host, port)
        else:
            self._s = s
        self._units = {'temperature': 'K', 'temperature_rate': 'K/min','field': 'Oe', 'field_rate': 'Oe/min'}
        for param in ['temperature', 'temperature_rate', 'field', 'field_rate', 'temperature_approach', 'field_approach', 'field_mode']:
            setattr(PPMS,param,property(fget=eval("lambda self: self._get_param('%s')" %param),
                                                fset=eval("lambda self, value: self._set_param('%s',value)" %param)))
        for param in ['temperature_status', 'field_status', 'chamber']:
            setattr(PPMS,param,property(fget=eval("lambda self: self._get_param('%s')" %param)))
        self._params = ['temperature', 'temperature_rate', 'temperature_approach', 'field', 'field_rate', 'field_approach', 'field_mode', 'temperature_status', 'field_status', 'chamber']
        self._functions = []

    def _get_param(self, param):
        return ask_socket(self._s, param)

    def _set_param(self, param, value):
        if type(value) == str:
            cmd = "%s = '%s'" %(param, value)
        else:
            cmd = '%s = %s' %(param, value)
        return ask_socket(self._s, cmd)

    def __del__(self):
        self._s.close()