import time
import math
from machine import Pin, reset
import network
import ntptime
import json
import requests
import secrets  # separate file that contains your WiFi credentials
import stepper

version = "1.0.8"
print("Toki Clock - Version:", version)

# Wi-Fi credentials
ssid = secrets.WIFI_SSID  # your SSID name stored in secrets.py
password = secrets.WIFI_PASSWORD  # your WiFi password stored in secrets.py

LED = Pin("LED", Pin.OUT)      # digital output for status LED
button = Pin(15, Pin.IN, Pin.PULL_UP)  # onboard button
stepper_control = Pin(0, Pin.OUT)  # stepper motor control pin
STEPPER_DELAY = 0.3 # pause to allow power to stabilize

# Define stepper motor pins
IN1 = 28
IN2 = 27
IN3 = 26
IN4 = 22

# Initialize stepper motor
stepper_motor = stepper.FullStepMotor.frompins(IN1, IN2, IN3, IN4)

# Set the current position as position 0
stepper_motor.reset()

address = "350 5th Avenue, New York, NY"
latitude = 40.7484773
longitude = -73.9881643
settings_file_url = "http://shinyshape.com/tokiclock/toki_clock_settings.json"

def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # Connect to network
    wlan.connect(ssid, password)
    connection_timeout = 10
    while connection_timeout > 0:
        if wlan.status() >= 3:
            break
        connection_timeout -= 1
        print('Waiting for Wi-Fi connection...')
        blink_led(1, 0.1)
        check_button(0)  # allow button check during wait
        time.sleep(1)
    # Check if connection is successful
    if wlan.status() != 3:
        print('Failed to establish a network connection')
        return False
    else:
        print('Connection successful!')
        network_info = wlan.ifconfig()
        print('IP address:', network_info[0])
        return True

def formatted_time(lt):
    return(f"UTC: {lt[0]:04d}-{lt[1]:02d}-{lt[2]:02d} {lt[3]:02d}:{lt[4]:02d}:{lt[5]:02d}")

def blink_led(times, interval=0.2):
    for _ in range(times):
        LED.on()
        time.sleep(interval)
        LED.off()
        time.sleep(interval)

def parse_iso8601(timestamp):
    if 'T' not in timestamp:
        # Extract date only
        year, month, day = timestamp.split('-')
    else:
        # Split the timestamp into date and time
        date_str, time_str = timestamp.split('T')
        # Extract year, month, day
        year, month, day = date_str.split('-')
        if time_str.count(':') == 1:
            # Time only has hours and minutes
            hour, minute = time_str.split(':')
            second = '0'
        else:
            # Extract hours, minutes, seconds
            hour, minute, second = time_str.split(':')
            second = second.split('Z')[0]  # Remove 'Z' if present
    # Combine into final time format
    if 'T' in timestamp:
        tupple_time = (int(year), int(month), int(day), int(hour), int(minute), int(second), int('0'), int('0'))
    else:
        tupple_time = (int(year), int(month), int(day), int('0'), int('0'), int('0'), int('0'), int('0'))
    return(tupple_time)

def fetch_solar_data():
    try:
        # Make GET request
        response = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=sunrise,sunset&past_days=1&forecast_days=2", timeout=10)
        # Get response code
        response_code = response.status_code
        # Get response content
        response_content = response.content
        solar_data = response.json()
        # Print results
        print('Response code: ', response_code)
        # print('Response content:', response_content)
        return solar_data
    except Exception as e:
        print('Error fetching solar data:', e)
        return None
    
def update_solar_data():
    global prior_sunset, sunrise, sunset, next_sunrise, past_sunset_epoch, sunrise_epoch, sunset_epoch, next_sunrise_epoch
    try:
        solar = fetch_solar_data()
        if solar is not None:
            # print('Solar Data:', solar)
            prior_sunset = solar['daily']['sunset'][0]
            sunrise = solar['daily']['sunrise'][1]
            sunset = solar['daily']['sunset'][1]
            next_sunrise = solar['daily']['sunrise'][2]
            timestamp = solar['daily']['time'][1]
            past_sunset_epoch = time.mktime(parse_iso8601(prior_sunset))
            sunrise_epoch = time.mktime(parse_iso8601(sunrise))
            sunset_epoch = time.mktime(parse_iso8601(sunset))
            next_sunrise_epoch = time.mktime(parse_iso8601(next_sunrise))
            print('Prior sunset:', parse_iso8601(prior_sunset))
            print('Sunrise:', parse_iso8601(sunrise))
            print('Sunset:', parse_iso8601(sunset))
            print('Next sunrise:', parse_iso8601(next_sunrise))
            print('Prior sunset epoch:', past_sunset_epoch)
            print('Sunrise epoch:', sunrise_epoch)
            print('Sunset epoch:', sunset_epoch)
            print('Next sunrise epoch:', next_sunrise_epoch)
            print('Date:', parse_iso8601(timestamp))
        else:
            print('No solar data available')
    except Exception as e:
        print('Error parsing solar data:', e)
    
def open_config():
    try:
        with open('config.json', 'r') as f:
            config_str = f.read()
            config = json.loads(config_str)
            # print(config)
            return config
    except OSError:
        print("Creating configuration file.")
        try:
            with open("config.json", "w") as f:
                config = {"address": "350 5th Avenue, New York, NY", "latitude": 40.7484773, "longitude": -73.9881643, "setttings_file_url": "http://shinyshape.com/windlantern/wind_lantern_settings.json"}
                json_string = json.dumps(config)
                # print(config)
                f.write(json_string)
                return config
        except Exception as e:
            print("Error storing light levels:", e)

def save_config():
    try:
        with open("config.json", "r") as f:
            config_str = f.read()
            config = json.loads(config_str)
            if (config.get('address') == address and
                config.get('latitude') == latitude and
                config.get('longitude') == longitude and
                config.get('settings_file_url') == settings_file_url):
                print("Configuration unchanged, not saving.")
                return
    except Exception as e:
        print("Error reading config for comparison:", e)
    try:
        with open("config.json", "w") as f:
            config = {"address": address, "latitude": latitude, "longitude": longitude, "settings_file_url": settings_file_url}
            json_string = json.dumps(config)
            # print(config)
            f.write(json_string)
            print("Configuration saved.")
    except Exception as e:
        print("Error saving config:", e)

def fetch_address(url):
    try:
        # Make GET request
        response = requests.get(url, timeout=10)
        # Get response code
        response_code = response.status_code
        print('Response code: ', response_code)
        # response_content = response.content
        # print('Response content:', response_content)
        config_raw = response.json()
        # Print results
        print('Configuration: ', config_raw)
        return config_raw
    except Exception as e:
        print('Error fetching settings:', e)
        return None

def fetch_location_from_address(address):
    try:
        headers = {
            "User-Agent": "rp2"  # Add a custom user agent
        }
        response = requests.get(f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1", headers=headers, timeout=10)
        # print(response.content)
        response_code = response.status_code
        response_content = response.content
        location_data = response.json()
        print('Response code: ', response_code)
        
        if location_data:
            lat = location_data[0]['lat']
            lon = location_data[0]['lon']
            print(f"Fetched coordinates for address '{address}': Latitude {lat}, Longitude {lon}")
            return float(lat), float(lon)
        else:
            raise ValueError("Location not found")
    except Exception as e:
        print('Error fetching location data:', e)
        return None, None  
    
async def update_location():
    global address, latitude, longitude, set
    location = fetch_address(settings_file_url)
    if location is not None:
        address = location.get('address')
        print("Using Address:", address)
        if address:
            latitude, longitude = fetch_location_from_address(address.replace(" ", "+"))
            save_config()
    else:
        print("Using default coordinates")

def calculate_toki(prior_sunset_epoch, sunrise_epoch, sunset_epoch, next_sunrise_epoch, current_epoch):
    if current_epoch < sunrise_epoch:
        # Before sunrise
        print('Before sunrise')
        toki_percent = (current_epoch - prior_sunset_epoch) / (sunrise_epoch - prior_sunset_epoch)
        toki_angle = 90 + toki_percent * 180
    elif current_epoch < sunset_epoch:
        # Between sunrise and sunset
        print('Between sunrise and sunset')
        toki_percent = (current_epoch - sunrise_epoch) / (sunset_epoch - sunrise_epoch)
        toki_angle = 270 + toki_percent * 180
    else:
        # After sunset
        print('After sunset')
        toki_percent = (current_epoch - sunset_epoch) / (next_sunrise_epoch - sunset_epoch)
        toki_angle = 90 + toki_percent * 180
    print('Toki percent:', toki_percent)
    toki_hour = math.ceil(toki_percent * 6)
    return round(toki_angle % 360), toki_hour

def check_button(toki_angle):
    if button.value() == 0:
        print('Button pressed, returning to angle 0')
        stepper_control.on()
        time.sleep(STEPPER_DELAY)
        stepper_motor.step_until_angle(0)
        time.sleep(2)
        print('Entering manual adjustment mode. Hold button to rotate clockwise.')
        while button.value() == 0:
            # Move stepper 1 degree at a time while button is held
            stepper_motor.step(34)
            time.sleep(0.1)
        print('Exiting manual adjustment mode.')
        stepper_motor.reset()
        time.sleep(1)
        print(f"Toki Angle: {toki_angle:.2f} degrees")
        # Move stepper motor to Toki angle
        stepper_motor.step_until_angle(toki_angle)
        time.sleep(STEPPER_DELAY)
        stepper_control.off()


def stepper_test():
    pass
    #     print('500 clockwise steps')
    #     #Move 500 steps in clockwise direction
    #     stepper_motor.step(500)
    #     sleep(0.5) # stop for a while
        
    #     print('500 counterclockwise steps')
    #     # Move 500 steps in counterclockwise direction
    #     stepper_motor.step(-500)
    #     sleep(0.5) # stop for a while
        
    #     print('Go to position 2000')
    #     # Go to a specific position (in steps)
    #     stepper_motor.step_until(2000)
    #     sleep(0.5) # stop for a while
        
    #     print('Forcce direction to counterclockwise and go to position 2000')
    #     # Force a direction using the dir paramter
    #     stepper_motor.step_until(2000, dir=-1)
    #     sleep(0.5) # stop for a while        
        
    #     print('Go to angle 359')
    #     # Go to a specific position (angle, maximum is 359, otherwise it will spin indefinetely)
    #     stepper_motor.step_until_angle(359)
    #     sleep(0.5) # stop for a while

next_ntp_sync, next_solar_sync = 0, 0
past_sunset_epoch, sunrise_epoch, sunset_epoch, next_sunrise_epoch, current_epoch = 0, 0, 0, 0, 0

def main():
    global next_ntp_sync, next_solar_sync, address, latitude, longitude, settings_file_url
    connection = False
    connection_timeout = 10
    blink_led(3, 0.1)
    while not connection:
            connection = connect_to_wifi()
            connection_timeout -= 1
            if connection_timeout == 0:
                print('Could not connect to Wi-Fi, exiting')
                reset()
    ntp_set = False
    while not ntp_set:
        try:
            print('Syncing time via NTP...')
            ntptime.settime()
            print(f"System time updated to {formatted_time(time.localtime())} via NTP.")
            next_ntp_sync = time.time() + 43200 # update every 12 hours
            ntp_set = True
        except Exception as e:
            print("Failed to update time via NTP.", e)
            print('Retrying in 10 seconds...')
            time.sleep(10)
    while True:
        blink_led(2, 0.1)
        if not connection:
            break # exit if no connection
        # Sync time via NTP immediately, then every 12 hours
        if (time.time() >= next_ntp_sync):
            try:
                print('Syncing time via NTP...')
                ntptime.settime()
                print(f"System time updated to {formatted_time(time.localtime())} via NTP.")
                next_ntp_sync = time.time() + 43200 # update every 12 hours
            except Exception as e:
                last_ntp_sync = time.time()
                next_ntp_sync = time.time() + 600  # try again in 10 minutes
                print("Failed to update time via NTP.", e)
        # Fetch solar data immediately, then every 12 hours
        if (time.time() >= next_solar_sync):
            try:
                print('Fetching solar data...')
                update_solar_data()
                next_solar_sync = time.time() + 43200  # update every 12 hours
            except Exception as e:
                next_solar_sync = time.time() + 600  # try again in 10 minutes
                print("Failed to update time via NTP.", e)
        # Calculate Toki angle
        current_epoch = time.time()
        print('Current epoch time:', current_epoch)
        toki_angle, toki_hour = calculate_toki(past_sunset_epoch, sunrise_epoch, sunset_epoch, next_sunrise_epoch, current_epoch)
        print(f"Toki Angle: {toki_angle:.2f} degrees, Toki Hour: {toki_hour}")
        # Move stepper motor to Toki angle
        stepper_control.on()
        time.sleep(STEPPER_DELAY)
        stepper_motor.step_until_angle(toki_angle)
        time.sleep(STEPPER_DELAY)
        stepper_control.off()
        print('Sleeping for 60 seconds before next update...')
        start_time = time.time()
        while (time.time() - start_time) < 60:
            check_button(toki_angle)
            time.sleep(0.1)

if __name__ == "__main__":
    try:
        # Run the main loop
        main()
    except Exception as e:
        print('Error occurred: ', e)
    except KeyboardInterrupt:
        print('Returning to angle 0')
        stepper_control.on()
        time.sleep(STEPPER_DELAY)
        stepper_motor.step_until_angle(0)
        time.sleep(STEPPER_DELAY)
        stepper_control.off()
        print('Program Interrupted by the user')

     