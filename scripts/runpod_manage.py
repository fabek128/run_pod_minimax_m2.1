#!/usr/bin/env python3
import argparse
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiError(RuntimeError):
    def __init__(self, method, url, status, reason, detail):
        super().__init__(f"{method} {url} failed: {status} {reason} {detail}")
        self.method = method
        self.url = url
        self.status = status
        self.reason = reason
        self.detail = detail


def load_env_file(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def get_env(key: str, env_map: dict, default=None):
    value = os.getenv(key)
    if value is not None:
        return value
    return env_map.get(key, default)


def parse_bool(value, default=False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_int(value, default=None):
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid integer value: {value}") from exc


def parse_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [item.strip() for item in str(value).split(",") if item.strip()]


def request_json(api_base, api_key, method, path, data=None, params=None, verbose=False):
    url = f"{api_base}{path}"
    if params:
        url = f"{url}?{urlencode(params, doseq=True)}"
    headers = {"Authorization": f"Bearer {api_key}"}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if verbose:
        print(f"[api] {method} {url}")
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            raw = resp.read()
            if not raw:
                if verbose:
                    print(f"[api] {method} {url} -> {resp.getcode()}")
                return resp.getcode(), None
            data = json.loads(raw)
            if verbose:
                if isinstance(data, list):
                    print(f"[api] {method} {url} -> {resp.getcode()} items={len(data)}")
                elif isinstance(data, dict):
                    keys = ", ".join(sorted(data.keys())[:8])
                    print(f"[api] {method} {url} -> {resp.getcode()} keys={keys}")
                else:
                    print(f"[api] {method} {url} -> {resp.getcode()}")
            return resp.getcode(), data
    except HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        raise ApiError(method, url, err.code, err.reason, detail)
    except URLError as err:
        raise ApiError(method, url, "N/A", "NetworkError", err.reason)


def build_container_env(env_map: dict) -> dict:
    allowlist = parse_list(get_env("RUNPOD_CONTAINER_ENV_KEYS", env_map))
    container_env = {}
    if allowlist:
        for key in allowlist:
            value = get_env(key, env_map)
            if value is not None and value != "":
                container_env[key] = value
        return container_env

    for key, value in env_map.items():
        if key.startswith("RUNPOD_"):
            continue
        if key == "LLAMA_BASE_URL":
            continue
        if value != "":
            container_env[key] = value
    return container_env


def redact_env(env_map: dict) -> dict:
    redacted = {}
    for key, value in env_map.items():
        if any(token in key.upper() for token in ("TOKEN", "KEY", "PASSWORD", "SECRET")):
            redacted[key] = "***"
        else:
            redacted[key] = value
    return redacted


def get_network_volume(api_base, api_key, volume_id, verbose=False):
    if not volume_id:
        return None
    _, volume = request_json(api_base, api_key, "GET", f"/networkvolumes/{volume_id}", verbose=verbose)
    return volume


def ensure_network_volume(api_base, api_key, env_map):
    volume_id = get_env("RUNPOD_NETWORK_VOLUME_ID", env_map)
    if volume_id:
        return volume_id

    volume_name = get_env("RUNPOD_NETWORK_VOLUME_NAME", env_map)
    if not volume_name:
        return None

    _, volumes = request_json(api_base, api_key, "GET", "/networkvolumes")
    for volume in volumes or []:
        if volume.get("name") == volume_name:
            return volume.get("id")

    size_gb = parse_int(get_env("RUNPOD_NETWORK_VOLUME_SIZE_GB", env_map))
    data_center_id = get_env("RUNPOD_NETWORK_VOLUME_DATA_CENTER_ID", env_map)
    if not size_gb or not data_center_id:
        raise SystemExit("RUNPOD_NETWORK_VOLUME_SIZE_GB and RUNPOD_NETWORK_VOLUME_DATA_CENTER_ID are required.")

    payload = {"name": volume_name, "size": size_gb, "dataCenterId": data_center_id}
    _, created = request_json(api_base, api_key, "POST", "/networkvolumes", data=payload)
    return created.get("id")


def main():
    parser = argparse.ArgumentParser(description="Create or recreate RunPod CPU pods via REST API.")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without calling the API.")
    parser.add_argument("--verbose", action="store_true", help="Print verbose API logs.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    env_file = Path(get_env("RUNPOD_ENV_FILE", {}, str(repo_root / ".env")))
    env_map = load_env_file(env_file)

    api_key = get_env("RUNPOD_API_KEY", env_map)
    if not api_key:
        raise SystemExit("RUNPOD_API_KEY is required.")

    api_base = get_env("RUNPOD_API_BASE", env_map, "https://rest.runpod.io/v1")
    pod_name = get_env("RUNPOD_POD_NAME", env_map, "cpu-llama")
    pod_count = parse_int(get_env("RUNPOD_POD_COUNT", env_map)) or parse_int(get_env("POD_INSTANCES", env_map), 1)
    retry_attempts = parse_int(get_env("RUNPOD_RETRY_ATTEMPTS", env_map), 0) or 0
    retry_delay = parse_int(get_env("RUNPOD_RETRY_DELAY_SEC", env_map), 60) or 60
    allow_any_dc = parse_bool(get_env("RUNPOD_ALLOW_ANY_DATACENTER_ON_FAILURE", env_map), False)

    image_name = get_env("RUNPOD_IMAGE_NAME", env_map)
    if not image_name:
        raise SystemExit("RUNPOD_IMAGE_NAME is required.")

    compute_type = get_env("RUNPOD_COMPUTE_TYPE", env_map, "CPU")
    cloud_type = get_env("RUNPOD_CLOUD_TYPE", env_map, "SECURE")

    cpu_flavors = parse_list(get_env("RUNPOD_CPU_FLAVORS", env_map) or get_env("RUNPOD_CPU_FLAVOR", env_map))
    cpu_fallbacks = parse_list(get_env("RUNPOD_CPU_FLAVOR_FALLBACKS", env_map))
    cpu_flavor_priority = get_env("RUNPOD_CPU_FLAVOR_PRIORITY", env_map)
    fallback_enabled = parse_bool(get_env("RUNPOD_FALLBACK_ENABLED", env_map), False)

    ports = parse_list(get_env("RUNPOD_PORTS", env_map, "8000/http"))
    data_center_ids = parse_list(get_env("RUNPOD_DATA_CENTER_IDS", env_map))
    volume_mount_path = get_env("RUNPOD_VOLUME_MOUNT_PATH", env_map, "/models")
    volume_in_gb = parse_int(get_env("RUNPOD_VOLUME_SIZE_GB", env_map))
    container_disk_gb = parse_int(get_env("RUNPOD_CONTAINER_DISK_GB", env_map))

    container_env = build_container_env(env_map)
    network_volume_id = ensure_network_volume(api_base, api_key, env_map)
    network_volume = None
    if network_volume_id:
        network_volume = get_network_volume(api_base, api_key, network_volume_id, verbose=args.verbose)
        if network_volume and network_volume.get("dataCenterId"):
            dc = network_volume.get("dataCenterId")
            if data_center_ids and dc not in data_center_ids:
                print(f"[warn] Network volume is in {dc}. Overriding dataCenterIds to match the volume.")
            data_center_ids = [dc]

    names = [pod_name] if pod_count == 1 else [f"{pod_name}-{i+1}" for i in range(pod_count)]

    print(f"Using env file: {env_file}")
    print(f"API base: {api_base}")
    print(f"Pod name(s): {', '.join(names)}")
    print(f"Image: {image_name}")
    print(f"Compute: {compute_type} | Cloud: {cloud_type}")
    if cpu_flavors:
        print(f"CPU flavors: {', '.join(cpu_flavors)}")
    if fallback_enabled and cpu_fallbacks:
        print(f"Fallback enabled: CPU flavors={', '.join(cpu_fallbacks)}")
    if data_center_ids:
        print(f"Data centers: {', '.join(data_center_ids)}")
    print(f"Ports: {', '.join(ports)}")
    if network_volume_id:
        if network_volume and network_volume.get("dataCenterId"):
            print(f"Network volume ID: {network_volume_id} (DC {network_volume.get('dataCenterId')})")
        else:
            print(f"Network volume ID: {network_volume_id}")
    if volume_in_gb and not network_volume_id:
        print(f"Pod volume (GB): {volume_in_gb}")
    if container_disk_gb:
        print(f"Container disk (GB): {container_disk_gb}")
    if container_env:
        print(f"Container env keys: {', '.join(sorted(container_env.keys()))}")

    for name in names:
        _, pods = request_json(api_base, api_key, "GET", "/pods", params={"name": name}, verbose=args.verbose)
        for pod in pods or []:
            print(f"Deleting pod {pod.get('name')} ({pod.get('id')})")
            if not args.dry_run:
                request_json(api_base, api_key, "DELETE", f"/pods/{pod.get('id')}", verbose=args.verbose)
                time.sleep(1)

        base_payload = {
            "name": name,
            "imageName": image_name,
            "computeType": compute_type,
            "cloudType": cloud_type,
            "ports": ports,
            "env": container_env,
            "volumeMountPath": volume_mount_path,
        }

        if data_center_ids:
            base_payload["dataCenterIds"] = data_center_ids
        if volume_in_gb and not network_volume_id:
            base_payload["volumeInGb"] = volume_in_gb
        if network_volume_id:
            base_payload["networkVolumeId"] = network_volume_id
        if container_disk_gb:
            base_payload["containerDiskInGb"] = container_disk_gb
        if cpu_flavor_priority:
            base_payload["cpuFlavorPriority"] = cpu_flavor_priority

        def try_create(payload, attempts):
            used_any_dc_local = False
            for attempt in range(1, attempts + 1):
                try:
                    print(f"[create] {name} attempt {attempt}/{attempts}")
                    if args.verbose:
                        safe_payload = dict(payload)
                        safe_payload["env"] = redact_env(safe_payload.get("env", {}))
                        print(f"[payload] {json.dumps(safe_payload, indent=2)}")
                    _, created = request_json(
                        api_base,
                        api_key,
                        "POST",
                        "/pods",
                        data=payload,
                        verbose=args.verbose,
                    )
                    print(f"Created pod {created.get('name')} ({created.get('id')})")
                    return True
                except ApiError as err:
                    msg = str(err.detail or "")
                    lower_msg = msg.lower()
                    print(f"[error] {err}")
                    if err.detail:
                        print(f"[error-detail] {err.detail}")
                    if "no instances" in lower_msg:
                        if allow_any_dc and data_center_ids and not used_any_dc_local:
                            print("No instances available. Retrying without dataCenterIds...")
                            payload.pop("dataCenterIds", None)
                            used_any_dc_local = True
                            time.sleep(2)
                            continue
                        if attempt < attempts:
                            print(f"No instances available. Retry {attempt}/{attempts} in {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue
                        return False
                    raise SystemExit(1)
            return False

        if args.dry_run:
            print(f"Dry run - create payload for {name}:")
            safe_payload = dict(base_payload)
            safe_payload["env"] = redact_env(safe_payload.get("env", {}))
            if cpu_flavors:
                safe_payload["cpuFlavorIds"] = cpu_flavors
            print(json.dumps(safe_payload, indent=2))
            continue

        attempts = retry_attempts + 1

        if not cpu_flavors and not cpu_fallbacks:
            raise SystemExit("RUNPOD_CPU_FLAVORS (or RUNPOD_CPU_FLAVOR) is required for CPU pods.")

        flavor_candidates = []
        if cpu_flavors:
            flavor_candidates.extend(cpu_flavors)
        if cpu_fallbacks:
            for item in cpu_fallbacks:
                if item not in flavor_candidates:
                    flavor_candidates.append(item)
        if not fallback_enabled and cpu_flavors:
            flavor_candidates = [cpu_flavors[0]]

        created_ok = False
        for flavor in flavor_candidates:
            payload = dict(base_payload)
            payload["cpuFlavorIds"] = [flavor]
            print(f"[select] CPU flavor={flavor}")
            if try_create(payload, attempts):
                created_ok = True
                break

        if not created_ok:
            print("No instances available for the requested CPU flavor/region.")
            print("Try another CPU flavor, different data center, or try again later.")
            raise SystemExit(1)


if __name__ == "__main__":
    main()
