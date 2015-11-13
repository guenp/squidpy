from squidpy.instrument import Instrument
from instrumental.drivers.daq import ni

class NIDAQ(Instrument):
	'''
	Instrument driver for NIDAQ card
	'''
	def __init__(self, name='nidaq', dev_name='Dev1'):
		self.units = {'ai0': 'V'}
		self.daq  = ni.NIDAQ(dev_name)
		self._ai0 = self.ai0
		super(NIDAQ, self).__init__(name)
	
	@property
	def ai0(self):
	    return self.daq.ai0.read().magnitude