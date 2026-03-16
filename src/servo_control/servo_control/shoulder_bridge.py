import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import math

# --- REPLACE WITH YOUR ACTUAL MOTOR LIBRARY ---
# from sts3215_library import STS3215 

class ShoulderBridge(Node):
    def __init__(self):
        super().__init__('shoulder_bridge')
        
        # 1. Initialize your Servo Controller here
        # self.servo = STS3215(port='/dev/ttyUSB0', baudrate=1000000)
        # self.servo_id = 1 

        # 2. Subscribe to the joint_states topic from the GUI
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_state_callback,
            10)
        
        self.get_logger().info('Shoulder Bridge Node Started. Listening for "Shoulder JNT"...')

    def joint_state_callback(self, msg):
        try:
            # Find the index of the Shoulder joint in the message
            index = msg.name.index('Shoulder JNT')
            # Position is in Radians
            rad_pos = msg.position[index]
            
            # 3. Convert Radians to Servo Steps
            # STS3215 typically uses 0-4095 for 0-360 degrees
            # (Check your specific motor's zero-point offset)
            deg_pos = math.degrees(rad_pos)
            servo_step = int((deg_pos + 180) * (4096 / 360)) 

            self.get_logger().info(f'Joint: {rad_pos:.2f} rad -> Servo Step: {servo_step}')
            
            # 4. Send command to hardware
            # self.servo.write_position(self.servo_id, servo_step)

        except ValueError:
            # This happens if 'Shoulder JNT' isn't in the message yet
            pass

def main(args=None):
    rclpy.init(args=args)
    node = ShoulderBridge()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()