from squidpy.instrument import Instrument
from instrumental.drivers.daq import ni

class NIDAQ(Instrument):
	'''
	Instrument driver for NIDAQ card
	'''
	def __init__(self, name='nidaq', dev_name='Dev1'):
		self._daq  = ni.NIDAQ(dev_name)
		super(NIDAQ, self).__init__(name)
		self._units = {'ai0': 'V'}
		self._name = name
		self._units = {}
		self._params = self._daq.get_AI_channels() + self._daq.get_AO_channels()
		for chan in self._daq.get_AI_channels():
			setattr(NIDAQ,chan,property(fget=eval('lambda self: self.get_chan(\'%s\')' %chan)))
			self.units[chan] = 'V'
		for chan in self._daq.get_AO_channels():
			setattr(self, '_%s' %chan, None)
			setattr(NIDAQ,chan,property(fset=eval('lambda self, value: self.set_chan(\'%s\',value)' %chan), fget=eval('lambda self: getattr(self,\'_%s\')' %chan)))
			self.units[chan] = 'V'

	def get_chan(self, chan):
		return getattr(self._daq,chan).read().magnitude
	
	def set_chan(self, chan, value):
		setattr(self, '_%s' %chan, value)
		getattr(self._daq,chan).write('%sV' %value)