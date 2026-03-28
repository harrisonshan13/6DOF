import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    urdf_path = os.path.join(
        get_package_share_directory('URDF_TEST'),
        'urdf',
        'URDF_TEST.urdf'
    )

    with open(urdf_path, 'r') as f:
        robot_description = f.read()

    return LaunchDescription([

        # 1. Robot State Publisher — broadcasts transforms from URDF
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{'robot_description': robot_description}]
        ),

        # 2. Joint State Publisher GUI (sliders)
        #    Remapped: publishes to /joint_commands instead of /joint_states
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            remappings=[('joint_states', 'joint_commands')]
        ),

        # 3. Motor Node — listens on /joint_commands, publishes to /joint_states
        Node(
            package='servo_control',
            executable='motor_node',
            name='sts_servo_node',
        ),

        # 4. RViz
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
        ),

    ])