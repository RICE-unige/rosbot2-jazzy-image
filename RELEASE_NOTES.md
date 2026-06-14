# Release Notes

## v2026.06.14 - Initial ROS 2 Jazzy Image

Release date: 2026-06-14

Zenodo record: https://zenodo.org/records/20693851

DOI: https://doi.org/10.5281/zenodo.20693851

Image files:

```text
Compressed image: rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img.gz
Compressed size:  15148403212 bytes (15.15 GB / 14.11 GiB)
Compressed SHA256:
  99b65763f5f729f476b746b5a2f94662fe1af6623ec657544f8e4d55e5c4cd3b

Raw image after decompression: rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img
Raw image size:                25848446976 bytes (25.85 GB / 24.07 GiB)
Raw image SHA256:
  16fcee65a6e91df261674c061dfc05ef1c81955bbf3298b2d3e5e6e9d3448303
```

Included:

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

Verification performed before publication:

- Raw image MBR signature verified: `55aa`
- Linux partition type verified: `0x83`
- Partition end verified to match image end
- gzip integrity test passed
- SHA256 checks passed
- Image was flashed to a 32 GB SD card and spot-verified at the first and last 64 MiB

Known limitations:

- Camera calibration file is not included.
- Large Nav2 workloads are limited by Tinker Board CPU headroom.
- Use small supervised motion tests before larger autonomous navigation.

License and third-party software:

- Repository scripts and documentation are released under the repository license.
- The SD-card image includes upstream operating-system packages, ROS packages, drivers, firmware, and third-party software under their respective licenses.
