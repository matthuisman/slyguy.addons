from slyguy import plugin, settings

@plugin.route('')
def home(**kwargs):
    settings.open()
