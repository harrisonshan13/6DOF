import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'URDF_TEST'
    pkg_share = get_package_share_directory(package_name)
    
    # Paths for URDF and RViz config
    urdf_file = os.path.join(pkg_share, 'urdf', 'URDF_TEST.urdf')
    rviz_config_file = os.path.join(pkg_share, 'rviz', 'urdf.rviz')

    return LaunchDescription([
        # Robot State Publisher (Publishes the TF tree)
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': open(urdf_file).read()}]
        ),
        # Joint State Publisher GUI (The Sliders)
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
            arguments=['-d', rviz_config_file] # Added comma before this and used the variable
        ) # Removed the extra closing parenthesis that was here
    ])