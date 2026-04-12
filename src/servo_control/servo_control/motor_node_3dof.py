import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from rcl_interfaces.msg import SetParametersResult
from dynamixel_sdk import *
import math

# ─── Register Addresses for STS3215 ───────────────────────────────────────────
ADDR_P_GAIN          = 10 # Proportional Gain (Stiffness)
ADDR_MAX_TORQUE      = 16   # Max Output (0-1000)
ADDR_PUNCH           = 24   # Min Startup Current (0-1000)
ADDR_GOAL_STS        = 42   # Goal Position
ADDR_PRESENT_POS     = 56   # Present Position (read back)

# ─── Motor Mapping (Based on your URDF) ───────────────────────────────────────
JOINT_MAP = {
    '360_JNT': 1,      # Base Rotation
    'SHOULDER_JNT': 3, # Shoulder
    'ELBOW_JNT': 2    # Elbow
}

class STSServoNode3DOF(Node):
    def __init__(self):
        super().__init__('sts_servo_node_3dof')

        # ── Hardware Init ──────────────────────────────────────────────────────
        self.port_handler   = PortHandler('/dev/ttyACM0')
        self.packet_handler = PacketHandler(1.0)

        if not self.port_handler.openPort():
            self.get_logger().error("Hardware error: Could not open /dev/ttyACM0")
            return

        if not self.port_handler.setBaudRate(1000000):
            self.get_logger().error("Hardware error: Failed to set baud rate.")
            return

        # ── Startup Ping Check ────────────────────────────────────────────────
        for name, motor_id in JOINT_MAP.items():
            _, result, _ = self.packet_handler.ping(self.port_handler, motor_id)
            if result == COMM_SUCCESS:
                self.get_logger().info(f"✅ {name} (ID {motor_id}) connected.")
            else:
                self.get_logger().error(f"❌ {name} (ID {motor_id}) NOT FOUND. Check ID/Wiring.")

        # ── Declare Parameters ────────────────────────────────────────────────
        self.declare_parameter('servo_p_gain', 12)
        self.declare_parameter('max_torque', 300)
        self.declare_parameter('punch', 0)

        self.update_hardware()

        # ── ROS Infrastructure ────────────────────────────────────────────────
        self.joint_state_pub = self.create_publisher(JointState, 'joint_states', 10)
        
        # Subscribe to joint_commands (from GUI sliders or controller)
        self.create_subscription(JointState, 'joint_commands', self.joint_command_callback, 10)
        
        # Feedback loop at 20Hz (reads real motor positions)
        self.create_timer(0.05, self.publish_joint_states)
        
        self.add_on_set_parameters_callback(self.parameter_callback)

        self.get_logger().info("3DOF Node Active: JNT_360(1), SHOULDER(2), ELBOW(3)")

    def update_hardware(self):
        """Initial hardware sync with ROS parameters."""
        p_gain = self.get_parameter('servo_p_gain').value
        m_torque = self.get_parameter('max_torque').value
        punch = self.get_parameter('punch').value

        for motor_id in JOINT_MAP.values():
            self.packet_handler.write1ByteTxRx(self.port_handler, motor_id, ADDR_P_GAIN, p_gain)
            self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, ADDR_MAX_TORQUE, m_torque)
            self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, ADDR_PUNCH, punch)

    def parameter_callback(self, params):
        """Live hardware tuning."""
        for param in params:
            for motor_id in JOINT_MAP.values():
                if param.name == 'servo_p_gain':
                    self.packet_handler.write1ByteTxRx(self.port_handler, motor_id, ADDR_P_GAIN, param.value)
                elif param.name == 'max_torque':
                    self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, ADDR_MAX_TORQUE, param.value)
                elif param.name == 'punch':
                    self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, ADDR_PUNCH, param.value)
        return SetParametersResult(successful=True)

    def rad_to_steps(self, rad):
        """Converts URDF radians to STS3215 raw steps (0-4095)."""
        deg = math.degrees(rad)
        steps = int(2048 + (deg * (4096 / 360)))
        return max(0, min(4095, steps))

    def steps_to_rad(self, steps):
        """Converts STS3215 raw steps back to URDF radians."""
        deg = (steps - 2048) * (360 / 4096)
        return math.radians(deg)

    def joint_command_callback(self, msg):
        """Receives commands and writes to the correct motor."""
        for name, motor_id in JOINT_MAP.items():
            if name in msg.name:
                idx = msg.name.index(name)
                steps = self.rad_to_steps(msg.position[idx])
                self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, ADDR_GOAL_STS, steps)

    def publish_joint_states(self):
        """Polls hardware and publishes to /joint_states for RViz visualization."""
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        
        for name, motor_id in JOINT_MAP.items():
            pos_raw, result, _ = self.packet_handler.read2ByteTxRx(self.port_handler, motor_id, ADDR_PRESENT_POS)
            if result == COMM_SUCCESS:
                msg.name.append(name)
                msg.position.append(self.steps_to_rad(pos_raw))
        
        if msg.name:
            self.joint_state_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = STSServoNode3DOF()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()