#!/usr/bin/env python3
"""Stop and hold an RPLIDAR motor off through its serial adapter."""

import argparse
import array
import fcntl
import os
import signal
import sys
import termios
import time


RPLIDAR_SYNC = 0xA5
RPLIDAR_CMD_STOP = 0x25
RPLIDAR_CMD_SCAN = 0x20
RPLIDAR_CMD_SET_MOTOR_PWM = 0xF0
RPLIDAR_CMD_HQ_MOTOR_SPEED_CTRL = 0xA8


running = True


def handle_signal(signum, frame):
    del signum, frame
    global running
    running = False


def set_dtr(fd, enabled):
    request = termios.TIOCMBIS if enabled else termios.TIOCMBIC
    value = array.array("i", [termios.TIOCM_DTR])
    fcntl.ioctl(fd, request, value, True)


def set_rts(fd, enabled):
    request = termios.TIOCMBIS if enabled else termios.TIOCMBIC
    value = array.array("i", [termios.TIOCM_RTS])
    fcntl.ioctl(fd, request, value, True)


def configure_serial(fd, baud):
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0
    attrs[1] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0
    speed = getattr(termios, f"B{baud}", termios.B115200)
    attrs[4] = speed
    attrs[5] = speed
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 1
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)


def command_packet(command, payload=b""):
    packet_command = command
    packet = bytearray([RPLIDAR_SYNC, packet_command])
    if payload:
        checksum = RPLIDAR_SYNC ^ packet_command ^ len(payload)
        for value in payload:
            checksum ^= value
        packet.append(len(payload))
        packet.extend(payload)
        packet.append(checksum)
    return bytes(packet)


def write_command(fd, command, payload=b""):
    os.write(fd, command_packet(command, payload))
    termios.tcdrain(fd)


def force_motor_stop(fd):
    pwm_zero = b"\x00\x00"
    # Different CP210x adapter boards wire motor enable differently. Cycle all
    # DTR/RTS states while sending both scan-stop and PWM-zero commands, then
    # leave both lines asserted. This matched the ROSbot 2.0 RPLIDAR adapter in
    # testing and is harmless for adapters that only use one line.
    for _ in range(2):
        for dtr in (False, True):
            for rts in (False, True):
                set_dtr(fd, dtr)
                set_rts(fd, rts)
                write_command(fd, RPLIDAR_CMD_STOP)
                time.sleep(0.05)
                write_command(fd, RPLIDAR_CMD_SET_MOTOR_PWM, pwm_zero)
                time.sleep(0.05)
                write_command(fd, RPLIDAR_CMD_HQ_MOTOR_SPEED_CTRL, pwm_zero)
                time.sleep(0.15)
    set_dtr(fd, True)
    set_rts(fd, True)
    termios.tcflush(fd, termios.TCIFLUSH)


def hold_motor_stop(fd):
    pwm_zero = b"\x00\x00"
    set_dtr(fd, True)
    set_rts(fd, True)
    write_command(fd, RPLIDAR_CMD_STOP)
    time.sleep(0.05)
    write_command(fd, RPLIDAR_CMD_SET_MOTOR_PWM, pwm_zero)
    time.sleep(0.05)
    write_command(fd, RPLIDAR_CMD_HQ_MOTOR_SPEED_CTRL, pwm_zero)
    termios.tcflush(fd, termios.TCIFLUSH)


def read_available(fd, duration):
    deadline = time.monotonic() + duration
    data = bytearray()
    while time.monotonic() < deadline:
        try:
            chunk = os.read(fd, 4096)
        except BlockingIOError:
            chunk = b""
        if chunk:
            data.extend(chunk)
        time.sleep(0.02)
    return bytes(data)


def verify_motor_stopped(fd):
    termios.tcflush(fd, termios.TCIOFLUSH)
    write_command(fd, RPLIDAR_CMD_SCAN)
    time.sleep(0.15)
    data = read_available(fd, 1.2)
    force_motor_stop(fd)

    # A stopped motor may still return a small response descriptor. A spinning
    # lidar streams measurement packets continuously and quickly exceeds this.
    return len(data) < 64, len(data)


def main():
    parser = argparse.ArgumentParser(
        description="Stop an RPLIDAR motor and keep the serial adapter in the stopped state."
    )
    parser.add_argument("--port", default="/dev/rplidar", help="Serial device for the RPLIDAR")
    parser.add_argument("--baud", type=int, default=115200, help="RPLIDAR serial baud rate")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between DTR refreshes")
    parser.add_argument("--verify", action="store_true", help="Fail if scan data still streams after motor stop")
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    fd = os.open(args.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        configure_serial(fd, args.baud)
        force_motor_stop(fd)
        if args.verify:
            stopped, byte_count = verify_motor_stopped(fd)
            if not stopped:
                print(
                    f"rosbot_lidar_motor_hold: motor still appears active ({byte_count} scan bytes)",
                    file=sys.stderr,
                )
                return 2
            print(f"rosbot_lidar_motor_hold: motor stop verified ({byte_count} scan bytes)")
        while running:
            hold_motor_stop(fd)
            time.sleep(max(args.interval, 0.1))
    finally:
        try:
            set_dtr(fd, False)
            set_rts(fd, False)
        except OSError:
            pass
        os.close(fd)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"rosbot_lidar_motor_hold: {exc}", file=sys.stderr)
        raise SystemExit(1)
