cmake_minimum_required(VERSION 3.8)
project(URDF_TEST)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

# This installs your folders so ROS can find them at runtime
install(DIRECTORY
  meshes
  urdf
  launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()