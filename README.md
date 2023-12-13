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

Create the following service file ```nitroc-ui.service``` in ```/usr/lib/systemd/system/```.  You can use the following command to invoke the system editor.

```
systemctl edit --full --force nitroc-ui
```


The service file is also available on [Github](https://github.com/renestraub/nitroc-ui/blob/master/nitroc-ui.service)


```
[Unit]
Description=NITROC Minimal WebUI
After=gnss-mgr.service

[Service]
Type=simple
ExecStart=/usr/local/bin/nitroc-ui-start
PIDFile=/run/nitroc-ui.pid
 
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=10
 
[Install]
WantedBy=multi-user.target
```


Manage the service with the following systemd commands.

```bash
systemctl daemon-reload        # Tell systemd to search for new services
systemctl enable nitroc-ui     # Enable service for next startup

systemctl start nitroc-ui      # Start service right now
```


### Revision History


#### v0.1.0 (20231206)

- Initial release


#### Known Bugs & Limitations

