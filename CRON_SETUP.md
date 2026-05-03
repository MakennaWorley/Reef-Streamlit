# Cron Job Setup for Daily Data Loading

This document explains how to set up a cron job for guaranteed daily execution of the reef data loader, even when Streamlit is not running.

## Quick Setup

Run this command to add the cron job:

```bash
(crontab -l 2>/dev/null; echo "0 0 * * * cd /Users/makennaworley/Desktop/GitHubCode/reef-streamlit && source reef-env/bin/activate && python -m mongo.load_daily_data >> /tmp/reef_cron.log 2>&1") | crontab -
```

## Manual Setup

If you prefer to set it up manually:

1. Open your crontab editor:
   ```bash
   crontab -e
   ```

2. Add this line (runs daily at midnight UTC):
   ```
   0 0 * * * cd /Users/makennaworley/Desktop/GitHubCode/reef-streamlit && source reef-env/bin/activate && python -m mongo.load_daily_data >> /tmp/reef_cron.log 2>&1
   ```

3. Save and exit (typically `Ctrl+X` then `Y` then `Enter`)

## Verification

Check if the cron job was added:
```bash
crontab -l
```

You should see your reef data loader job listed.

## Logs

View the cron job execution logs:
```bash
tail -f /tmp/reef_cron.log
```

## Remove Cron Job

If you need to remove the cron job:
```bash
crontab -r
```

Then re-add just your other jobs if needed.

## Notes

- **Time Zone**: The cron job runs at midnight UTC. Adjust the hour value if needed (e.g., `0 5 * * *` for 5 AM UTC)
- **Path**: Make sure the path `/Users/makennaworley/Desktop/GitHubCode/reef-streamlit` is correct
- **Virtual Environment**: The `source reef-env/bin/activate` ensures the correct Python environment is used
- **Logging**: Output is logged to `/tmp/reef_cron.log` for monitoring

## Dual Setup (Recommended)

With **both** cron job + Streamlit scheduler:

- ✅ **Cron job**: Guaranteed daily execution at midnight
- ✅ **Streamlit scheduler**: Additional backup when Streamlit app is running

This ensures your data is always updated, regardless of whether Streamlit is active.
