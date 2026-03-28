from dynamixel_sdk import *

port = PortHandler('/dev/ttyACM0')
packet = PacketHandler(1.0)
port.openPort()
port.setBaudRate(1000000)

ADDR_LOCK = 55
ADDR_ID   = 5
CURRENT_ID = 1
NEW_ID     = 3  # Change to 3 for the second motor

# Ping to confirm
model_num, result, error = packet.ping(port, CURRENT_ID)
if result != COMM_SUCCESS:
    print(f"❌ Cannot reach motor ID {CURRENT_ID}")
    port.closePort()
    exit()
print(f"✅ Motor found on ID {CURRENT_ID}")

# Unlock EEPROM
packet.write1ByteTxRx(port, CURRENT_ID, ADDR_LOCK, 0)
print("🔓 EEPROM unlocked")

# Write new ID
packet.write1ByteTxRx(port, CURRENT_ID, ADDR_ID, NEW_ID)
print(f"✏️  ID set to {NEW_ID}")

# Lock EEPROM
packet.write1ByteTxRx(port, NEW_ID, ADDR_LOCK, 1)
print("🔒 EEPROM locked")

port.closePort()
print("✅ Done — power cycle the motor to apply")