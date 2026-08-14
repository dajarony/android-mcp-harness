# Verifies the harness itself, on any machine, with one command.
#
# The Android emulator is deliberately NOT in here. Running it in a container
# needs /dev/kvm, which Docker Desktop on Windows and macOS cannot reliably pass
# through, and Appium's UiAutomator2 driver forwards device ports through the
# adb server, so those forwards would land on the host and be unreachable from
# inside. Claiming otherwise would be a promise nobody had tested.
#
# What this image does prove: the contracts hold, the bank passes, the MCP
# server starts over real stdio and publishes exactly its declared catalogue.
# The live campaign against an AVD stays native, and `doctor` says what is
# missing for it.

FROM python:3.13-slim

# adb is present so `doctor` can report on a device and so this image can talk
# to an adb server on the host when one is offered.
RUN apt-get update \
    && apt-get install -y --no-install-recommends adb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /harness

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY . .

ENV PYTHONPATH=/harness \
    PYTHONUNBUFFERED=1 \
    ANDROID_UDID=emulator-5554 \
    APPIUM_URL=http://127.0.0.1:4723

# The bank needs no device, so the default command proves the harness outright.
CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
