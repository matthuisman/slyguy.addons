from slyguy.migrate import migrate

message = 'SkyGo has made big changes & a new add-on is required.\nCurrently live channels is working. VOD coming soon.\nClick Yes to install the new add-on'

migrate('slyguy.skygo.nz', copy_userdata=False, message=message)