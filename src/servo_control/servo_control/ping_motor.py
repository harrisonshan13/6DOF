from dynamixel_sdk import *

# Settings
MY_PORT  = '/dev/ttyACM0'
BAUDRATE = 1000000
PROTOCOL = 1.0

# Scan range - checks IDs 1 through 10
ID_RANGE = range(1, 11)

def main():
    

    portHandler   = PortHandler(MY_PORT)
    packetHandler = PacketHandler(PROTOCOL)

    if not portHandler.openPort():
        print("❌ Could not open port. Run: sudo chmod 666 /dev/ttyACM0")
        exit()

    if not portHandler.setBaudRate(BAUDRATE):
        print("❌ Could not set baud rate.")
        exit()

    print(f"🔍 Scanning IDs {ID_RANGE.start} to {ID_RANGE.stop - 1} on {MY_PORT}...\n")

    found = []

    for motor_id in ID_RANGE:
        model_num, result, error = packetHandler.ping(portHandler, motor_id)
        if result == COMM_SUCCESS:
            print(f"  ✅ Motor found — ID: {motor_id}  |  Model Number: {model_num}")
            found.append(motor_id)

    print(f"\n{'─' * 40}")
    if found:
        print(f"✅ {len(found)} motor(s) detected: IDs {found}")
    else:
        print("❌ No motors found. Check wiring and power.")

    portHandler.closePort()