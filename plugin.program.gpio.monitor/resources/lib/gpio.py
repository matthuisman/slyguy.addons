import os
import sys
import subprocess
import shutil

from six import PY3
from kodi_six import xbmc

from slyguy import gui, database
from slyguy.constants import ADDON_PATH, ADDON_ID
from slyguy.log import log
from slyguy.exceptions import Error
from slyguy.util import set_kodi_string, get_kodi_string, remove_file, md5sum

from .constants import *
from .language import _
from .models import Button

if PY3:
    # http://archive.raspberrypi.org/debian/pool/main/r/rpi.gpio/python3-rpi.gpio_0.7.0~buster-1_armhf.deb
    SO_SRC = os.path.join(ADDON_PATH, 'resources', 'files', '0.7.0_py3.so')
else:
    # http://archive.raspberrypi.org/debian/pool/main/r/rpi.gpio/python-rpi.gpio_0.7.0~buster-1_armhf.deb
    SO_SRC = os.path.join(ADDON_PATH, 'resources', 'files', '0.7.0_py2.so')

SO_DST = os.path.join(ADDON_PATH, 'resources', 'lib', 'RPi', '_GPIO.so')

if not os.path.exists(SO_SRC):
    raise Exception('Missing required {} file'.format(SO_SRC))

if md5sum(SO_SRC) != md5sum(SO_DST):
    remove_file(SO_DST)
    shutil.copy(SO_SRC, SO_DST)

if os.path.exists('/storage/.kodi'):
    SYSTEM = 'libreelec'
elif os.path.exists('/home/osmc'):
    SYSTEM = 'osmc'
elif os.path.exists('/home/pi'):
    SYSTEM = 'raspbian'
elif os.path.exists('/home/xbian'):
    SYSTEM = 'xbian'
else:
    SYSTEM = 'mock'

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import gpiozero

INSTALLED = False
if SYSTEM == 'mock':
    from gpiozero.pins.mock import MockFactory as Factory
    gpiozero.Device.pin_factory = Factory()
    log.debug('System not supported. Using mock factory')
    INSTALLED = True
else:
    try:
        from gpiozero.pins.rpigpio import RPiGPIOFactory as Factory
        gpiozero.Device.pin_factory = Factory()
        gpiozero.Device.pin_factory.pin(BCM_PINS[0]).state
        INSTALLED = True
    except Exception as e:
        log.exception(e)

def install():
    remove_file(SO_DST)
    shutil.copy(SO_SRC, SO_DST)

    if SYSTEM == 'libreelec':
        install_libreelec()
    elif SYSTEM == 'raspbian':
        install_raspbian()
    elif SYSTEM == 'osmc':
        install_osmc()
        return True
    elif SYSTEM == 'xbian':
        install_xbian()
        return True
    elif SYSTEM == 'mock':
        gui.ok(_.SYSTEM_UNSUPPORTED)

def install_libreelec():
    return

def install_raspbian():
    return

def install_osmc():
    sudo_cmd = 'sudo su -c "{}"'
    install_debian(sudo_cmd, 'osmc')

def install_xbian():
    password = gui.input(_.XBIAN_PASSWORD, default='raspberry')
    sudo_cmd = 'echo "{}" | sudo -S su -c "{{}}"'.format(password)

    try:
        install_debian(sudo_cmd, 'xbian')
    except Exception as e:
        log.exception(e)
        raise Error(_.XBIAN_ERROR)

def install_debian(sudo_cmd, user):
    def cmd(cmd):
        return subprocess.check_output(sudo_cmd.format(cmd), shell=True).strip()

    src_path = os.path.join(ADDON_PATH, 'resources', 'files', '99-gpio.rules')
    dst_path = '/etc/udev/rules.d/99-{}.GPIO.rules'.format(ADDON_ID)
    cmd('groupadd -f -r gpio && adduser {0} gpio && adduser root gpio && rm -f "{2}" && cp "{1}" "{2}"'.format(user, src_path, dst_path))

def set_state(pin, state):
    if not INSTALLED:
        return

    log.debug('Set pin {} to {}'.format(pin, state))
    out_pin = gpiozero.Device.pin_factory.pin(int(pin))
    out_pin.output_with_state(int(state))

def callback(function):
    log.debug('Callback: {}'.format(function))

    for function in function.split(FUNCTION_DELIMETER):
        xbmc.executebuiltin(function.strip(), True)

def service():
    def setup_buttons():
        log.debug('Setting up buttons')

        try:
            database.connect()

            Button.update(status=Button.Status.INACTIVE, error=None).where(Button.enabled == True).execute()
            Button.update(status=Button.Status.DISABLED, error=None).where(Button.enabled == False).execute()
            btns = list(Button.select().where(Button.enabled == True))

            buttons = []
            for btn in btns:
                if not btn.has_callbacks():
                    continue

                try:
                    button = gpiozero.Button(btn.pin, pull_up=btn.pull_up,
                        bounce_time=btn.bounce_time or None, hold_time=btn.hold_time, hold_repeat=btn.hold_repeat)

                    if btn.when_pressed:
                        button.when_pressed = lambda function=btn.when_pressed: callback(function)

                    if btn.when_released:
                        button.when_released = lambda function=btn.when_released: callback(function)

                    if btn.when_held:
                        button.when_held = lambda function=btn.when_held: callback(function)
                except Exception as e:
                    log.exception(e)
                    btn.status = Button.Status.ERROR
                    btn.error  = e
                else:
                    btn.status = Button.Status.ACTIVE
                    buttons.append(button)

                btn.save()

            return buttons
        except Exception as e:
            log.debug(e)
            return []
        finally:
            database.close()

    monitor = xbmc.Monitor()

    while not monitor.abortRequested():
        buttons = setup_buttons()

        set_kodi_string('_gpio_reload')
        while not monitor.abortRequested():
            if not monitor.waitForAbort(1) and get_kodi_string('_gpio_reload'):
                break

        for button in buttons:
            button.close()

    gpiozero.Device.pin_factory.close()