import peewee

from slyguy import database, gui

from .constants import BCM_PINS, COLOR_INACTIVE, COLOR_ACTIVE, COLOR_DISABLED, COLOR_ERROR
from .language import _

class Button(database.Model):
    class Status(object):
        INACTIVE = 1
        ACTIVE   = 2
        ERROR    = 3
        DISABLED = 4

    pin           = peewee.IntegerField()
    name          = peewee.TextField(null=True)
    enabled       = peewee.BooleanField(default=False)

    pull_up       = peewee.BooleanField(default=True)
    bounce_time   = peewee.FloatField(null=True)
    hold_time     = peewee.FloatField(default=1)
    hold_repeat   = peewee.BooleanField(default=False)

    when_pressed  = peewee.TextField(null=True)
    when_released = peewee.TextField(null=True)
    when_held     = peewee.TextField(null=True)

    status        = peewee.IntegerField(default=Status.INACTIVE)
    error         = peewee.TextField(null=True)

    def label(self):
        status, description = self.status_label()

        return _(_.BTN_LABEL, 
            name   = self.name or '', 
            pin    = self.pin_label, 
            status = status,
            ), description

    @property
    def pin_label(self):
        return _(_.PIN_LABEL, pin=self.pin)

    def status_label(self):
        if self.status == Button.Status.DISABLED:
            return _(_.STATUS_DISABLED, _color=COLOR_DISABLED), _.STATUS_DISABLED_DESC
        elif self.status == Button.Status.ERROR:
            return _(_.STATUS_ERROR, _color=COLOR_ERROR), _(_.STATUS_ERROR_DESC, error=_(self.error, _color=COLOR_ERROR))
        elif self.status == Button.Status.ACTIVE:
            return _(_.STATUS_ACTIVE, _color=COLOR_ACTIVE), _.STATUS_ACTIVE_DESC
        else:
            return _(_.STATUS_INACTIVE, _color=COLOR_INACTIVE), _.STATUS_INACTIVE_DESC

    def has_callbacks(self):
        return self.when_pressed or self.when_released or self.when_held

    def select_pin(self):
        options = [_(_.PIN_LABEL, pin=x) for x in BCM_PINS]
        index = gui.select(_.BTN_PIN, options)
        if index < 0:
            return False

        self.pin = BCM_PINS[index]
        if self.enabled:
            self.enabled = False
            self.toggle_enabled()

        return True

    def select_name(self):
        name = gui.input(_.BTN_NAME, default=self.name or '')
        if not name:
            return False

        self.name = name
        return True

    def toggle_enabled(self):
        if self.enabled:
            self.enabled = False
        else:
            pin_used = Button.select(Button.id).where(Button.id != self.id, Button.pin == self.pin, Button.enabled == True).exists()
            if pin_used:
                if not gui.yes_no(_.DISABLE_OTHER_BTN):
                    return False

                Button.update(enabled=False).where(Button.pin == self.pin).execute()

            self.enabled = True

        return True

    def toggle_pull_up(self):
        self.pull_up = not self.pull_up
        return True

    def select_bounce_time(self):
        bounce_time = gui.input(_.BTN_BOUNCE_TIME, default=str(self.bounce_time) if self.bounce_time else '')
        if not bounce_time:
            return False

        self.bounce_time = float(bounce_time)
        return True

    def select_hold_time(self):
        hold_time = gui.input(_.BTN_HOLD_TIME, default=str(self.hold_time))
        if not hold_time:
            return False

        self.hold_time = float(hold_time)
        return True

    def toggle_hold_repeat(self):
        self.hold_repeat = not self.hold_repeat
        return True

    def select_when_pressed(self):
        when_pressed = gui.input(_.BTN_WHEN_PRESSED, default=self.when_pressed or '')
        if not when_pressed:
            return False

        self.when_pressed = when_pressed
        return True

    def select_when_released(self):
        when_released = gui.input(_.BTN_WHEN_RELEASED, default=self.when_released or '')
        if not when_released:
            return False

        self.when_released = when_released
        return True

    def select_when_held(self):
        when_held = gui.input(_.BTN_WHEN_HELD, default=self.when_held or '')
        if not when_held:
            return False

        self.when_held = when_held
        return True


database.init([Button])
