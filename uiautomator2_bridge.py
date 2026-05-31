#!/usr/bin/env python3
"""
uiautomator2 bridge for android-mcp.
Reads JSON commands from stdin, executes via uiautomator2, returns JSON on stdout.
"""
import sys
import json
import base64
import traceback

try:
    import uiautomator2 as u2
except ImportError:
    sys.stderr.write("uiautomator2 not installed. Run: pip install uiautomator2\n")
    sys.exit(1)

_device = None

def get_device(device_serial=None):
    global _device
    if _device is None:
        try:
            if device_serial:
                _device = u2.connect(device_serial)
            else:
                _device = u2.connect()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to device: {e}")
    return _device

def handle_get_device_info(args):
    serial = args.get("deviceSerial")
    d = get_device(serial)
    info = d.info
    return {"success": True, "data": info}

def handle_tap(args):
    d = get_device()
    x, y = args["x"], args["y"]
    d.click(x, y)
    return {"success": True}

def handle_input_text(args):
    d = get_device()
    d.send_keys(args["text"])
    return {"success": True}

def handle_find_element(args):
    d = get_device()
    kwargs = {}
    if args.get("text"):
        kwargs["text"] = args["text"]
    if args.get("textContains"):
        kwargs["textContains"] = args["textContains"]
    if args.get("description"):
        kwargs["description"] = args["description"]
    if args.get("resourceId"):
        kwargs["resourceId"] = args["resourceId"]
    if args.get("className"):
        kwargs["className"] = args["className"]

    if not kwargs:
        return {"success": False, "found": False, "error": "No search criteria provided"}

    try:
        el = d(**kwargs)
        if el.exists:
            info = el.info
            bounds_obj = info.get("bounds", {})
            bounds = [
                bounds_obj.get("left", 0),
                bounds_obj.get("top", 0),
                bounds_obj.get("right", 0),
                bounds_obj.get("bottom", 0),
            ]
            return {
                "success": True,
                "found": True,
                "element": {
                    "description": info.get("contentDescription", ""),
                    "resourceId": info.get("resourceName", ""),
                    "className": info.get("className", ""),
                    "bounds": bounds,
                }
            }
        return {"success": True, "found": False}
    except Exception as e:
        return {"success": False, "found": False, "error": str(e)}

def handle_get_screen_dump(args):
    d = get_device()
    xml = d.dump_hierarchy()
    info = d.info
    return {
        "success": True,
        "data": {
            "xml": xml,
            "displayWidth": info.get("displayWidth", 1080),
            "displayHeight": info.get("displayHeight", 1920),
            "currentPackageName": info.get("currentPackageName", "unknown"),
        }
    }

def handle_open_app(args):
    d = get_device()
    pkg = args["packageName"]
    stop = args.get("stop", False)
    if stop:
        d.app_stop(pkg)
    activity = args.get("activity")
    if activity:
        d.app_start(pkg, activity)
    else:
        d.app_start(pkg)
    return {"success": True}

def handle_press_key(args):
    d = get_device()
    key = args["key"]
    d.press(key)
    return {"success": True}

def handle_swipe(args):
    d = get_device()
    d.swipe(args["fx"], args["fy"], args["tx"], args["ty"], duration=args.get("duration", 0.5))
    return {"success": True}

def handle_long_tap(args):
    d = get_device()
    d.long_click(args["x"], args["y"], duration=args.get("duration", 0.5))
    return {"success": True}

def handle_double_tap(args):
    d = get_device()
    d.double_click(args["x"], args["y"], duration=args.get("duration", 0.1))
    return {"success": True}

def handle_take_screenshot(args):
    import io
    d = get_device()
    img = d.screenshot()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    fname = args.get("filename")
    if fname:
        img.save(fname)
        return {"success": True, "message": f"Screenshot saved to {fname}", "data": {"image": b64}}
    return {"success": True, "data": {"image": b64}}

def handle_xpath_operation(args):
    d = get_device()
    xpath = args["xpath"]
    action = args.get("action", "click")
    el = d.xpath(xpath)
    if not el.wait(timeout=5):
        return {"success": False, "error": f"XPath element not found: {xpath}"}
    if action == "click":
        el.click()
        return {"success": True, "message": "XPath click completed"}
    elif action == "input":
        el.set_text(args.get("text", ""))
        return {"success": True, "message": "XPath input completed"}
    else:
        return {"success": False, "error": f"Unknown XPath action: {action}"}

def handle_get_installed_apps(args):
    d = get_device()
    apps = d.app_list_running()
    result = [{"packageName": a, "appName": a} for a in apps]
    return {"success": True, "data": {"apps": result}}

HANDLERS = {
    "get_device_info": handle_get_device_info,
    "tap": handle_tap,
    "input_text": handle_input_text,
    "find_element": handle_find_element,
    "get_screen_dump": handle_get_screen_dump,
    "open_app": handle_open_app,
    "press_key": handle_press_key,
    "swipe": handle_swipe,
    "long_tap": handle_long_tap,
    "double_tap": handle_double_tap,
    "take_screenshot": handle_take_screenshot,
    "xpath_operation": handle_xpath_operation,
    "get_installed_apps": handle_get_installed_apps,
}

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            cmd = json.loads(line)
            action = cmd.get("action", "")
            args = cmd.get("args", {})
            handler = HANDLERS.get(action)
            if handler:
                result = handler(args)
            else:
                result = {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            result = {"success": False, "error": str(e), "traceback": traceback.format_exc()}

        sys.stdout.write(json.dumps(result) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
