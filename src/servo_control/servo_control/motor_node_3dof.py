import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from rcl_interfaces.msg import SetParametersResult
from dynamixel_sdk import *
import math

# ─── Register Addresses for STS3215 ───────────────────────────────────────────
ADDR_P_GAIN          = 21   # Proportional Gain (Stiffness)
ADDR_MAX_TORQUE      = 16   # Max Output (0-1000)
ADDR_PUNCH           = 24   # Min Startup Current (0-1000)
ADDR_GOAL_STS        = 42   # Goal Position
ADDR_PRESENT_POS     = 56   # Present Position (read back)
ADDR_LOCK            = 55   # EEPROM Lock (0=unlock, 1=lock)

# ─── Motor IDs ────────────────────────────────────────────────────────────────
SHOULDER_ID = 2
ELBOW_ID    = 3

# ─── Joint Names (matching 3DOF URDF) ─────────────────────────────────────────
SHOULDER_JOINT = 'SHOULDER_JNT'
ELBOW_JOINT    = 'ELBOW_JNT'


class STSServoNode3DOF(Node):
    def __init__(self):
        super().__init__('sts_servo_node_3dof')

        # ── Hardware Init ──────────────────────────────────────────────────────
        self.port_handler   = PortHandler('/dev/ttyACM0')
        self.packet_handler = PacketHandler(1.0)

        if not self.port_handler.openPort():
            self.get_logger().error("Failed to open port /dev/ttyACM0. Run: sudo chmod 666 /dev/ttyACM0")
            return

        if not self.port_handler.setBaudRate(1000000):
            self.get_logger().error("Failed to set baud rate.")
            return

        self.get_logger().info("Port opened successfully.")

        # ── Ping both motors on startup ────────────────────────────────────────
        for motor_id, name in [(SHOULDER_ID, 'Shoulder'), (ELBOW_ID, 'Elbow')]:
            _, result, _ = self.packet_handler.ping(self.port_handler, motor_id)
            if result == COMM_SUCCESS:
                self.get_logger().info(f"✅ {name} motor (ID {motor_id}) found.")
            else:
                self.get_logger().error(f"❌ {name} motor (ID {motor_id}) not found. Check wiring.")

        # ── Declare Parameters for Live Tuning ────────────────────────────────
        self.declare_parameter('servo_p_gain', 12)
        self.declare_parameter('max_torque',  300)
        self.declare_parameter('punch',         0)

        # ── Push initial parameters to both motors ─────────────────────────────
        self.update_hardware()

        # ── ROS Infrastructure ─────────────────────────────────────────────────
        # Publisher — sends real motor positions back to ROS
        self.joint_state_pub = self.create_publisher(JointState, 'joint_states', 10)

        # Subscriber — receives target positions from GUI / controller
        self.create_subscription(JointState, 'joint_commands', self.joint_command_callback, 10)

        # Timer — reads actual motor positions and publishes at 20Hz
        self.create_timer(0.05, self.publish_joint_states)

        # Parameter callback for live tuning
        self.add_on_set_parameters_callback(self.parameter_callback)

        self.get_logger().info(
            "3DOF Motor Node Ready.\n"
            f"  Shoulder → ID {SHOULDER_ID} ({SHOULDER_JOINT})\n"
            f"  Elbow    → ID {ELBOW_ID} ({ELBOW_JOINT})\n"
            "  Listening on: /joint_commands\n"
            "  Publishing to: /joint_states"
        )

    # ── Hardware Parameter Sync ────────────────────────────────────────────────
    def update_hardware(self):
        """Push current ROS parameters to both motors."""
        p_gain   = self.get_parameter('servo_p_gain').value
        m_torque = self.get_parameter('max_torque').value
        punch    = self.get_parameter('punch').value

        for motor_id in [SHOULDER_ID, ELBOW_ID]:
            self.packet_handler.write1ByteTxRx(self.port_handler, motor_id, ADDR_P_GAIN,     p_gain)
            self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, ADDR_MAX_TORQUE, m_torque)
            self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, ADDR_PUNCH,      punch)

    def parameter_callback(self, params):
        """Live tuning — update hardware registers without restarting the node."""
        for param in params:
            for motor_id in [SHOULDER_ID, ELBOW_ID]:
                if param.name == 'servo_p_gain':
                    self.packet_handler.write1ByteTxRx(self.port_handler, motor_id, ADDR_P_GAIN, param.value)
                elif param.name == 'max_torque':
                    self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, ADDR_MAX_TORQUE, param.value)
                elif param.name == 'punch':
                    self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, ADDR_PUNCH, param.value)

        self.get_logger().info("Hardware registers updated.")
        return SetParametersResult(successful=True)

    # ── Conversion Helpers ─────────────────────────────────────────────────────
    def rad_to_steps(self, rad):
        """Convert radians to STS3215 position steps.
        0 rad = center = 2048 steps (motor pointing straight).
        """
        deg = math.degrees(rad)
        steps = int(2048 + (deg * (4096 / 360)))
        return max(0, min(4095, steps))

    def steps_to_rad(self, steps):
        """Convert STS3215 position steps back to radians."""
        deg = (steps - 2048) * (360 / 4096)
        return math.radians(deg)

    # ── Command Callback ───────────────────────────────────────────────────────
    def joint_command_callback(self, msg):
        """Receive target joint positions and send to motors."""
        for joint_name, motor_id in [(SHOULDER_JOINT, SHOULDER_ID), (ELBOW_JOINT, ELBOW_ID)]:
            if joint_name in msg.name:
                idx = msg.name.index(joint_name)
                steps = self.rad_to_steps(msg.position[idx])
                self.packet_handler.write2ByteTxRx(
                    self.port_handler, motor_id, ADDR_GOAL_STS, steps)

    # ── Feedback Publisher ─────────────────────────────────────────────────────
    def publish_joint_states(self):
        """Read actual motor positions and publish to /joint_states at 20Hz."""
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name     = [SHOULDER_JOINT, ELBOW_JOINT]
        msg.position = []

        for motor_id in [SHOULDER_ID, ELBOW_ID]:
            pos_raw, result, _ = self.packet_handler.read2ByteTxRx(
                self.port_handler, motor_id, ADDR_PRESENT_POS)
            if result == COMM_SUCCESS:
                msg.position.append(self.steps_to_rad(pos_raw))
            else:
                msg.position.append(0.0)
                self.get_logger().warn(f"Failed to read position from motor ID {motor_id}")

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
