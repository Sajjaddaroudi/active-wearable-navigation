#!/usr/bin/env python3
import argparse
import asyncio
import json
import math
import time

from garmin_bridge.websockets_compat import patch_websockets_asyncio


patch_websockets_asyncio()
import websockets


def make_batch(sequence, start_ms, samples=25, sample_rate_hz=25.0):
    step_ms = round(1000.0 / sample_rate_hz)
    indexes = range(samples)
    return {
        "type": "imu_batch",
        "version": 1,
        "sequence": sequence,
        "watch_timestamp_ms": [start_ms + i * step_ms for i in indexes],
        "accel_x_mg": [40.0 * math.sin((sequence * samples + i) * 0.12) for i in indexes],
        "accel_y_mg": [15.0 * math.sin((sequence * samples + i) * 0.05) for i in indexes],
        "accel_z_mg": [1000.0 + 30.0 * math.sin((sequence * samples + i) * 0.08) for i in indexes],
        "gyro_x_deg_s": [2.0 * math.sin((sequence * samples + i) * 0.10) for i in indexes],
        "gyro_y_deg_s": [1.5 * math.sin((sequence * samples + i) * 0.07) for i in indexes],
        "gyro_z_deg_s": [3.0 * math.sin((sequence * samples + i) * 0.09) for i in indexes],
        "phone_receive_time_ns": time.time_ns(),
    }


async def send_and_expect(websocket, message, expected_type):
    await websocket.send(json.dumps(message))
    response = json.loads(await websocket.recv())
    if response.get("type") != expected_type:
        raise RuntimeError(f"expected {expected_type}, got {response}")
    return response


async def run(args):
    uri = f"ws://{args.host}:{args.port}"
    async with websockets.connect(uri) as websocket:
        hello = await send_and_expect(
            websocket,
            {"type": "hello", "version": 1, "client": "test_client"},
            "hello_ack",
        )
        print(f"connected to {hello.get('server', 'server')}")

        started = await send_and_expect(
            websocket,
            {"type": "start_session", "version": 1, "label": args.label},
            "session_started",
        )
        if not started.get("success"):
            raise RuntimeError(started.get("message", "failed to start session"))
        print(f"started {started.get('session_id')}")

        watch_ms = 0
        for sequence in range(args.batches):
            batch = make_batch(sequence, watch_ms)
            ack = await send_and_expect(websocket, batch, "imu_batch_ack")
            if ack.get("sequence") != sequence:
                raise RuntimeError(f"unexpected ack: {ack}")
            watch_ms += 1000
            await asyncio.sleep(1.0)

        stopped = await send_and_expect(
            websocket,
            {"type": "stop_session", "version": 1},
            "session_stopped",
        )
        if not stopped.get("success"):
            raise RuntimeError(stopped.get("message", "failed to stop session"))
        print(f"stopped {stopped.get('session_id')}")


def main():
    parser = argparse.ArgumentParser(description="Test the WearNav generic app bridge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--label", default="app_bridge_test")
    parser.add_argument("--batches", type=int, default=6)
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
