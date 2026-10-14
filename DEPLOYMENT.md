# Deploying on Raspberry Pi

The `robotcar` systemd service runs `app.py` at boot and restarts it if it
exits unexpectedly. The installer uses Raspberry Pi OS's system Python
packages, grants the service user's account access to the `gpio` and `video`
groups when those groups are present, and registers the service with systemd.

## Install

1. Copy or clone this project onto the Raspberry Pi. Keep `app.py` and the
   `templates/` directory together. Log in as the normal Raspberry Pi user
   (not `root`), and open a terminal in the project directory.
2. Run:

   ```bash
   chmod +x deploy.sh
   sudo ./deploy.sh
   ```

   The installer installs Flask, OpenCV, Picamera2, and RPi.GPIO from apt,
   writes `/etc/systemd/system/robotcar.service` with the current project path,
   and enables and starts the service. To use another existing Linux account
   for the service, run `sudo ROBOTCAR_USER=<username> ./deploy.sh`.

3. Find the Pi's address and check the service:

   ```bash
   hostname -I
   sudo systemctl status robotcar
   ```

4. From a phone or computer on the same network, visit:

   ```text
   http://<raspberry-pi-ip>:5000
   ```

The service is enabled at boot. You do not need to launch `app.py` manually
after installation.

## Service commands

```bash
sudo systemctl status robotcar
sudo systemctl restart robotcar
sudo systemctl stop robotcar
sudo systemctl start robotcar
sudo journalctl -u robotcar -f
```

Run `sudo ./deploy.sh` again after changing the deployment setup or updating
the project; it refreshes dependencies and the service configuration, then
restarts the app.

## Troubleshooting

- **Service failed to start:** inspect recent logs with
  `sudo journalctl -u robotcar -e`.
- **Camera initialization errors:** confirm the camera works on the Pi and that
  Picamera2 is installed (`python3-picamera2`); check the service logs above.
- **GPIO permission errors:** check that the `gpio` group exists and that the
  service's `User` and `SupplementaryGroups` in
  `/etc/systemd/system/robotcar.service` are correct. The installer adds the
  account to available `gpio` and `video` groups.
- **Cannot connect:** confirm the phone/computer and Pi are on the same network,
  use the address from `hostname -I`, and check that port 5000 is allowed by
  the local firewall.

## Network safety

The app listens on all network interfaces, and its driving endpoints currently
have no authentication. Use it only on a trusted private network. Do not port
forward port 5000 or expose it directly to the public internet.
