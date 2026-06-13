# Release Notes

## Initial ROS 2 Jazzy Image

- Ubuntu 24.04 / Armbian base image for ASUS Tinker Board
- ROS 2 Jazzy runtime and compiled overlay included
- ROSbot 2.0 MAVLink bridge support
- RPLIDAR support with Boost scan mode
- Orbbec Astra OpenNI2 camera support
- RGB and depth compressed image transports included
- SLAM Toolbox live mapping support
- Nav2 support for live SLAM and saved maps
- Multi-robot namespace support through the public CLI and launch files
- Thermal guard and CPU tuning for Tinker Board stability

Known limitations:

- Camera calibration file is not included.
- Large Nav2 workloads are limited by Tinker Board CPU headroom.
- Use small supervised motion tests before larger autonomous navigation.
