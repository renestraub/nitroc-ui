import subprocess
# import asyncio


def secs_to_hhmm(secs):
    t = int((secs + 30) / 60)
    h = int(t / 60)
    m = int(t % 60)
    return h, m


def ping(ip):
    cp = subprocess.run(['/usr/bin/ping', '-c', '4', ip], stdout=subprocess.PIPE)
    res = cp.stdout.decode()

    return res


"""
async def ping(ip):
    proc = await asyncio.create_subprocess_exec('ping', '-c', '4', ip, stdout=subprocess.PIPE)
    await proc.wait()
    # cp = subprocess.run(['/usr/bin/ping', '-c', '4', ip], stdout=subprocess.PIPE)
    res = proc.stdout.decode()

    return res
"""


def nmcli_c():
    cp = subprocess.run(['/usr/bin/nmcli', 'c'], stdout=subprocess.PIPE)
    res = cp.stdout.decode()

    return res
