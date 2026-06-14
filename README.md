# ROSbot 2.0 ROS 2 Jazzy Image

[![Ubuntu 24.04](https://img.shields.io/badge/Ubuntu-24.04-E95420?logo=ubuntu&logoColor=white)](https://ubuntu.com/)
[![ROS 2 Jazzy](https://img.shields.io/badge/ROS%202-Jazzy-22314E?logo=ros&logoColor=white)](https://docs.ros.org/en/jazzy/)
[![Armbian](https://img.shields.io/badge/Armbian-Tinker%20Board-DD4814)](https://www.armbian.com/)
[![Hardware](https://img.shields.io/badge/hardware-ROSbot%202.0-blue)](#supported-hardware)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-community%20image-yellow)](#project-status)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20693851.svg)](https://doi.org/10.5281/zenodo.20693851)

<p align="center">
  <img src="https://husarion.com/assets/images/ROSbot_unboxing-d393720a14a85f2fd47dfa389230b821.jpg" alt="ROSbot 2.0 with lidar and RGB-D camera" width="720">
  <br>
  <sub>ROSbot 2.0 image from the Husarion ROSbot 2 quick-start guide.</sub>
</p>

Community Ubuntu 24.04 / Armbian image for running **ROS 2 Jazzy** on the original **Husarion ROSbot 2.0** with an **ASUS Tinker Board**.

The image is intended to make an old ROSbot 2.0 usable with ROS 2 without rebuilding the full stack on the robot. It includes the compiled ROS 2 runtime, ROSbot overlay, RPLIDAR support, Orbbec Astra support, SLAM Toolbox, Nav2, compressed image transports, and the ROSbot base bridge.

> [!WARNING]
> This is an unofficial community image. It is not produced, tested, endorsed, or supported by Husarion.

> [!CAUTION]
> Use this image and the scripts in this repository entirely at your own risk. By flashing the image or running the software, you accept full responsibility for any consequences, including robot movement, hardware damage, data loss, battery issues, thermal issues, network exposure, or any other damage to your robot, computer, environment, or people nearby.

## Project Status

This project is built for practical use on one tested ROSbot 2.0 configuration. It is not a general ROSbot distribution.

What currently works:

- Base driver stack on ROS 2 Jazzy
- RPLIDAR `/scan`
- Orbbec Astra RGB/depth topics
- RGB and depth compressed image topics
- Wheel odometry, IMU, battery, and TF
- SLAM Toolbox live mapping
- Nav2 with live SLAM or saved-map localization
- Namespaced multi-robot launch support
- Keyboard teleop compatibility for normal `/cmd_vel` tools
- Thermal guard and low-battery safety monitor
- CLI helper for start, stop, status, monitor, maps, goals, and teleop

## Supported Hardware

| Component | Supported target |
| --- | --- |
| Robot | ROSbot 2.0 |
| SBC | ASUS Tinker Board |
| OS base | Armbian / Ubuntu 24.04 Noble |
| ROS | ROS 2 Jazzy |
| Lidar | RPLIDAR on `/dev/rplidar` |
| Camera | Orbbec Astra / OpenNI2 |

> [!IMPORTANT]
> This image is only intended for ROSbot 2.0 with ASUS Tinker Board. Do not assume it is safe for ROSbot XL, ROSbot 3, Raspberry Pi variants, or custom hardware without reviewing and testing the launch files, firmware interface, serial devices, and power setup.

## Download

The public SD-card image is hosted on Zenodo.

<p>
  <a href="https://zenodo.org/records/20693851/files/rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img.gz?download=1"><strong>Download the ROSbot 2.0 Jazzy image (.img.gz)</strong></a>
  |
  <a href="https://zenodo.org/records/20693851">View the Zenodo record</a>
  |
  <a href="https://doi.org/10.5281/zenodo.20693851">DOI</a>
</p>

```text
Image:             rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img.gz
Minimum SD card:   32 GB
Compressed size:   15148403212 bytes (15.15 GB / 14.11 GiB)
Raw image size:    25848446976 bytes (25.85 GB / 24.07 GiB)
Compressed SHA256: 99b65763f5f729f476b746b5a2f94662fe1af6623ec657544f8e4d55e5c4cd3b
Raw image SHA256:  16fcee65a6e91df261674c061dfc05ef1c81955bbf3298b2d3e5e6e9d3448303
```

Download `SHA256SUMS` from the same Zenodo record and verify the image before flashing.

Ubuntu/Linux:

```bash
cd ~/Downloads
sha256sum -c SHA256SUMS --ignore-missing
gzip -t rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img.gz
```

macOS:

```bash
cd ~/Downloads
shasum -a 256 rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img.gz
gzip -t rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img.gz
```

Windows PowerShell:

```powershell
Get-FileHash .\rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img.gz -Algorithm SHA256
```

## Flash

> [!WARNING]
> Flashing overwrites the selected SD card. Double-check the target drive before starting.

Use a 32 GB or larger microSD card.

### balenaEtcher

[balenaEtcher](https://www.balena.io/etcher) is the simplest cross-platform option for Windows, Ubuntu/Linux, and macOS.

1. Open balenaEtcher.
2. Choose **Flash from file**.
3. Select `rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img.gz`.
4. Choose the target microSD card.
5. Select **Flash** and wait for validation to finish.
6. Eject the SD card safely.

balenaEtcher can flash the compressed `.img.gz` file directly.

### Rufus

[Rufus](https://rufus.ie/) is a good Windows option.

1. Insert the microSD card into the Windows PC.
2. Open Rufus.
3. In **Device**, select the microSD card.
4. In **Boot selection**, choose `rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img.gz`.
5. Select **Start**.
6. If Rufus asks for the write mode, choose **DD Image mode**.
7. Wait for Rufus to finish, then eject the SD card safely.

Rufus supports compressed bootable disk images. If your Rufus version refuses the `.img.gz`, decompress it first and select the resulting `.img` file.

### Ubuntu/Linux Command Line

Use this only if you are comfortable identifying raw block devices.

```bash
lsblk
```

Find the SD card device, for example `/dev/sdX`. Use the whole device, not a partition such as `/dev/sdX1`.

```bash
cd ~/Downloads
gunzip -c rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img.gz | sudo dd of=/dev/sdX bs=16M status=progress conv=fsync
sync
```

Replace `/dev/sdX` with the real SD card device.

### macOS Command Line

Use this only if you are comfortable identifying raw disks.

```bash
diskutil list
```

Find the SD card disk, for example `/dev/diskN`, then unmount it:

```bash
diskutil unmountDisk /dev/diskN
cd ~/Downloads
gunzip -c rosbot2-jazzy-tinkerboard-ubuntu24.04-20260614.img.gz | sudo dd of=/dev/rdiskN bs=16m
sync
diskutil eject /dev/diskN
```

Replace `diskN` and `rdiskN` with the real SD card disk number.

## First Boot

1. Power off the robot.
2. Insert the flashed microSD card.
3. Connect an Ethernet cable to the robot for the first boot.
4. Boot the robot.
5. Find the robot IP from your router, DHCP leases page, or a network scanner.
6. SSH into the robot:

```bash
ssh husarion@ROBOT_IP
```

Default login:

```text
user:     husarion
password: husarion
```

> [!TIP]
> Change the default password before putting the robot on an untrusted network.

## Install The Control CLI

The SD image contains the compiled ROS runtime. This repository contains the public CLI and documentation.

On the robot:

```bash
cd ~
git clone https://github.com/RICE-unige/rosbot2-jazzy-image.git
cd rosbot2-jazzy-image
cp rosbot.env.example rosbot.env
nano rosbot.env
```

The CLI reads configuration from:

```text
./rosbot.env
```

You can override the config path with:

```bash
ROSBOT_ENV_FILE=/path/to/rosbot.env ./rosbot status
```

## Repository Layout

```text
.
|-- rosbot                  # public CLI entrypoint
|-- rosbot.env.example      # local configuration template
|-- scripts/                # implementation helpers used by ./rosbot
|-- README.md
|-- RELEASE_NOTES.md
|-- THIRD_PARTY_LICENSE_NOTES.txt
|-- SHA256SUMS
`-- LICENSE
```

Keep `rosbot` at the repository root so users can run `./rosbot ...` directly after cloning.

## Quick Start

Start the base driver stack:

```bash
./rosbot start
```

Show status:

```bash
./rosbot status
```

Open the live dashboard:

```bash
./rosbot monitor
```

Run keyboard teleop:

```bash
./rosbot teleop
```

Stop all robot processes:

```bash
./rosbot stop
```

> [!CAUTION]
> Treat every command that starts drivers, teleop, SLAM, Nav2, or goals as capable of moving the robot. Test with the robot lifted or in a clear area first.

## CLI Commands

| Command | Purpose |
| --- | --- |
| `./rosbot start` | Start the base stack with defaults from `rosbot.env` |
| `./rosbot base` | Alias for the base stack |
| `./rosbot slam` | Start live SLAM |
| `./rosbot nav` | Start live SLAM plus Nav2 |
| `./rosbot map MAP.yaml` | Start saved-map localization plus Nav2 |
| `./rosbot restart MODE` | Stop the current stack and start another mode |
| `./rosbot stop` | Stop ROSbot stack, teleop bridge, monitor, and lidar motor |
| `./rosbot status` | Show runtime, network, thermal, battery, and process status |
| `./rosbot monitor` | Live in-place terminal dashboard |
| `./rosbot teleop` | Run keyboard teleop with normal Twist commands |
| `./rosbot logs` | Follow the latest launch log |
| `./rosbot save-map ~/maps/name` | Save the current SLAM map |
| `./rosbot pose X Y YAW` | Publish initial pose for saved-map navigation |
| `./rosbot goal X Y YAW --yes` | Send one supervised Nav2 goal |

Launch commands run in the background by default. Logs are stored in:

```text
~/.rosbot/logs
```

Use `--verbose` to stream ROS launch output in the terminal.

## Common Examples

```bash
./rosbot start --camera
./rosbot restart nav --camera
./rosbot restart map ~/maps/lab.yaml
./rosbot save-map ~/maps/lab
./rosbot goal 1.0 0.0 0.0 --yes
./rosbot monitor --interval 1
./rosbot logs
```

Only one robot stack should run at a time. If a stack is already running, the CLI will ask you to use `./rosbot restart MODE` or `./rosbot stop`.

## Configuration

Copy `rosbot.env.example` to `rosbot.env` and edit it for your robot.

```bash
cp rosbot.env.example rosbot.env
nano rosbot.env
```

Important defaults:

```bash
ROSBOT_NAMESPACE=
ROSBOT_START_CAMERA=false
ROSBOT_START_LIDAR=true
ROSBOT_START_JOY=false
ROS_DOMAIN_ID=0
RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ROSBOT_LIDAR_PORT=/dev/rplidar
```

For multi-robot use:

```bash
ROSBOT_NAMESPACE=robot1
```

or per command:

```bash
./rosbot nav --namespace robot1
```

## Battery And Safety

Battery safety is enabled by default:

```bash
ROSBOT_BATTERY_SAFETY=true
ROSBOT_BATTERY_WARN_PERCENT=20
ROSBOT_BATTERY_STOP_PERCENT=10
ROSBOT_BATTERY_STOP_DELAY=60
ROSBOT_BATTERY_STOP_TIMEOUT=20
ROSBOT_BATTERY_TREND_WINDOW=120
ROSBOT_BATTERY_TREND_MIN_DV=0.03
```

If the battery stays at or below `ROSBOT_BATTERY_STOP_PERCENT` for `ROSBOT_BATTERY_STOP_DELAY` seconds, the helper publishes zero velocity and stops the robot stack.

Disable battery safety for one run:

```bash
./rosbot nav --no-battery-safety
```

> [!NOTE]
> ROSbot 2.0 firmware reports direct charging state as `unknown`. The CLI keeps that direct value visible and adds an inferred voltage trend such as `probably charging`, `probably discharging`, or `stable` after enough samples.

## Teleop Compatibility

The controller consumes `TwistStamped` velocity commands internally on `/cmd_vel_stamped`. The CLI starts a compatibility bridge so standard tools like `teleop_twist_keyboard`, which publish `Twist` on `/cmd_vel`, still work.

```bash
./rosbot teleop
```

## Lidar Motor Stop

`./rosbot stop` also stops the RPLIDAR A1 motor. When the stack is stopped, `./rosbot status` may show:

```text
Lidar motor   held stopped
```

That means a small helper is holding `/dev/rplidar` in the line state needed to keep the physical lidar motor off after the ROS driver exits.

## Wi-Fi

Use Armbian's configuration tool:

```bash
sudo armbian-config
```

Then use the network menu to connect to Wi-Fi. Reconnect over SSH after the robot receives an IP address.

## Known Limitations

- Camera calibration is not included.
- Direct battery charging/discharging state is not exposed by ROSbot 2.0 firmware.
- The Tinker Board is CPU constrained; active cooling is strongly recommended.
- Large Nav2 workloads can overrun the CPU.
- Start with small supervised motion and navigation tests.
- The image is built for ROSbot 2.0 on ASUS Tinker Board only.

## License

This repository is released under the [MIT License](LICENSE).

The SD image and runtime include third-party software with their own licenses. Review upstream licenses before redistributing modified images.
