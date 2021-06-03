from slyguy.migrate import migrate

message = 'My Foxtel Go add-on now supports Foxtel Now.\nTherefore this add-on has been depreciated\nClick Yes to install Foxtel Go add-on'

migrate('plugin.video.foxtel.go', copy_userdata=False, message=message)
