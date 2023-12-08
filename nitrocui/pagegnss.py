"""
GNSS Status Page
"""
import logging

import tornado.web

from ._version import __version__ as version
from .data_model import Model
# from .gnss_model import Gnss

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


class GnssHandler(tornado.web.RequestHandler):
    def get(self):
        self.build_gnss()

    def build_gnss(self):
        logger.info('rendering page')

        # gnss = Gnss.instance
        # if gnss.gpsd_connected():
        #     try:
        #         tes = list()
        #         data = dict()

        #         # General System Information
        #         m = Model.instance
        #         md = m.get_all()

        #         serial = md['sys-version']['serial']

        #         gnss.invalidate()   # Enforce that config and status values are re-read

        #         # GNSS Version

        #         ver = gnss.version()
        #         tes.append(TE('<b>Version</b>', ''))
        #         tes.append(TE('HW', ver['hwVersion']))
        #         tes.append(TE('SW', ver['swVersion']))
        #         tes.append(TE('FW', ver['fwVersion']))
        #         tes.append(TE('Protocol', ver['protocol']))
        #         tes.append(TE('', ''))

        #         # GNSS Status (live)
        #         if 'gnss-pos' in md:
        #             # logger.debug("build_gnss 2")
        #             tes.append(TE('<b>Status</b>', ''))

        #             pos = md['gnss-pos']
        #             tes.append(TE('Fix', pos['fix']))
        #             text = f'Lon: {pos["lon"]:.7f}, Lat: {pos["lat"]:.7f}'
        #             tes.append(TE('Position', text))
        #             text = nice([('speed', '', 'km/h')], pos)
        #             tes.append(TE('Speed', f'{pos["speed"]:.0f} m/s, {pos["speed"]*3.60:.0f} km/h'))
        #             # tes.append(TE('', ''))

        #         # Config
        #         data['dyn_model'] = str(gnss.dynamic_model())
        #         data['nmea_protocol'] = gnss.nmea_protocol()
        #         uart_cfg = gnss.uart_settings()
        #         data['uart_settings'] = f'{uart_cfg["bitrate"]} bps, {uart_cfg["mode"]}'

        #         align = gnss.auto_align()
        #         data['imu_auto_align'] = 'On' if align else 'Off'

        #         # logger.debug("build_gnss 7")
        #         align_state = gnss.auto_align_state()
        #         data['imu_auto_align_state'] = align_state

        #         # logger.debug("build_gnss 8")
        #         cfg_angles = gnss.imu_cfg_angles()
        #         data['imu_cfg_roll'] = str(round(cfg_angles['roll']))
        #         data['imu_cfg_pitch'] = str(round(cfg_angles['pitch']))
        #         data['imu_cfg_yaw'] = str(round(cfg_angles['yaw']))

        #         vrp_ant = gnss.vrp_ant()
        #         data['vrp_ant_x'] = str(vrp_ant['x'])
        #         data['vrp_ant_y'] = str(vrp_ant['y'])
        #         data['vrp_ant_z'] = str(vrp_ant['z'])

        #         vrp_imu = gnss.vrp_imu()
        #         data['vrp_imu_x'] = str(vrp_imu['x'])
        #         data['vrp_imu_y'] = str(vrp_imu['y'])
        #         data['vrp_imu_z'] = str(vrp_imu['z'])

        #         # logger.debug("build_gnss 9")
        #         roll, pitch, yaw = gnss.auto_align_angles()
        #         angles_str = f'Yaw: {yaw}°, Pitch: {pitch}°, Roll: {roll}°'
        #         data['imu_angles'] = angles_str

        #         # logger.debug("build_gnss 10")
        #         esf_status = gnss.esf_status()
        #         text = nice([('fusion', 'Fusion', ''),
        #                     ('ins', 'INS', ''),
        #                     ('imu', 'IMU', ''),
        #                     ('imu-align', 'IMU Alignment', '')],
        #                     esf_status)
        #         data['esf_status'] = text
        #         logger.debug(data)

        #         self.render('gnss.html',
        #                     title=f'{serial}',
        #                     table=tes,
        #                     data=data,
        #                     message='',
        #                     version=version)

        #     except KeyError as e:
        #         self.render('gnss.html',
        #                     title='NITROC',
        #                     message=f'Data lookup error: {e} not found',
        #                     table=None,
        #                     data=None,
        #                     version='n/a')
        # else:
        #     self.render('gnss.html',
        #                 title='NITROC',
        #                 message='gpsd service not running',
        #                 table=None,
        #                 data=None,
        #                 version='n/a')


class GnssSaveStateHandler(tornado.web.RequestHandler):
    def get(self):
        pass
        # gnss = Gnss.instance
        # res = gnss.save_state()
        # self.write(res)


class GnssClearStateHandler(tornado.web.RequestHandler):
    def get(self):
        pass
        # gnss = Gnss.instance
        # res = gnss.clear_state()
        # self.write(res)


class GnssFactoryResetHandler(tornado.web.RequestHandler):
    def get(self):
        pass
        # gnss = Gnss.instance
        # res = gnss.reset_config()
        # self.write(res)


class GnssColdStartHandler(tornado.web.RequestHandler):
    def get(self):
        pass
        # gnss = Gnss.instance
        # res = gnss.cold_start()
        # self.write(res)
