import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    package_name = '3DOF'
    pkg_share = get_package_share_directory(package_name)

    urdf_file = os.path.join(pkg_share, 'urdf', '3DOF.urdf')
    rviz_config_file = os.path.join(pkg_share, 'rviz', 'urdf.rviz')

    return LaunchDescription([
        # Robot State Publisher (publishes TF tree from URDF)
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': open(urdf_file).read()}]
        ),
        # Joint State Publisher GUI (sliders for manual joint control)
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui'
        ),
        # RViz2
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_file]
        )
    ])
