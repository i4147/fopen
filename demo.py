import importlib
import sys

import fopen as wo


def main():
    print("=== WithOpen Demo ===")

    wo.remove("demo_1d", display=False)
    wo.w("demo_1d", ["alpha", "beta", "gamma"], is2d=False)
    print("1D read:", wo.r("demo_1d"))
    print("1D index 1:", wo.r("demo_1d", index=1))
    wo.a("demo_1d", ["delta"], is2d=False)
    print("After append:", wo.r("demo_1d"))

    wo.remove("demo_2d", display=False)
    wo.w("demo_2d", [["alice", 30], ["bob", 25], ["carol", 40]], is2d=True)
    print("2D read:", wo.r("demo_2d"))
    wo.a("demo_2d", [["dave", 22]], is2d=True)
    print("2D after append:", wo.r("demo_2d"))

    removed, remaining = wo.d("demo_2d", del_list=["bob"], index=[0])
    print(f"Removed {removed} row(s); remaining: {remaining}")

    wo.backup("demo_1d", display=True)
    wo.snapshot("demo_1d", "s", 0.0001, display=True)

    print("Files:", wo.listdir(display=False))
    payload = wo.info("demo_1d", display=False)
    print("Info:", payload)

    wo.consoles("demo_1d", multiple=False, alert=False)
    wo.warning(True)
    print("Backdate marker:", wo.backdate("demo_1d", "s", gap=0))

    print("Progress:", wo.loop_progress(3, 10))
    print("Future time:", wo.future_datetime(5, "m"))
    print("Align:", repr(wo.align_text("centered", "center")))
    print("Styled:", wo.stylize("bold text", bold=True))

    buffer = wo.ScreenBuffer(wait=True)
    buffer.put("log line 1")
    buffer.put("log line 2")
    buffer.put("warning line", level=1)
    for row in buffer.format_text_for_display():
        print(row)

    wo.remove("demo_1d", display=False)
    wo.remove("demo_2d", display=False)
    print("Done.")


if __name__ == "__main__":
    main()
