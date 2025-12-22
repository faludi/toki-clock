import time
from machine import Pin, reset
import network
import ntptime
import json
import secrets  # separate file that contains your WiFi credentials

version = "1.0.0"
print("Toki Clock - Version:", version)

# Wi-Fi credentials
ssid = secrets.WIFI_SSID  # your SSID name stored in secrets.py
password = secrets.WIFI_PASSWORD  # your WiFi password stored in secrets.py

LED = Pin("LED", Pin.OUT)      # digital output for status LED


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


def main():
    global microseasons,printer
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
            print("UTC time:", end=' ')
            show_time()
            time.sleep(10)  # main loop delay

if __name__ == "__main__":
     main()