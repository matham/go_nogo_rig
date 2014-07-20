''' Defines the devices used in this experiment.
'''


__all__ = ('DeviceStageInterface', 'Server', 'FTDIDevChannel', 'FTDIPin',
           'FTDIOdors', 'DAQInDevice', 'DAQOutDevice')

import csv
from functools import partial
from os.path import join

from moa.compat import bytes_type, unicode_type
from moa.threads import ScheduledEventLoop
from moa.device import Device

from pybarst.core.server import BarstServer
from pybarst.ftdi import FTDIChannel
from pybarst.ftdi.switch import PinSettings, SerializerSettings
from pybarst.mcdaq import MCDAQChannel
from pybarst.moa.ftdi import FTDIPinDevice, FTDISerializerDevice
from pybarst.moa.mcdaq import MCDAQDevice

from kivy.properties import ConfigParserProperty, BooleanProperty, ListProperty
from kivy.app import App
from kivy.clock import Clock

from go_nogo_rig import device_config_name


class DeviceStageInterface(object):
    ''' Base class for devices used in this project. It provides the callback
    on exception functionality.
    '''

    exception_callback = lambda self, *largs: Clock.schedule_once(partial(
        App.get_running_app().device_exception, *largs))

    def handle_exception(self, exception, event):
        self.exception_callback(exception, event)

    def start_device(self, started_callback):
        pass


class Server(DeviceStageInterface, ScheduledEventLoop, Device):

    def start_device(self, started_callback):
        # create actual server
        self.target = BarstServer(
            barst_path=(self.server_path if self.server_path else None),
            pipe_name=self.server_pipe)

        self.request_callback('start_server', started_callback)

    def start_server(self):
        server = self.target
        server.open_server()

    server_path = ConfigParserProperty('', 'Server', 'barst_path',
        device_config_name, val_type=unicode_type)

    server_pipe = ConfigParserProperty(b'', 'Server', 'pipe',
                                       device_config_name, val_type=bytes_type)


class FTDIDevChannel(DeviceStageInterface, ScheduledEventLoop, Device):

    def start_device(self, started_callback, dev_settings, server):

        self.target = FTDIChannel(
            channels=dev_settings, server=server, desc=self.ftdi_desc,
            serial=self.ftdi_serial)

        self.request_callback('start_channel', started_callback)

    def start_channel(self):
        self.target.open_channel(alloc=True)
        self.target.close_channel_server()
        return self.target.open_channel(alloc=True)

    ftdi_serial = ConfigParserProperty(b'', 'FTDI_chan', 'serial_number',
                                       device_config_name, val_type=bytes_type)

    ftdi_desc = ConfigParserProperty(b'', 'FTDI_chan', 'description_id',
                                     device_config_name, val_type=bytes_type)


class FTDIPin(DeviceStageInterface, FTDIPinDevice):

    def __init__(self, **kwargs):
        mapping = {'pump': self.pump_pin}
        super(FTDIPin, self).__init__(mapping=mapping, input=False, **kwargs)

    def get_settings(self):
        return PinSettings(num_bytes=1, bitmask=(1 << self.pump_pin),
                           output=True)

    def start_device(self, started_callback):
        self.request_callback('activate_pin_device', started_callback)

    def activate_pin_device(self):
        pin = self.target
        pin.open_channel()
        pin.set_state(True)
        pin.write(buff_mask=0xFF, buffer=[0x00])

    pump_pin = ConfigParserProperty(0, 'FTDI_pin', 'pump_pin',
                                    device_config_name, val_type=int)

    pump = BooleanProperty(False, allownone=True)


class FTDIOdors(DeviceStageInterface, FTDISerializerDevice):

    def __init__(self, **kwargs):
        N = 8 * self.num_boards
        mapping = {'p{}'.format(i): i for i in range(N)}
        super(FTDIOdors, self).__init__(mapping=mapping, input=False, **kwargs)

        # now read the odor list
        with open(join(App.get_running_app().data_directory, self.odor_path),
                  'rb') as fh:
            odors = self.odors = ['Odor_{}'.format(i) for i in range(N)]
            for row in csv.reader(fh):
                odors[int(row[0])] = row[1]

    def get_settings(self):
        return SerializerSettings(clock_bit=self.clock_bit,
            data_bit=self.data_bit, latch_bit=self.latch_bit,
            num_boards=self.num_boards, output=True)

    def start_device(self, started_callback):
        self.request_callback('activate_odor_device', started_callback)

    def activate_odor_device(self):
        odors = self.target
        odors.open_channel()
        odors.set_state(True)
        odors.write(set_low=range(8 * self.num_boards))

    p0 = BooleanProperty(False, allownone=True)

    p1 = BooleanProperty(False, allownone=True)

    p2 = BooleanProperty(False, allownone=True)

    p3 = BooleanProperty(False, allownone=True)

    p4 = BooleanProperty(False, allownone=True)

    p5 = BooleanProperty(False, allownone=True)

    p6 = BooleanProperty(False, allownone=True)

    p7 = BooleanProperty(False, allownone=True)

    p8 = BooleanProperty(False, allownone=True)

    p9 = BooleanProperty(False, allownone=True)

    p10 = BooleanProperty(False, allownone=True)

    p11 = BooleanProperty(False, allownone=True)

    p12 = BooleanProperty(False, allownone=True)

    p13 = BooleanProperty(False, allownone=True)

    p14 = BooleanProperty(False, allownone=True)

    p15 = BooleanProperty(False, allownone=True)

    clock_bit = ConfigParserProperty(0, 'FTDI_odor', 'clock_bit',
                                     device_config_name, val_type=int)

    data_bit = ConfigParserProperty(0, 'FTDI_odor', 'data_bit',
                                    device_config_name, val_type=int)

    latch_bit = ConfigParserProperty(0, 'FTDI_odor', 'latch_bit',
                                     device_config_name, val_type=int)

    num_boards = ConfigParserProperty(1, 'FTDI_odor', 'num_boards',
                                      device_config_name, val_type=int)

    odor_path = ConfigParserProperty(u'odor_list.txt', 'FTDI_odor',
        'Odor_list_path', device_config_name, val_type=unicode_type)

    odors = ListProperty([])


class DAQInDevice(DeviceStageInterface, MCDAQDevice):

    def __init__(self, **kwargs):
        mapping = {'nose_beam': self.nose_beam_pin,
                   'reward_beam_r': self.reward_beam_r_pin}
        super(DAQInDevice, self).__init__(mapping=mapping, input=True,
                                          **kwargs)

    def start_device(self, started_callback, server):

        self.target = MCDAQChannel(chan=self.SAS_chan, server=server)

        self.request_callback('start_channel', started_callback)

    def start_channel(self):
        target = self.target
        target.open_channel()
        target.close_channel_server()
        target.open_channel()

    SAS_chan = ConfigParserProperty(0, 'Switch_and_Sense_8_8',
        'channel_number', device_config_name, val_type=int)

    nose_beam = BooleanProperty(False, allownone=True)

    nose_beam_pin = ConfigParserProperty(0, 'Switch_and_Sense_8_8',
        'nose_beam_pin', device_config_name, val_type=int)

    reward_beam_r = BooleanProperty(False, allownone=True)

    reward_beam_r_pin = ConfigParserProperty(0, 'Switch_and_Sense_8_8',
        'reward_beam_r_pin', device_config_name, val_type=int)


class DAQOutDevice(DeviceStageInterface, MCDAQDevice):

    def __init__(self, **kwargs):
        mapping = {'house_light': self.house_light_pin,
                   'stress_light': self.stress_light_pin}
        super(DAQOutDevice, self).__init__(mapping=mapping, **kwargs)

    def start_device(self, started_callback, server):

        self.target = MCDAQChannel(chan=self.SAS_chan, server=server)

        self.request_callback('start_channel', started_callback)

    def start_channel(self):
        self.target.open_channel()

    SAS_chan = ConfigParserProperty(0, 'Switch_and_Sense_8_8',
        'channel_number', device_config_name, val_type=int)

    house_light = BooleanProperty(False, allownone=True)

    house_light_pin = ConfigParserProperty(0, 'Switch_and_Sense_8_8',
        'house_light_pin', device_config_name, val_type=int)

    stress_light = BooleanProperty(False, allownone=True)

    stress_light_pin = ConfigParserProperty(0, 'Switch_and_Sense_8_8',
        'stress_light_pin', device_config_name, val_type=int)