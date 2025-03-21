"""
Main Page (Single Page)
"""
import logging
import tornado.web

from ._version import __version__ as version
from .data_model import Model
from .tools import secs_to_hhmm, format_size, format_frequency

logger = logging.getLogger('nitroc-ui')


class TE(object):
    """
    Table Element to be displayed in info.tpl
    """
    def __init__(self, header, text):
        self.header = '&nbsp;&nbsp;' + header
        self.text = text


class TH(object):
    """
    Table Element to be displayed in info.tpl
    """
    def __init__(self, header):
        self.header = '<b>' + header + '</b>'
        self.text = '' 


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
            assert m
            md = m.get_all()

            cloud_log_state = md.get(False, 'cloud')
            
            serial = md.get('N/A', 'sys-version', 'serial')
            ver_info = md.get(None, 'sys-version')
            text = nice([('sys', 'System', ''),
                        ('bl', 'Bootloader', ''),
                        ('hw', 'Hardware', '')],
                        ver_info,
                        linebreak=True)
            tes.append(TE('Version', text))

            tes.append(TE('Date', md.get('N/A', 'sys-datetime', 'date')))
            tes.append(TE('Start Reason', md.get('N/A', 'sys-boot', 'reason')))
            tes.append(TE('Uptime', md.get('N/A', 'sys-datetime', 'uptime')))

            total, free = md.get((0, 0), 'sys-misc', 'mem')
            total = format_size(int(total * 1024))
            free = format_size(int(free * 1024))
            tes.append(TE('Memory', f'Total: {total}, Free: {free}'))

            wear_slc, wear_mlc = md.get((0, 0), 'sys-disc', 'wear')
            sysroot_info = md.get('N/A', 'sys-disc', 'part_sysroot')
            tes.append(TE('Disc', f'eMMC Wear Level: SLC: {wear_slc} %, MLC: {wear_mlc} %<br>'
                                  f'Root: {sysroot_info}'))

            a, b, c = md.get((0, 0, 0), 'sys-misc', 'load')
            tes.append(TE('Load', f'{a}, {b}, {c}'))

            temp_str = ""
            for i in range(1, 5):
                freq = md.get(0, 'sys-misc', f'cpu{i}_freq')
                freq = format_frequency(freq * 1_000)
                temp_str += f'{freq}, ' 
            temp_str = temp_str.rstrip(', ')
            tes.append(TE('CPU Frequency', temp_str))

            tes.append(TH('Temperatures'))

            temp_str = ""
            temp = md.get(0, 'sys-misc', 'temp_mb')
            if temp:
                temp_str += f'Mainboard: {temp:.0f} °C'
            temp = md.get(0, 'sys-misc', 'temp_mb2')
            if temp:
                temp_str += f', {temp:.0f} °C'
            temp = md.get(0, 'sys-misc', 'temp_eth')
            if temp:
                temp_str += f', ETH {temp:.0f} °C'
            tes.append(TE('PCB', temp_str))

            temp_str = ""
            for i in range(1, 5):
                temp = md.get(0, 'sys-misc', f'temp_nmcf{i}')
                if temp:
                    temp_str += f'{i}: {temp:.0f} °C, '
            temp_str = temp_str.rstrip(', ')
            tes.append(TE('NMCF', temp_str))

            temp_str = ""
            temp = md.get(0, 'sys-misc', 'temp_phy1')
            if temp:
                temp_str += f'1: {temp:.0f} °C, '
            temp = md.get(0, 'sys-misc', 'temp_phy2')
            if temp:
                temp_str += f'2: {temp:.0f} °C, '
            temp = md.get(0, 'sys-misc', 'temp_phy3')
            if temp:
                temp_str += f'3: {temp:.0f} °C'
            temp_str = temp_str.rstrip(', ')
            if temp_str != "":
                tes.append(TE('ETH PHY', temp_str))

            temp = md.get(0, 'sys-misc', 'temp_eth_switch')
            if temp:
                temp_str += f'{temp:.0f} °C'
                tes.append(TE('ETH Switch', temp_str))

            temp_str = ""
            temp = md.get(0, 'sys-misc', 'temp_tc1')
            if temp:
                temp_str += f'1: {temp:.0f} °C, '
            temp = md.get(0, 'sys-misc', 'temp_tc2')
            if temp:
                temp_str += f'2: {temp:.0f} °C, '
            temp = md.get(0, 'sys-misc', 'temp_tc3')
            if temp:
                temp_str += f'3: {temp:.0f} °C, '
            temp = md.get(0, 'sys-misc', 'temp_tc4')
            if temp:
                temp_str += f'4: {temp:.0f} °C, '
            temp = md.get(0, 'sys-misc', 'temp_tc5')
            if temp:
                temp_str += f'5: {temp:.0f} °C, '
            temp = md.get(0, 'sys-misc', 'temp_tc6')
            if temp:
                temp_str += f'6: {temp:.0f} °C, '
            temp = md.get(0, 'sys-misc', 'temp_tc7')
            if temp:
                temp_str += f'7: {temp:.0f} °C, '
            temp = md.get(0, 'sys-misc', 'temp_tc8')
            if temp:
                temp_str += f'8: {temp:.0f} °C, '
            temp_str = temp_str.rstrip(', ')
            if temp_str != "":
                tes.append(TE('Thermocouple', temp_str))

            temp = md.get(0, 'sys-misc', 'temp_nvm_ssd')
            if temp:
                temp_str = f'{temp:.0f} °C'
                tes.append(TE('NVM SSD', temp_str))

            temp = md.get(0, 'sys-misc', 'temp_wifi_wle3000')
            if temp:
                temp_str = f'{temp:.0f} °C'
                tes.append(TE('Wi-Fi WLE3000', temp_str))

            temp_str = ""
            temp = md.get(0, 'sys-misc', 'temp_ap')
            if temp:
                temp_str += f'AP: {temp:.0f} °C, '
            temp = md.get(0, 'sys-misc', 'temp_cp0')
            if temp:
                temp_str += f'CP0: {temp:.0f} °C, '
            temp = md.get(0, 'sys-misc', 'temp_cp2')
            if temp:
                temp_str += f'CP2: {temp:.0f} °C'
            temp_str = temp_str.rstrip(', ')
            tes.append(TE('CPU/SB', temp_str))

            v_in = md.get(0.0, 'sys-misc', 'v_in')
            v_rtc = md.get(0.0, 'sys-misc', 'v_rtc')
            if v_in > 0.0 and v_rtc > 0.0:
                tes.append(TE('Voltages', f'Input: {v_in:.1f} V, RTC: {v_rtc:.2f} V'))

            tes.append(TH('Power'))
            temp_str = ""
            temp = md.get(0, 'sys-misc', 'pwr_mb')
            if temp:
                temp_str += f'Mainboard: {temp:.1f} W, '
            temp = md.get(0, 'sys-misc', 'pwr_eth')
            if temp:
                temp_str += f'ETH: {temp:.1f} W'
            tes.append(TE('PCB', temp_str))

            temp_str = ""
            for i in range(1, 5):
                temp = md.get(0, 'sys-misc', f'pwr_nmcf{i}')
                if temp:
                    temp_str += f'{i}: {temp:.1f} W, '
            temp_str = temp_str.rstrip(', ')
            tes.append(TE('NMCF', temp_str))


            # Network Information
            tes.append(TE('', ''))
            tes.append(TH('Network'))

            inet_access = md.get('unknown', 'network', 'inet-conn')
            tes.append(TE('internet', inet_access))

            rx, tx = md.get((None, None), 'net-wwan0', 'bytes')
            if rx and tx:
                rx = format_size(int(rx))
                tx = format_size(int(tx))
                tes.append(TE('wwan0', f'Rx: {rx}, Tx: {tx}'))

            rx, tx = md.get((None, None), 'net-wlan0', 'bytes')
            if rx and tx:
                rx = format_size(int(rx))
                tx = format_size(int(tx))
                tes.append(TE('wlan0', f'Rx: {rx}, Tx: {tx}'))

            # Modem Information
            if (modem_id := md.get(-1, 'modem', 'modem-id')) != -1:
                mi = m.get_section('modem')
                assert mi

                tes.append(TE('', ''))
                tes.append(TH('Mobile'))

                tes.append(TE('Modem Id', modem_id))

                vendor = mi.get('-', 'vendor')
                model = mi.get('-', 'model')
                tes.append(TE('Type', f'{vendor} {model}'))

                state = md.get('-', 'modem', 'state')

                access_tech = mi.get('n/a', 'access-tech')
                if (access_tech2 := mi.get('', 'access-tech2')) != '':
                    tes.append(TE('State', f'{state}, {access_tech} {access_tech2}'))
                else:
                    tes.append(TE('State', f'{state}, {access_tech}'))

                if mi.exists('location'):
                    default = {'mcc': '-', 'mnc': '-', 'lac': '-', 'cid': '-'}
                    loc_info = mi.get(default, 'location')
                    text = nice([('mcc', 'MCC', ''),
                                ('mnc', 'MNC', ''),
                                ('lac', 'LAC', ''),
                                ('cid', 'CID', '')],
                                loc_info)
                    tes.append(TE('Cell', text))
                    data.update(loc_info)

                # Display quality as reported by MM
                sq = mi.get(0, 'signal-quality')
                sq_str = f'{sq}%'
                tes.append(TE('Signal', sq_str))

                # Raw signal quality information
                if mi.exists('signal-5g'):
                    default = {'rsrp': '-', 'rsrq': '-', 'snr': '-'}
                    sig = mi.get(default, 'signal-5g')
                    text = nice([('rsrp', 'RSRP', 'dBm'),
                                ('rsrq', 'RSRQ', 'dB'),
                                ('snr', 'S/N', 'dB')],
                                sig, 
                                linebreak=True)
                    tes.append(TE('Signal 5G', text))
                if mi.exists('signal-lte'):
                    default = {'rsrp': '-', 'rsrq': '-', 'rssi': '-', 'snr': '-'}
                    sig = mi.get(default, 'signal-lte')
                    if 'rssi' in sig and 'snr' in sig:
                        text = nice([('rsrp', 'RSRP', 'dBm'),
                                    ('rsrq', 'RSRQ', 'dB'),
                                    ('rssi', 'RSSI', 'dB'),
                                    ('snr', 'S/N', 'dB')],
                                    sig, 
                                    linebreak=True)
                    else:
                        text = nice([('rsrp', 'RSRP', 'dBm'),
                                    ('rsrq', 'RSRQ', 'dB')],
                                    sig, 
                                    linebreak=True)
                    tes.append(TE('Signal LTE', text))
                if mi.exists('signal-umts'):
                    default = {'rscp': '-', 'ecio': '-'}
                    sig = mi.get(default, 'signal-umts')
                    text = nice([('rscp', 'RSCP', 'dBm'),
                                ('ecio', 'ECIO', 'dB')],
                                sig, 
                                linebreak=True)
                    tes.append(TE('Signal UMTS', text))

                if (bearer_id := mi.get(-1, 'bearer-id')) != -1:
                    tes.append(TE('Bearer Id', bearer_id))

                    if mi.exists('bearer-uptime'):
                        ut = mi.get(0, 'bearer-uptime')
                        if ut != 0:
                            uth, utm = secs_to_hhmm(ut)
                            val = f'{uth}:{utm:02} hh:mm'

                            max_ut = md.get(None, 'watermark', 'bearer-uptime')
                            if max_ut is not None:
                                max_uth, max_utm = secs_to_hhmm(max_ut)
                                val += f' (max.: {max_uth}:{max_utm:02} hh:mm)'

                            tes.append(TE('Uptime', val))

                            ip = mi.get('-', 'bearer-ip')
                            tes.append(TE('IP', ip))

                if md.exists('link', 'link'):
                    delay_in_ms = md.get(0, 'link', 'link') * 1000.0
                    tes.append(TE('Ping', f'{delay_in_ms:.0f} ms'))

                if (sim_id := mi.get(-1, 'sim-id')) != -1:
                    tes.append(TE('SIM Id', sim_id))
                    tes.append(TE('IMSI', mi.get('-', 'sim-imsi')))
                    tes.append(TE('ICCID', mi.get('-', 'sim-iccid')))
            else:
                tes.append(TE('', ''))
                tes.append(TE('Modem Id', 'No Modem'))

            # GNSS
            if md.exists('gnss-pos'):
                tes.append(TE('', ''))
                tes.append(TH('GNSS'))

                default = {'fix': '-', 'lon': 0.0, 'lat': 0.0, 'speed': 0.0, 'pdop': 99.99}
                pos = md.get(default, 'gnss-pos')

                tes.append(TE('Fix', pos['fix']))
                text = f'Lon: {pos["lon"]:.7f}, Lat: {pos["lat"]:.7f}'
                tes.append(TE('Position', text))
                tes.append(TE('Speed', f'{pos["speed"]:.0f} m/s, {pos["speed"]*3.60:.0f} km/h'))

            # # OBD-II
            # if 'obd2' in md:
            #     tes.append(TE('', ''))
            #     tes.append(TH('OBD-II'))
            #     speed = md['obd2']['speed']
            #     tes.append(TE('Speed', f'{speed/3.60:.0f} m/s, {speed:.0f} km/h'))

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
