# Harogic SDR and RF Swift Setup Rules

- **Docker & Sudo:** DO NOT use `sudo` for any docker or hardware operations, as it restarts the user's system. The user operates docker via `newgrp docker` or standard permissions.
- **RF Swift Environment:** The project relies on PentHertz's RF Swift container toolbox. The term "swiftpp" refers to this container environment, not a specific executable inside it.
- **Harogic Image:** Always use the `penthertz/rfswift_noble:sdr_full` image for Harogic tests, as it comes pre-compiled with `SoapySDR` and the `libHarogicSupport.so` module (`harogic` factory).
- **Execution Command:** To run the container and detect the Harogic device, you MUST use privileged mode (`-u 1`) and bind the USB bus (`-s /dev/bus/usb`). 
  Command: `rfswift run -i penthertz/rfswift_noble:sdr_full -s /dev/bus/usb -u 1`
- **SDR Detection:** Inside the container, use `SoapySDRUtil --find` to verify Harogic detection, or `gqrx` to listen to signals.
