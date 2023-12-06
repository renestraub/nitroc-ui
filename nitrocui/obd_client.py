"""
OBD 2 Test Code

Request speed and writes it to console

https://en.wikipedia.org/wiki/OBD-II_PIDs
"""

from subprocess import Popen, PIPE
import socket
import struct
import time
import logging

from nitrocui.timeout import Timeout


RX_TIMEOUT = 1.0


logger = logging.getLogger('nitroc-ui')


class OBD2():
    def __init__(self, interface, bitrate):
        self.interface = interface
        self.bitrate = bitrate

        self.sock = None
        self.can_frame_fmt = "<IB3x8s"
        self.req_id = 0x7dF
        self.resp_id = 0x7e8
        self.service_current_data = 0x01

    def setup(self):
        try:
            self._enable_interface()

            self.sock = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
            self.sock.bind((self.interface,))
        except OSError:
            logger.warning(f'Cannot bind to interface {self.interface}')

    def cleanup(self):
        self.sock.close()
        self._enable_interface()

    def speed(self):
        return self._query(OBD2_VehicleSpeed())

    def engine_coolant_temp(self):
        return self._query(OBD2_EngineCoolantTemp())

    def engine_speed(self):
        return self._query(OBD2_EngineSpeed())

    def _query(self, pid):
        self._flush_rx_queue()
        if self._request(pid):
            if self._wait_for_response(pid):
                return pid

    def _request(self, pid):
        payload = bytearray()
        payload.append(2)   # bytes to follow
        payload.append(self.service_current_data)   # service
        payload.append(pid.PID)   # PID code
        for _ in range(8 - 3):  # Fill remaining CAN frame
            payload.append(0x55)

        tx_frame = struct.pack(self.can_frame_fmt, self.req_id, len(payload), payload)
        try:
            res = self.sock.send(tx_frame)
            return res == 16
        except OSError:
            # In case no CAN station is present the transmit fails. Eventually
            # the transmit queue fills up and the send() call fails
            # logging.warning("Transmit queue full, send failed")
            return None

    def _wait_for_response(self, pid):
        to = Timeout(RX_TIMEOUT)
        while not to.has_elapsed():
            try:
                self.sock.settimeout(RX_TIMEOUT/10)
                rx_frame = self.sock.recv(16)
                can_id, length, data = struct.unpack(self.can_frame_fmt, rx_frame)
                can_id &= socket.CAN_EFF_MASK

                # Check if expected response is received.
                # At least VAG control units send unsolicited CAN frames. These are silently ignored.
                if can_id == self.resp_id and length == 8:
                    num_bytes = data[0]
                    if num_bytes >= 3 and num_bytes <= 6 and data[1] == self.service_current_data + 0x40 and data[2] == pid.PID:
                        pid.decode(data[3:num_bytes+1])
                        return pid

            except socket.timeout:
                logger.debug("Timeout waiting for response")
                # TODO: Capture OSError here as well?

    def _flush_rx_queue(self):
        self.sock.settimeout(0.000001)  # 1 us, must not be 0.0
        while True:
            try:
                _ = self.sock.recv(16)
            except socket.timeout:
                # logging.warning("Timeout flushing")
                break
            except OSError:
                # Observed once "OSError: [Errno 100] Network is down"
                logger.warning('problem flushing CAN rx queue')
                break

    def _enable_interface(self):
        name = self.interface
        speed = self.bitrate

        logger.info(f"Enabling CAN interface {name} with {speed} bps")

        self._exec_script(['ip', 'link', 'set', name, 'down'])
        self._exec_script(['ip', 'link', 'set', name, 'type', 'can', 'bitrate', str(speed)])
        self._exec_script(['ip', 'link', 'set', name, 'up'])

        # Note: After a transmit error, the interface does not come up properly.
        #       A second link up/down resets the interface.
        # TODO: Check whether interface state can be checked somehow (e.g. dmesg)
        self._exec_script(['ip', 'link', 'set', name, 'down'])
        self._exec_script(['ip', 'link', 'set', name, 'type', 'can', 'bitrate', str(speed)])
        self._exec_script(['ip', 'link', 'set', name, 'up'])

    def _disable_interface(self):
        name = self.interface
        logger.debug(f"Disabling CAN interface {name}")

        self._exec_script(['ip', 'link', 'set', name, 'down'])

    @staticmethod
    def _exec_script(command):
        with Popen(command, stdout=PIPE, stderr=PIPE) as pipe:
            stdout = pipe.stdout.read().decode().strip()
            logger.debug(
                'calling "{}" results in "{}" on stdout'.format(command, stdout)
            )
            stderr = pipe.stderr.read().decode().strip()
            if stderr != '':
                raise OSError(
                    'calling "{}" reported "{}" on stderr'.format(command, stderr)
                )
            rc = pipe.poll()

        return rc, stdout


class OBD2_VehicleSpeed():
    PID = 0x0D

    def __init__(self):
        self._speed = -1

    def decode(self, data):
        self._speed = data[0]

    def value(self):
        return self._speed

    def units(self):
        return "km/h"


class OBD2_EngineCoolantTemp():
    PID = 0x05

    def __init__(self):
        self._temp = -1

    def decode(self, data):
        self._temp = data[0] - 40

    def value(self):
        return self._temp

    def units(self):
        return "°C"


class OBD2_EngineSpeed():
    PID = 0x0C

    def __init__(self):
        self._rpm = -1

    def decode(self, data):
        self._rpm = int((256 * data[0] + data[1]) / 4)

    def value(self):
        return self._rpm

    def units(self):
        return "rpm"


def odb2(interface):
    obd = OBD2(interface, 500*1000)
    obd.setup()

    runtime = 360000
    t = Timeout(runtime)
    while not t.has_elapsed():
        pid1 = obd.speed()
        if pid1:
            print(f'{pid1.value()} {pid1.units()}')
        else:
            print('Cannot get vehicle speed')

        # pid2 = obd.engine_coolant_temp()
        # print(f'{pid2.value()} {pid2.units()}')

        # pid3 = obd.engine_speed()
        # print(f'{pid3.value()} {pid3.units()}')

        time.sleep(0.1)

    obd.cleanup()


if __name__ == "__main__":
    odb2('can0')
