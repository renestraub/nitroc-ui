"""
Main Page (Single Page)
"""
import logging

import tornado.web

from ._version import __version__ as version
from .data_model import Model
from .tools import secs_to_hhmm

logger = logging.getLogger('nitroc-ui')


class TE(object):
    """
    Table Element to be displayed in info.tpl
    """
    def __init__(self, header, text):
        self.header = header
        self.text = text


def nice(items, data, linebreak=False):
    res = ''
    for i in items:
        key, header, unit = i
        val = data[key]
        if res != '':
            if linebreak:
                res += '</br>'
            else:
                res += ', '

        res += f'{header}: {val}'
        if unit != '':
            res += f' {unit}'

    return res


class Data():
    def __init__(self, data):
        super().__init__()
        self._data = data

    def get(self, default, *keys):
        dct = self._data
        for key in keys:
            try:
                dct = dct[key]
            except KeyError as e:
                logger.debug(f'cannot get {e}')
                return default
        return dct


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render_page()

    def render_page(self, message=None, console=None):
        logger.info('rendering page')

        try:
            tes = list()
            data = dict()

            # General System Information
            m = Model.instance
            md = m.get_all()
            d = Data(md)

            cloud_log_state = md['cloud']
            serial = d.get('N/A', 'sys-version', 'serial')

            # tes.append(TE('<b>System</b>', ''))
            text = nice([('sys', 'System', ''),
                        ('bl', 'Bootloader', ''),
                        ('hw', 'Hardware', '')],
                        md['sys-version'], True)
            tes.append(TE('Version', text))

            dt = d.get('N/A', 'sys-datetime', 'date')
            tes.append(TE('Date', dt))

            sr = d.get('N/A', 'sys-boot', 'reason')
            tes.append(TE('Start Reason', sr))

            ut = d.get('N/A', 'sys-datetime', 'uptime')
            tes.append(TE('Uptime', ut))

            total, free = d.get((0, 0), 'sys-misc', 'mem')
            total = int(total/1024)
            free = int(free/1024)
            tes.append(TE('Memory', f'Total: {total} MB, Free: {free} MB'))

            wear_slc, wear_mlc = d.get((0, 0), 'sys-disc', 'wear')
            sysroot_info = d.get('N/A', 'sys-disc', 'part_sysroot')
            tes.append(TE('Disc', f'eMMC Wear Level: SLC: {wear_slc} %, MLC: {wear_mlc} %<br>'
                                  f'Root: {sysroot_info}'))

            a, b, c = d.get((0, 0, 0), 'sys-misc', 'load')
            tes.append(TE('Load', f'{a}, {b}, {c}'))

            core1 = d.get((0, 0, 0), 'sys-misc', 'cpu1_freq') / 1000
            core2 = d.get((0, 0, 0), 'sys-misc', 'cpu2_freq') / 1000
            core3 = d.get((0, 0, 0), 'sys-misc', 'cpu3_freq') / 1000
            core4 = d.get((0, 0, 0), 'sys-misc', 'cpu4_freq') / 1000
            tes.append(TE('CPU Frequency', f'{core1:.0f}, {core2:.0f}, {core3:.0f}, {core4:.0f} MHz'))

            tes.append(TE('<b>Temperatures</b>', ''))

            temp_str = ""
            temp = d.get(0, 'sys-misc', 'temp_mb')
            if temp:
                temp_str += f'Mainboard: {temp:.0f} °C'
            temp = d.get(0, 'sys-misc', 'temp_mb2')
            if temp:
                temp_str += f', {temp:.0f} °C'
            temp = d.get(0, 'sys-misc', 'temp_eth')
            if temp:
                temp_str += f', ETH {temp:.0f} °C'
            tes.append(TE('PCB', temp_str))

            temp_str = ""
            temp = d.get(0, 'sys-misc', 'temp_nmcf1')
            if temp:
                temp_str += f'1: {temp:.0f} °C, '
            temp = d.get(0, 'sys-misc', 'temp_nmcf2')
            if temp:
                temp_str += f'2: {temp:.0f} °C, '
            temp = d.get(0, 'sys-misc', 'temp_nmcf3')
            if temp:
                temp_str += f'3: {temp:.0f} °C, '
            temp = d.get(0, 'sys-misc', 'temp_nmcf4')
            if temp:
                temp_str += f'4: {temp:.0f} °C'
            tes.append(TE('NMCF', temp_str))

            temp_str = ""
            temp = d.get(0, 'sys-misc', 'temp_phy1')
            if temp:
                temp_str += f'1: {temp:.0f} °C, '
            temp = d.get(0, 'sys-misc', 'temp_phy2')
            if temp:
                temp_str += f'2: {temp:.0f} °C, '
            temp = d.get(0, 'sys-misc', 'temp_phy3')
            if temp:
                temp_str += f'3: {temp:.0f} °C'
            if temp_str != "":
                tes.append(TE('ETH PHY', temp_str))

            temp = d.get(0, 'sys-misc', 'temp_eth_switch')
            if temp:
                temp_str += f'{temp:.0f} °C'
                tes.append(TE('ETH Switch', temp_str))

            temp_str = ""
            temp = d.get(0, 'sys-misc', 'temp_tc1')
            if temp:
                temp_str += f'1: {temp:.0f} °C, '
            temp = d.get(0, 'sys-misc', 'temp_tc2')
            if temp:
                temp_str += f'2: {temp:.0f} °C, '
            temp = d.get(0, 'sys-misc', 'temp_tc3')
            if temp:
                temp_str += f'3: {temp:.0f} °C, '
            temp = d.get(0, 'sys-misc', 'temp_tc4')
            if temp:
                temp_str += f'4: {temp:.0f} °C'
            temp = d.get(0, 'sys-misc', 'temp_tc5')
            if temp:
                temp_str += f'5: {temp:.0f} °C'
            temp = d.get(0, 'sys-misc', 'temp_tc6')
            if temp:
                temp_str += f'6: {temp:.0f} °C'
            temp = d.get(0, 'sys-misc', 'temp_tc7')
            if temp:
                temp_str += f'7: {temp:.0f} °C'
            temp = d.get(0, 'sys-misc', 'temp_tc8')
            if temp:
                temp_str += f'8: {temp:.0f} °C'
            if temp_str != "":
                tes.append(TE('Thermocouple', temp_str))

            temp = d.get(0, 'sys-misc', 'temp_nvm_ssd')
            if temp:
                temp_str = f'{temp:.0f} °C'
                tes.append(TE('NVM SSD', temp_str))

            temp = d.get(0, 'sys-misc', 'temp_wifi_wle3000')
            if temp:
                temp_str = f'{temp:.0f} °C'
                tes.append(TE('Wi-Fi WLE3000', temp_str))

            temp_str = ""
            temp = d.get(0, 'sys-misc', 'temp_ap')
            if temp:
                temp_str += f'AP: {temp:.0f} °C, '
            temp = d.get(0, 'sys-misc', 'temp_cp0')
            if temp:
                temp_str += f'CP0: {temp:.0f} °C, '
            temp = d.get(0, 'sys-misc', 'temp_cp2')
            if temp:
                temp_str += f'CP2: {temp:.0f} °C'
            tes.append(TE('CPU/SB', temp_str))

            # v_in = md['sys-misc']['v_in']
            # v_rtc = md['sys-misc']['v_rtc']
            # tes.append(TE('Voltages', f'Input: {v_in:.1f} V, RTC: {v_rtc:.2f} V'))

            tes.append(TE('<b>Power</b>', ''))
            temp_str = ""
            temp = d.get(0, 'sys-misc', 'pwr_mb')
            if temp:
                temp_str += f'Mainboard: {temp:.1f} W, '
            temp = d.get(0, 'sys-misc', 'pwr_eth')
            if temp:
                temp_str += f'ETH: {temp:.1f} W'
            tes.append(TE('PCB', temp_str))

            temp_str = ""
            temp = d.get(0, 'sys-misc', 'pwr_nmcf1')
            if temp:
                temp_str += f'1: {temp:.1f} W, '
            temp = d.get(0, 'sys-misc', 'pwr_nmcf2')
            if temp:
                temp_str += f'2: {temp:.1f} W, '
            temp = d.get(0, 'sys-misc', 'pwr_nmcf3')
            if temp:
                temp_str += f'3: {temp:.1f} W, '
            temp = d.get(0, 'sys-misc', 'pwr_nmcf4')
            if temp:
                temp_str += f'4: {temp:.1f} W'
            tes.append(TE('NMCF', temp_str))


            # Network Information
            tes.append(TE('', ''))
            tes.append(TE('<b>Network</b>', ''))

            rx, tx = d.get((None, None), 'net-wwan0', 'bytes')
            if rx and tx:
                rx = int(rx) / 1000000
                tx = int(tx) / 1000000
                tes.append(TE('wwan0', f'Rx: {rx:.1f} MB, Tx: {tx:.1f} MB'))

            rx, tx = d.get((None, None), 'net-wlan0', 'bytes')
            if rx and tx:
                rx = int(rx) / 1000000
                tx = int(tx) / 1000000
                tes.append(TE('wlan0', f'Rx: {rx:.1f} MB, Tx: {tx:.1f} MB'))

            # Modem Information
            mi = md['modem']
            if 'modem-id' in mi:
                tes.append(TE('', ''))
                tes.append(TE('<b>Mobile</b>', ''))

                tes.append(TE('Modem Id', mi['modem-id']))

                vendor = mi['vendor']
                model = mi['model']
                tes.append(TE('Type', f'{vendor} {model}'))

                state = mi['state']

                # # Sometimes ModemManager seems to report wrong access tech
                # # Display RAT as reported by --signal-get if it differs
                access_tech = mi['access-tech']
                if 'access-tech2' in mi:
                    access_tech2 = mi['access-tech2']
                    tes.append(TE('State', f'{state}, {access_tech} {access_tech2}'))
                else:
                    tes.append(TE('State', f'{state}, {access_tech}'))

                if 'location' in mi:
                    loc_info = mi['location']
                    if loc_info['mcc']:
                        text = nice([('mcc', 'MCC', ''),
                                    ('mnc', 'MNC', ''),
                                    ('lac', 'LAC', ''),
                                    ('cid', 'CID', '')],
                                    loc_info)
                        tes.append(TE('Cell', text))
                        data.update(loc_info)

                # Display quality as reported by MM
                sq = mi['signal-quality']
                sq_str = f'{sq}%'
                # if 'signal-quality2' in mi:
                #     sq2 = mi['signal-quality2']
                #     sq_str += f' ({sq2:.0f}%)'
                tes.append(TE('Signal', sq_str))

                # Raw signal quality information
                print(mi)
                if 'signal-5g' in mi:
                    sig = mi['signal-5g']
                    text = nice([('rsrp', 'RSRP', 'dBm'),
                                ('rsrq', 'RSRQ', 'dB'),
                                ('snr', 'S/N', 'dB')],
                                sig, True)
                    tes.append(TE('Signal 5G', text))
                if 'signal-lte' in mi:
                    sig = mi['signal-lte']
                    if 'rssi' in sig and 'snr' in sig:
                        text = nice([('rsrp', 'RSRP', 'dBm'),
                                    ('rsrq', 'RSRQ', 'dB'),
                                    ('rssi', 'RSSI', 'dB'),
                                    ('snr', 'S/N', 'dB')],
                                    sig, True)
                    else:
                        text = nice([('rsrp', 'RSRP', 'dBm'),
                                    ('rsrq', 'RSRQ', 'dB')],
                                    sig, True)
                    tes.append(TE('Signal LTE', text))
                if 'signal-umts' in mi:
                    sig = mi['signal-umts']
                    text = nice([('rscp', 'RSCP', 'dBm'),
                                ('ecio', 'ECIO', 'dB')],
                                sig, True)
                    tes.append(TE('Signal UMTS', text))

                if 'bearer-id' in mi:
                    tes.append(TE('', ''))
                    tes.append(TE('Bearer Id', mi['bearer-id']))

                    if 'bearer-uptime' in mi:
                        max_ut = None
                        wtm = md['watermark']
                        if 'bearer-uptime' in wtm:
                            max_ut = wtm['bearer-uptime']

                        ut = mi['bearer-uptime']
                        if ut:
                            uth, utm = secs_to_hhmm(ut)
                            val = f'{uth}:{utm:02} hh:mm'

                            if max_ut is not None:
                                max_uth, max_utm = secs_to_hhmm(max_ut)
                                val += f' (max.: {max_uth}:{max_utm:02} hh:mm)'

                            tes.append(TE('Uptime', val))

                            ip = mi['bearer-ip']
                            tes.append(TE('IP', ip))

                    if 'link' in md:
                        if 'delay' in md['link']:
                            delay_in_ms = md['link']['delay'] * 1000.0
                            tes.append(TE('Ping', f'{delay_in_ms:.0f} ms'))

                if 'sim-id' in mi:
                    tes.append(TE('', ''))
                    tes.append(TE('SIM Id', mi['sim-id']))
                    tes.append(TE('IMSI', mi['sim-imsi']))
                    tes.append(TE('ICCID', mi['sim-iccid']))

            else:
                tes.append(TE('', ''))
                tes.append(TE('Modem Id', 'No Modem'))

            # GNSS
            if 'gnss-pos' in md:
                tes.append(TE('', ''))
                tes.append(TE('<b>GNSS</b>', ''))

                pos = md['gnss-pos']
                tes.append(TE('Fix', pos['fix']))
                text = f'Lon: {pos["lon"]:.7f}, Lat: {pos["lat"]:.7f}'
                tes.append(TE('Position', text))
                text = nice([('speed', '', 'km/h')], pos)
                tes.append(TE('Speed', f'{pos["speed"]:.0f} m/s, {pos["speed"]*3.60:.0f} km/h'))

            # OBD-II
            if 'obd2' in md:
                tes.append(TE('', ''))
                tes.append(TE('<b>OBD-II</b>', ''))
                speed = md['obd2']['speed']
                tes.append(TE('Speed', f'{speed/3.60:.0f} m/s, {speed:.0f} km/h'))

            # OBD-II
            if 'phy-broadr0' in md:
                state = md['phy-broadr0']
                tes.append(TE('', ''))
                tes.append(TE('<b>100BASE-T1</b>', ''))
                tes.append(TE('BroadR0', f'{state["state"]}, {state["quality"]} %'))

            self.render('main.html',
                        title=f'{serial}',
                        table=tes,
                        data=data,
                        message=message,
                        console=console,
                        version=version,
                        cloud_log=cloud_log_state)

        except KeyError as e:
            logger.warning(f'lookup error {e}')
            self.render('main.html',
                        title='NITROC',
                        message=f'Data lookup error: {e} not found',
                        table=None,
                        data=None,
                        console=None,
                        version='n/a',
                        cloud_log=False)
