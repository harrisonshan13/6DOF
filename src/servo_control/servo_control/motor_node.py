import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from dynamixel_sdk import *
import math

# Register Addresses for STS3215
ADDR_MODE = 33
ADDR_TORQUE = 40
ADDR_SPEED = 44
ADDR_GOAL_STS = 42

class STSServoNode(Node):
    def __init__(self):
        super().__init__('sts_servo_node')
        
        # 1. Setup Port - ACM0
        self.port_handler = PortHandler('/dev/ttyACM0')
        self.packet_handler = PacketHandler(1.0)

        if not self.port_handler.openPort():
            self.get_logger().error("Failed to open /dev/ttyACM0.")
            return
            
        if not self.port_handler.setBaudRate(1000000):
            self.get_logger().error("Failed to set Baudrate.")
            return

        # 2. Setup Subscription
        self.subscription = self.create_subscription(
            JointState, 
            'joint_states', 
            self.joint_state_callback, 
            10)

        self.get_logger().info("Bridge Active: RViz 'Shoulder JNT' -> STS3215 ID 1")

    def joint_state_callback(self, msg):
        try:
            if 'Shoulder JNT' in msg.name:
                idx = msg.name.index('Shoulder JNT')
                pos_rad = msg.position[idx]
                
                # Conversion: Radians to 0-4095
                pos_deg = math.degrees(pos_rad)
                target_pos = int(2048 + (pos_deg * (4096 / 360)))
                target_pos = max(0, min(4095, target_pos))
                
                self.send_to_motor(1, target_pos)
                
        except Exception as e:
            self.get_logger().error(f"Error in callback: {e}")

    def send_to_motor(self, servo_id, position):
        # Reverting to TxRx as these are the guaranteed methods in the Python SDK
        self.packet_handler.write1ByteTxRx(self.port_handler, servo_id, ADDR_MODE, 0)
        self.packet_handler.write1ByteTxRx(self.port_handler, servo_id, ADDR_TORQUE, 1)
        self.packet_handler.write2ByteTxRx(self.port_handler, servo_id, ADDR_SPEED, 800)
        
        # Send Position
        dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(
            self.port_handler, servo_id, ADDR_GOAL_STS, position
        )
        
        # Optional: Print error if it fails (uncomment if troubleshooting)
        # if dxl_comm_result != COMM_SUCCESS:
        #     self.get_logger().warn("Comm error")

def main(args=None):
    rclpy.init(args=args)
    node = STSServoNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()