#!/usr/bin/env python3
"""Cache ROSbot battery status and optionally stop the robot on low battery."""

import argparse
import math
import os
import shlex
import subprocess
import sys
import tempfile
import time

import rclpy
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import Twist, TwistStamped
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Float32MultiArray


STATUS = {
    BatteryState.POWER_SUPPLY_STATUS_UNKNOWN: "unknown",
    BatteryState.POWER_SUPPLY_STATUS_CHARGING: "charging",
    BatteryState.POWER_SUPPLY_STATUS_DISCHARGING: "discharging",
    BatteryState.POWER_SUPPLY_STATUS_NOT_CHARGING: "not_charging",
    BatteryState.POWER_SUPPLY_STATUS_FULL: "full",
}

HEALTH = {
    BatteryState.POWER_SUPPLY_HEALTH_UNKNOWN: "unknown",
    BatteryState.POWER_SUPPLY_HEALTH_GOOD: "good",
    BatteryState.POWER_SUPPLY_HEALTH_OVERHEAT: "overheat",
    BatteryState.POWER_SUPPLY_HEALTH_DEAD: "dead",
    BatteryState.POWER_SUPPLY_HEALTH_OVERVOLTAGE: "overvoltage",
    BatteryState.POWER_SUPPLY_HEALTH_UNSPEC_FAILURE: "failure",
    BatteryState.POWER_SUPPLY_HEALTH_COLD: "cold",
    BatteryState.POWER_SUPPLY_HEALTH_WATCHDOG_TIMER_EXPIRE: "watchdog_expired",
    BatteryState.POWER_SUPPLY_HEALTH_SAFETY_TIMER_EXPIRE: "safety_timer_expired",
}

TECH = {
    BatteryState.POWER_SUPPLY_TECHNOLOGY_UNKNOWN: "unknown",
    BatteryState.POWER_SUPPLY_TECHNOLOGY_NIMH: "nimh",
    BatteryState.POWER_SUPPLY_TECHNOLOGY_LION: "li_ion",
    BatteryState.POWER_SUPPLY_TECHNOLOGY_LIPO: "li_po",
    BatteryState.POWER_SUPPLY_TECHNOLOGY_LIFE: "li_fe",
    BatteryState.POWER_SUPPLY_TECHNOLOGY_NICD: "nicd",
    BatteryState.POWER_SUPPLY_TECHNOLOGY_LIMN: "li_mn",
}


def topic_for(namespace, topic):
    if topic.startswith("/"):
        return topic
    namespace = namespace.strip("/")
    if namespace:
        return f"/{namespace}/{topic}"
    return f"/{topic}"


def topic_set(namespace, topic):
    namespace = namespace.strip("/")
    topics = {f"/{topic.strip('/')}"}
    if namespace:
        topics.add(f"/{namespace}/{topic.strip('/')}")
    return sorted(topics)


def finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def fmt_float(value, digits=3):
    if not finite(value):
        return ""
    return f"{float(value):.{digits}f}"


def percent_from_msg(msg):
    if not finite(msg.percentage):
        return None
    percentage = float(msg.percentage)
    if percentage <= 1.0:
        percentage *= 100.0
    return max(0.0, min(100.0, percentage))


def status_to_dict(msg, topic, alert="ok", safety="off", timer_remaining=""):
    percent = percent_from_msg(msg)
    status = STATUS.get(msg.power_supply_status, f"code_{msg.power_supply_status}")
    if status in ("charging", "full"):
        external_power = "yes"
    elif status == "discharging":
        external_power = "no"
    else:
        external_power = "unknown"

    return {
        "available": "true",
        "timestamp": str(int(time.time())),
        "topic": topic,
        "percentage": "" if percent is None else f"{percent:.1f}",
        "voltage": fmt_float(msg.voltage, 2),
        "current": fmt_float(msg.current, 2),
        "status": status,
        "external_power": external_power,
        "health": HEALTH.get(msg.power_supply_health, f"code_{msg.power_supply_health}"),
        "technology": TECH.get(msg.power_supply_technology, f"code_{msg.power_supply_technology}"),
        "present": "true" if msg.present else "false",
        "cell_voltage": ",".join(fmt_float(value, 2) for value in msg.cell_voltage if finite(value)),
        "location": msg.location or "",
        "serial_number": msg.serial_number or "",
        "alert": alert,
        "safety": safety,
        "timer_remaining": str(timer_remaining),
    }


def history_sample(msg):
    if not finite(msg.voltage):
        return None
    percent = percent_from_msg(msg)
    return {
        "timestamp": int(time.time()),
        "voltage": float(msg.voltage),
        "percentage": percent,
        "status": STATUS.get(msg.power_supply_status, f"code_{msg.power_supply_status}"),
    }


def read_history(path, max_age):
    if not path or not os.path.exists(path):
        return []
    now = time.time()
    samples = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            try:
                timestamp = float(parts[0])
                voltage = float(parts[1])
                percentage = None if parts[2] == "" else float(parts[2])
            except ValueError:
                continue
            if now - timestamp <= max_age:
                samples.append(
                    {
                        "timestamp": timestamp,
                        "voltage": voltage,
                        "percentage": percentage,
                        "status": parts[3],
                    }
                )
    return samples


def write_history(path, samples):
    if not path:
        return
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".battery-history-", dir=directory, text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        for sample in samples:
            percentage = sample["percentage"]
            percent_text = "" if percentage is None else f"{percentage:.3f}"
            handle.write(
                f"{int(sample['timestamp'])}\t{sample['voltage']:.6f}\t"
                f"{percent_text}\t{sample['status']}\n"
            )
    os.replace(tmp, path)


def append_history(path, msg, keep_age):
    sample = history_sample(msg)
    if sample is None or not path:
        return []
    samples = read_history(path, keep_age)
    samples.append(sample)
    write_history(path, samples)
    return samples


def infer_power_trend(msg, topic, history_path, window, min_dv):
    status = STATUS.get(msg.power_supply_status, f"code_{msg.power_supply_status}")
    direct = {
        "charging": "charging",
        "full": "full",
        "discharging": "discharging",
        "not_charging": "not_charging",
    }.get(status)
    if direct:
        return {
            "power_trend": direct,
            "power_trend_source": "firmware",
            "power_trend_window": "0",
            "power_trend_delta_voltage": "",
            "power_trend_delta_percentage": "",
            "power_trend_note": "direct",
        }

    samples = read_history(history_path, max(window * 2.0, 60.0))
    current = history_sample(msg)
    if current is not None:
        samples.append(current)
    now = time.time()
    samples = [sample for sample in samples if now - sample["timestamp"] <= window]
    if len(samples) < 2:
        return {
            "power_trend": "unknown",
            "power_trend_source": "unavailable",
            "power_trend_window": str(int(window)),
            "power_trend_delta_voltage": "",
            "power_trend_delta_percentage": "",
            "power_trend_note": "need_more_samples",
        }

    samples.sort(key=lambda item: item["timestamp"])
    first = samples[0]
    last = samples[-1]
    span = last["timestamp"] - first["timestamp"]
    minimum_span = min(max(window / 3.0, 30.0), window)
    if span < minimum_span:
        return {
            "power_trend": "unknown",
            "power_trend_source": "voltage_trend",
            "power_trend_window": str(int(span)),
            "power_trend_delta_voltage": "",
            "power_trend_delta_percentage": "",
            "power_trend_note": "warming_up",
        }

    group_size = max(1, min(5, len(samples) // 4 or 1))
    first_group = samples[:group_size]
    last_group = samples[-group_size:]
    first_voltage = sum(sample["voltage"] for sample in first_group) / len(first_group)
    last_voltage = sum(sample["voltage"] for sample in last_group) / len(last_group)
    delta_voltage = last_voltage - first_voltage

    first_percent_values = [sample["percentage"] for sample in first_group if sample["percentage"] is not None]
    last_percent_values = [sample["percentage"] for sample in last_group if sample["percentage"] is not None]
    first_percent = (
        sum(first_percent_values) / len(first_percent_values) if first_percent_values else None
    )
    last_percent = (
        sum(last_percent_values) / len(last_percent_values) if last_percent_values else None
    )
    delta_percent = None
    if first_percent is not None and last_percent is not None:
        delta_percent = last_percent - first_percent

    trend = "stable"
    discharge_min_dv = max(min_dv * 2.0, 0.08)
    if delta_voltage >= min_dv and (delta_percent is None or delta_percent >= -1.0):
        trend = "probably_charging"
    elif delta_percent is not None and delta_percent >= 1.0 and delta_voltage >= -min_dv:
        trend = "probably_charging"
    elif delta_voltage <= -discharge_min_dv and (delta_percent is None or delta_percent <= 1.0):
        trend = "probably_discharging"
    elif delta_percent is not None and delta_percent <= -2.0 and delta_voltage <= -min_dv:
        trend = "probably_discharging"

    return {
        "power_trend": trend,
        "power_trend_source": "voltage_trend",
        "power_trend_window": str(int(round(span))),
        "power_trend_delta_voltage": f"{delta_voltage:.3f}",
        "power_trend_delta_percentage": "" if delta_percent is None else f"{delta_percent:.1f}",
        "power_trend_note": f"{topic}: firmware_status_unknown",
    }


def add_power_trend(data, msg, topic, history_path, window, min_dv):
    data.update(infer_power_trend(msg, topic, history_path, window, min_dv))
    return data


def write_cache(path, data):
    if not path:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".battery-", dir=os.path.dirname(path), text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        for key, value in data.items():
            handle.write(f"{key}={shlex.quote(str(value))}\n")
    os.replace(tmp, path)


def print_cache(data):
    for key, value in data.items():
        print(f"{key}={value}")


def is_stop_blocked_by_power(msg):
    return msg.power_supply_status in (
        BatteryState.POWER_SUPPLY_STATUS_CHARGING,
        BatteryState.POWER_SUPPLY_STATUS_FULL,
    )


def publish_zero_commands(node, namespace, duration=1.0):
    twist_publishers = [node.create_publisher(Twist, topic, 10) for topic in topic_set(namespace, "cmd_vel")]
    stamped_publishers = [
        node.create_publisher(TwistStamped, topic, 10) for topic in topic_set(namespace, "cmd_vel_stamped")
    ]
    motor_publishers = [
        node.create_publisher(Float32MultiArray, topic, 10) for topic in topic_set(namespace, "_motors/cmd")
    ]

    twist = Twist()
    stamped = TwistStamped()
    stamped.header.frame_id = "base_link" if not namespace else f"{namespace}/base_link"
    motors = Float32MultiArray()
    motors.data = [0.0, 0.0, 0.0, 0.0]

    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        stamped.header.stamp = node.get_clock().now().to_msg()
        for publisher in twist_publishers:
            publisher.publish(twist)
        for publisher in stamped_publishers:
            publisher.publish(stamped)
        for publisher in motor_publishers:
            publisher.publish(motors)
        rclpy.spin_once(node, timeout_sec=0.0)
        time.sleep(0.05)


def terminate_matching(pattern, signal_name):
    result = subprocess.run(["pgrep", "-f", pattern], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return
    own_pid = os.getpid()
    parent_pid = os.getppid()
    for raw_pid in result.stdout.split():
        try:
            pid = int(raw_pid)
        except ValueError:
            continue
        if pid in (own_pid, parent_pid, 1):
            continue
        subprocess.run(["kill", f"-{signal_name}", str(pid)], check=False)


def hard_stop_processes():
    patterns = [
        "[r]os2 launch rosbot_bringup",
        "[r]os2 launch nav2_bringup",
        "[r]os2 launch slam_toolbox",
        "[r]os2 launch rplidar_ros",
        "[r]obot_state_publisher",
        "[j]oy_node",
        "[t]eleop_node",
        "[r]plidar_composition",
        "[b]ridge_node",
        "[t]f_namespace_bridge",
        "[r]os2_control_node",
        "[e]kf_node",
        "[o]penni2_camera_driver",
        "[/]image_transport[/]republish",
        "[a]sync_slam_toolbox_node",
        "[s]lam_toolbox",
        "[m]ap_server",
        "[a]mcl",
        "[p]lanner_server",
        "[c]ontroller_server",
        "[s]moother_server",
        "[b]ehavior_server",
        "[b]t_navigator",
        "[w]aypoint_follower",
        "[v]elocity_smoother",
        "[c]ollision_monitor",
        "[l]ifecycle_manager",
        "[r]osbot_twist_bridge.py",
    ]
    for pattern in patterns:
        terminate_matching(pattern, "TERM")
    time.sleep(2.0)
    for pattern in patterns:
        terminate_matching(pattern, "KILL")


def lidar_holder_pids():
    result = subprocess.run(["ps", "-eo", "pid=,args="], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return []
    own_pid = os.getpid()
    parent_pid = os.getppid()
    pids = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        args = parts[1]
        if pid in (own_pid, parent_pid, 1):
            continue
        if "rosbot_lidar_motor_hold.py" in args and "rosbot_battery_monitor.py" not in args:
            pids.append(pid)
    return pids


def start_lidar_holder(command):
    if not command:
        return
    if lidar_holder_pids():
        return
    subprocess.Popen(
        shlex.split(command),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def alert_for(msg, warn_percent, stop_percent, low_since, stop_delay):
    percent = percent_from_msg(msg)
    if percent is None:
        return "unknown", ""
    if percent <= stop_percent and not is_stop_blocked_by_power(msg):
        remaining = max(0, int(round(stop_delay - (time.monotonic() - low_since)))) if low_since else int(stop_delay)
        return "critical", remaining
    if percent <= warn_percent:
        return "low", ""
    return "ok", ""


def spin_once(topic, timeout, cache, history="", trend_window=120.0, trend_min_dv=0.03):
    rclpy.init()
    node = rclpy.create_node("rosbot_battery_status_once")
    qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
    )
    result = {"msg": None}
    node.create_subscription(BatteryState, topic, lambda msg: result.__setitem__("msg", msg), qos)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and result["msg"] is None:
        rclpy.spin_once(node, timeout_sec=0.1)

    if result["msg"] is None:
        data = {
            "available": "false",
            "timestamp": str(int(time.time())),
            "topic": topic,
            "alert": "unknown",
            "safety": "unknown",
        }
    else:
        append_history(history, result["msg"], max(trend_window * 2.0, 600.0))
        data = status_to_dict(result["msg"], topic)
        add_power_trend(data, result["msg"], topic, history, trend_window, trend_min_dv)

    write_cache(cache, data)
    print_cache(data)
    node.destroy_node()
    rclpy.shutdown()
    return 0 if result["msg"] is not None else 1


def watch(args):
    rclpy.init()
    node = rclpy.create_node("rosbot_battery_monitor")
    qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
    )
    state = {"msg": None, "low_since": None, "last_log": 0.0, "last_history": 0.0}

    def callback(msg):
        now = time.monotonic()
        if now - state["last_history"] >= args.history_interval:
            append_history(args.history, msg, max(args.trend_window * 2.0, 600.0))
            state["last_history"] = now
        percent = percent_from_msg(msg)
        if (
            args.safety
            and percent is not None
            and percent <= args.stop_percent
            and not is_stop_blocked_by_power(msg)
        ):
            if state["low_since"] is None:
                state["low_since"] = time.monotonic()
        else:
            state["low_since"] = None

        alert, remaining = alert_for(
            msg, args.warn_percent, args.stop_percent, state["low_since"], args.stop_delay
        )
        data = status_to_dict(
            msg,
            args.topic,
            alert=alert,
            safety="on" if args.safety else "off",
            timer_remaining=remaining,
        )
        add_power_trend(data, msg, args.topic, args.history, args.trend_window, args.trend_min_dv)
        data["warn_percent"] = f"{args.warn_percent:.1f}"
        data["stop_percent"] = f"{args.stop_percent:.1f}"
        data["stop_delay"] = str(int(args.stop_delay))
        write_cache(args.cache, data)
        state["msg"] = msg

    node.create_subscription(BatteryState, args.topic, callback, qos)
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.2)
        msg = state["msg"]
        if msg is None:
            continue
        percent = percent_from_msg(msg)
        if state["low_since"] is None or percent is None:
            continue
        elapsed = time.monotonic() - state["low_since"]
        now = time.monotonic()
        if now - state["last_log"] >= 10.0:
            remaining = max(0, int(round(args.stop_delay - elapsed)))
            print(
                f"Battery critical: {percent:.1f}% <= {args.stop_percent:.1f}%; "
                f"stopping in {remaining}s",
                flush=True,
            )
            state["last_log"] = now
        if elapsed >= args.stop_delay:
            print(
                f"Battery critical for {int(args.stop_delay)}s: {percent:.1f}%. Running stop command.",
                flush=True,
            )
            publish_zero_commands(node, args.namespace, duration=1.0)
            try:
                completed = subprocess.run(
                    shlex.split(args.stop_command),
                    check=False,
                    timeout=args.stop_timeout,
                )
                if completed.returncode != 0:
                    print(
                        f"Stop command exited with {completed.returncode}; running hard stop fallback.",
                        flush=True,
                    )
                    hard_stop_processes()
                    start_lidar_holder(args.lidar_hold_command)
            except subprocess.TimeoutExpired:
                print("Stop command timed out; running hard stop fallback.", flush=True)
                hard_stop_processes()
                start_lidar_holder(args.lidar_hold_command)
            data = status_to_dict(msg, args.topic, alert="ok", safety="off")
            add_power_trend(data, msg, args.topic, args.history, args.trend_window, args.trend_min_dv)
            data["warn_percent"] = f"{args.warn_percent:.1f}"
            data["stop_percent"] = f"{args.stop_percent:.1f}"
            data["stop_delay"] = str(int(args.stop_delay))
            write_cache(args.cache, data)
            break

    node.destroy_node()
    rclpy.shutdown()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    once = subparsers.add_parser("once", help="Read one battery message")
    once.add_argument("--topic", required=True)
    once.add_argument("--cache", default="")
    once.add_argument("--timeout", type=float, default=2.0)
    once.add_argument("--history", default="")
    once.add_argument("--trend-window", type=float, default=120.0)
    once.add_argument("--trend-min-dv", type=float, default=0.03)

    watch_parser = subparsers.add_parser("watch", help="Cache battery status and enforce safety")
    watch_parser.add_argument("--topic", required=True)
    watch_parser.add_argument("--cache", required=True)
    watch_parser.add_argument("--warn-percent", type=float, required=True)
    watch_parser.add_argument("--stop-percent", type=float, required=True)
    watch_parser.add_argument("--stop-delay", type=float, required=True)
    watch_parser.add_argument("--safety", action="store_true")
    watch_parser.add_argument("--namespace", default="")
    watch_parser.add_argument("--stop-command", required=True)
    watch_parser.add_argument("--stop-timeout", type=float, default=20.0)
    watch_parser.add_argument("--lidar-hold-command", default="")
    watch_parser.add_argument("--history", default="")
    watch_parser.add_argument("--history-interval", type=float, default=5.0)
    watch_parser.add_argument("--trend-window", type=float, default=120.0)
    watch_parser.add_argument("--trend-min-dv", type=float, default=0.03)

    args = parser.parse_args()
    if args.command == "once":
        return spin_once(args.topic, args.timeout, args.cache, args.history, args.trend_window, args.trend_min_dv)
    return watch(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0)
    except Exception as exc:
        print(f"rosbot_battery_monitor: {exc}", file=sys.stderr)
        raise SystemExit(1)
