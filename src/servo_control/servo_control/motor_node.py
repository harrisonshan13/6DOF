import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
from dynamixel_sdk import *

# Register Addresses
ADDR_MODE = 33
ADDR_TORQUE = 40
ADDR_SPEED = 44
ADDR_GOAL_SCS = 30
ADDR_GOAL_STS = 42

class STSServoNode(Node):
    def __init__(self):
        super().__init__('sts_servo_node')
        
        # Setup Port
        self.port_handler = PortHandler('/dev/ttyACM0')
        self.packet_handler = PacketHandler(1.0)

        if not self.port_handler.openPort() or not self.port_handler.setBaudRate(1000000):
            self.get_logger().error("硬件连接失败 - Check USB/Power")
            return

        self.get_logger().info("Hardware Ready. Listening on /set_joint_pos")

        # Subscription
        self.subscription = self.create_subscription(
            Int32, 
            'set_joint_pos', 
            self.listener_callback, 
            10)

    def listener_callback(self, msg):
        target = msg.data
        servo_id = 0xFE # Broadcast
        
        # 1. Force Reset/Wake: Mode to Position (0), Torque ON (1), Speed (500)
        self.packet_handler.write1ByteTxRx(self.port_handler, servo_id, ADDR_MODE, 0)
        self.packet_handler.write1ByteTxRx(self.port_handler, servo_id, ADDR_TORQUE, 1)
        self.packet_handler.write2ByteTxRx(self.port_handler, servo_id, ADDR_SPEED, 500)

        # 2. Command Position (Try both common registers)
        self.packet_handler.write2ByteTxRx(self.port_handler, servo_id, ADDR_GOAL_SCS, target)
        self.packet_handler.write2ByteTxRx(self.port_handler, servo_id, ADDR_GOAL_STS, target)

        self.get_logger().info(f"Syncing motor to {target}")

def main(args=None):
    rclpy.init(args=args)
    node = STSServoNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()