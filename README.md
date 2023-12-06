## NITROC User Interface and Cloud Client

![System](https://img.shields.io/badge/system-VCU%20Pro-blue)
![System](https://img.shields.io/badge/system-NG800-blue)


### Introduction

A Web user interface for the NITROC platform. It displays important status information and allows basic maintenance actions. Written in Python, based on Tornado webserver.


### Features

* Display important system information
  * System date/time, load, temperature, input voltage, memory and disk usage
  * Mobile link information: registration state, signal strength, bearer information
  * GNSS fix mode, position and speed
* Determine GSM cell location, including geographic position (uses OpenCellId and OpenStreetMap)
* Execute test ping over mobile network and display latency
* Upload of telemetry to Thingsboard server
* GNSS detailled information and automotive configuration
* Realtime driving display with speed and navigations information, live update
* Traffic information of wwan interface


### Short Description

#### Main Page

The following is the main page, showing most information. To refresh information, reload the page. The slider, next to the Refresh Page button, can be enabled for automatic page refresh.

![Info](https://github.com/renestraub/nitroc-ui/raw/master/preview/info.png)


#### GNSS Status

The GNSS Status page displays information about the GNSS module and especially UDR settings. Since the page has to load a lot of GNSS modem information, it takes 1..2 seconds to load. Refresh page manually to update live data or after a configuration change.

![Gnss](https://github.com/renestraub/nitroc-ui/raw/master/preview/gnss.png)


#### GNSS Config

The GNSS Config page displays the configuration file of the GNSS manager for edit. Changes can be saved and the GNSS manager restarted to apply the changes.

![GnssConfig](https://github.com/renestraub/nitroc-ui/raw/master/preview/gnss-config.png)


#### Realtime Display

For drive tests the realtime page is most suitable. It display drive related information in realtime. The page is updated via a Websocket connection once a second. Check the green dot to see whether the connection to the NITROC webserver is active. The dot blinks once a seconds to signal activity.

![Realtime](https://github.com/renestraub/nitroc/raw/master/preview/realtime.png)


#### WWAN Traffic Page

The mobile traffic on wwan0 interface is summarized on this page in tabular and graphical form. Use this page to check the accumulated traffic and compare against your mobile plan.

![Traffic](https://github.com/renestraub/nitroc/raw/master/preview/traffic.png)



### Requirements

* NITROC Hardware with developer image installed
* Python 3.11+


### Quickstart

1. Install the module with `pip install nitroc-ui`
1. Start webserver from shell `nitroc-ui-start`
1. Open the website with your browser `192.168.137.100` (or whatever IP address you defined)


#### Run from Python

```python
from nitrocui.server import run_server

run_server(port=80)
```


#### Installation as systemd service

Create the following service file ```vcu-ui.service``` in ```/usr/lib/systemd/system/```.  You can use the following command to invoke the system editor.

```
systemctl edit --full --force vcu-ui
```


The service file is also available on [Github](https://github.com/renestraub/vcu-ui/blob/master/vcu-ui.service)


```
[Unit]
Description=VCU Pro Minimal WebUI
After=gnss-mgr.service

[Service]
Type=simple
ExecStart=/usr/bin/vcu-ui-start
PIDFile=/run/vcu-ui.pid
 
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=10
 
[Install]
WantedBy=multi-user.target
```


Manage the service with the following systemd commands.

```bash
systemctl daemon-reload     # Tell systemd to search for new services
systemctl enable vcu-ui     # Enable service for next startup

systemctl start vcu-ui      # Start service right now
```


### Revision History

#### v0.9.5 (20230923)

- Fix LTE RSSI information. Was showing RSRP instead.


#### v0.9.4 (20230917)

- Fix display of hardware version (don't suppress trailing 0)
- Display maxmimum bearer life time since tool start


#### v0.9.3 (20230217)

- Use Ace editor component for GNSS configuration


#### v0.9.2 (20230122)

- Add menu to edit GNSS configuration file and restart GNSS manager to apply
- Remove old configuration option GUI
- Minor UI cleanups


#### v0.9.1 (20230108)

- Improve gpsd resilience, be tolerant if gpsd is not (yet) running
- Display modem type
- Display LTE RSSI and SNR if present


#### v0.9.0 (20221230)

- Update for OEM Linux 1.6.x
- Refactor SysInfo to use sensors command if present
- Improve vnstat error handling
- Improve GNSS module access robustness 


#### v0.8.2 (20221007)

- Update for OEM Linux 1.5.x
- Update to ubxlib 0.4.0 for gpsd compatibility


#### v0.8.0 (20211218)

- Improve realtime view
- Update for OEM Linux with kernel 5.10


#### v0.7.10 (20210822)

- Compute extended signal quality and display it on main screen, realtime view and Thingsboard
- Update signal quality every 2 seconds automatically
- Show radio access technology (RAT) on realtime view, upload to Thingsboard
- Show engine coolant temperature on realtime view
- Remove Enable Signal Meas. Button
- Show start reason and provide it on Thingsboard
- Provide bootloader version on Thingsboard
- Provide modem firmware version on Thingsboard
- Add Powerdown command
- Add Sleep command
- Fix typo in UMTS signal quality display (RSCP)


#### v0.7.0 (20210516)

- Add traffic monitor
- Add SIM information (IMSI, ICCID)
- Reduce number of timestamps in cloud upload by combining more items
- Add optional temperature sensor for NG800 mainboard
- Ignore unwanted obd2 messages


#### v0.6.0 (20210420)

Feature release for environmental tests

- Add OBD-II speed information
- Add 100BASE-T1 port link quality


#### v0.5.4 (20210411)

- Change IMU angles order to Yaw, Pitch, Roll
- Add Network traffic (wwan0, wlan0) query and Thingsboard upload
- Add ubxlib version and UBX protocol version report
- Update to ubxlib version 0.3.5
- Fix problem with GNSS page load/refresh


#### v0.5.3 (20210109)

- Add NG800
- Add disc information (eMMC wear level, root/data partition usage)
- Provide web app manifest to run as app
- Flake8 Python Linting


#### v0.5.2 (20200904)

- Wait for gpsd service to become ready at startup
- Supress minor position changes on cloud upload to save data volume


#### v0.5.0 (20200718)

- Major refactoring of Thingsboard IoT upload
- New transmit queue class


#### v0.4.4 (20200716)

- GNSS lever arm configuration added
- Upgrade to ubxlib 0.1.11 for lever arm


#### v0.4.2 (20200612)

- Updated this documentation
- Report RSRQ, ECIO as dB (not dBm)
- Report bearer info to Thingsboard
- Report UI version to Thingsboard
- Restart ping process after mobile link loss
- Queue telemetry data on upload error to retry later
- GNSS configuration save/reset added
- GNSS state save/clear (save-on-shutdown) added
- System reboot function added
- JavaScript code refactored
- General code cleanup, remove dead code
- Upgrade to ubxlib 0.1.9


#### Known Bugs & Limitations

