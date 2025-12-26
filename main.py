import time
from machine import Pin, reset
import network
import ntptime
import json
import requests
import secrets  # separate file that contains your WiFi credentials

version = "1.0.0"
print("Toki Clock - Version:", version)

# Wi-Fi credentials
ssid = secrets.WIFI_SSID  # your SSID name stored in secrets.py
password = secrets.WIFI_PASSWORD  # your WiFi password stored in secrets.py

LED = Pin("LED", Pin.OUT)      # digital output for status LED

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

def show_time():
    lt = time.localtime()
    print(f"UTC time: {lt[0]:04d}-{lt[1]:02d}-{lt[2]:02d} {lt[3]:02d}:{lt[4]:02d}:{lt[5]:02d}")

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

# def parse_datetime(timestamp):
#     # Split the timestamp into date and time
#     date_str, time_str = timestamp.split('T')
#     # Extract year, month, day
#     year, month, day = date_str.split('-')
#     # Extract hours and minutes
#     hour, minute = time_str.split(':')
#     # Combine into final time format
#     formatted_time = f"{month}/{day}/{year} {hour:2}:{minute:2} UTC"
#     return(formatted_time)

# def parse_date(timestamp):
#     # Extract year, month, day
#     year, month, day = timestamp.split('-')
#     # Combine into final time format
#     formatted_date = f"{month}/{day}/{year} UTC"
#     return(formatted_date)

def fetch_solar_data():
    try:
        # Make GET request
        response = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=sunrise,sunset&forecast_days=1", timeout=10)
        # Get response code
        response_code = response.status_code
        # Get response content
        response_content = response.content
        solar_data = response.json()
        # Print results
        print('Response code: ', response_code)
        print('Response content:', response_content)
        return solar_data
    except Exception as e:
        print('Error fetching solar data:', e)
        return None
    
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


def main():
    connection = False
    connection_timeout = 10
    blink_led(3, 0.1)
    while not connection:
            connection = connect_to_wifi()
            connection_timeout -= 1
            if connection_timeout == 0:
                print('Could not connect to Wi-Fi, exiting')
                reset()
    try:
        ntptime.settime()
        print(f"System time updated to {time.time()} via NTP.")
        # For testing, you can hard-code a date: (year, month, day, weekday, hour, minute, second, millisecond)
        # RTC().datetime((2026, 11, 7, 2, 20, 31, 0, 0))
        # print(f"System time updated to {time.time()} hard-coded.")
    except:
        print("Failed to update time via NTP.")
    while True:
        blink_led(2, 0.1)
        if not connection:
            break # exit if no connection
        show_time()
        time.sleep(10)  # main loop delay
        # try:
        # Fetch and display weather data
        solar = fetch_solar_data()
        if solar is not None:
            # print('Solar Data:', solar)
            sunrise = solar['daily']['sunrise'][0]
            sunset = solar['daily']['sunset'][0]
            timestamp = solar['daily']['time'][0]
            sunrise_epoch = time.mktime(parse_iso8601(sunrise))
            sunset_epoch = time.mktime(parse_iso8601(sunset))
            print('Sunrise:', parse_iso8601(sunrise))
            print('Sunrise epoch:', sunrise_epoch)
            print('Sunset:', parse_iso8601(sunset))
            print('Sunset epoch:', sunset_epoch)
            solar_noon = (time.mktime(parse_iso8601(sunrise)) + time.mktime(parse_iso8601(sunset))) // 2
            print('Solar noon:', time.localtime(solar_noon))
            print('Date:', parse_iso8601(timestamp))
            if time.time() < sunrise_epoch:
                print("It's before sunrise.")
            elif time.time() > sunset_epoch:
                print("It's after sunset.")

        else:
            print('No solar data available')
        # except Exception as e:
        #     print('Error parsing solar data:', e)
        time.sleep(30)

if __name__ == "__main__":
     main()