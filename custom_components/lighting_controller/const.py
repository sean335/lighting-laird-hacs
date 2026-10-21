"""Constants for the Lighting Controller integration."""

DOMAIN = "lighting_controller"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
DEFAULT_PORT = 80

# Platforms
PLATFORMS = ["light", "event"]

# Bus Event Name
EVENT_LIGHTING_CONTROLLER = "lighting_controller_event"

# Event Attributes
ATTR_EVENT_TYPE = "type"
ATTR_PANEL_ID = "panel_id"
ATTR_PANEL_NAME = "panel_name"
ATTR_PIN = "pin"
ATTR_BUTTON_ID = "button_id"
ATTR_BUTTON_NAME = "button_name"
ATTR_STATE = "state"
ATTR_DIRECTION = "direction"
ATTR_STEP = "step"
ATTR_PATTERN_ID = "pattern_id"
ATTR_PATTERN_NAME = "pattern_name"
ATTR_LAMP_ID = "lamp_id"
ATTR_BRIGHTNESS = "brightness"
ATTR_IS_ON = "is_on"

# Services
SERVICE_SET_BUTTON_LED = "set_button_led"
SERVICE_IDENTIFY_PANEL = "identify_panel"
SERVICE_IDENTIFY_BUTTON = "identify_button"

ATTR_SERVICE_PANEL_ID = "panel_id"
ATTR_SERVICE_PIN = "pin"
ATTR_SERVICE_STATE = "state"
ATTR_SERVICE_BRIGHTNESS = "brightness"

