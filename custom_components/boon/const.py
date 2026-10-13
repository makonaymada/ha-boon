"""Constants for the Boon Smart Home integration."""

DOMAIN = "boon"

CONF_PHONE_NUMBER = "phone_number"
CONF_OTP_CODE = "otp_code"
CONF_TOKEN = "token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_USER_ID = "user_id"
CONF_INVITE_CODE = "invite_code"
CONF_CUSTOM_CAMERAS = "custom_cameras"

API_BASE_URL = "https://api.boon.systems:8081"
DEVICE_BASE_URL = "https://elevators-api.boon.systems/v2"

HEADER_ORIGIN_APP = "Boon"
DEFAULT_USER_AGENT = "okhttp/4.12.0"

DEFAULT_SCAN_INTERVAL_SECONDS = 30

EVENT_BOON_CALL = "boon_intercom_call"

PLATFORMS = ["button", "lock", "camera", "sensor"]
