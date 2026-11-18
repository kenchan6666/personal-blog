# Backups on the VM

Install (once, as a sudoer):

```bash
sudo cp deployment/systemd/personal-blog-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now personal-blog-backup.timer
sudo systemctl start personal-blog-backup.service   # run one now
journalctl -u personal-blog-backup.service -n 50
```

Archives land in `/mnt/disks/data/backups` (14 days). The data disk itself also
has a daily GCP snapshot schedule (`personalblog-data-daily`, 7-day retention).

`data/` in the checkout is a symlink to `/mnt/disks/data/personal-blog-data`,
so uploads (`media/`) and resume PDFs (`resumes/`) sit on the data disk.
