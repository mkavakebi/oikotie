# Automatic Daily Scraping Setup

This guide explains how to set up automatic daily data refresh for the Oikotie Property Tracker on your Mac.

## What Was Created

1. **`run_daily_scrape.sh`** - Shell script that runs the scraper
2. **`com.oikotie.dailyscrape.plist`** - launchd configuration file (in `~/Library/LaunchAgents/`)

## Installation Steps

### 1. Make the Script Executable

```bash
chmod +x /Users/morteza.kavakebi/PycharmProjects/oikotie/scripts/run_daily_scrape.sh
```

### 2. Load the Scheduled Task

```bash
launchctl load ~/Library/LaunchAgents/com.oikotie.dailyscrape.plist
```

### 3. Verify It's Loaded

```bash
launchctl list | grep oikotie
```

You should see `com.oikotie.dailyscrape` in the output.

## Schedule Configuration

**Current Schedule**: Daily at 9:00 AM

To change the time, edit the plist file:
```bash
nano ~/Library/LaunchAgents/com.oikotie.dailyscrape.plist
```

Modify the `Hour` and `Minute` values:
```xml
<key>Hour</key>
<integer>9</integer>  <!-- Change this (0-23) -->
<key>Minute</key>
<integer>0</integer>  <!-- Change this (0-59) -->
```

After editing, reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.oikotie.dailyscrape.plist
launchctl load ~/Library/LaunchAgents/com.oikotie.dailyscrape.plist
```

## Management Commands

### Stop Automatic Scraping
```bash
launchctl unload ~/Library/LaunchAgents/com.oikotie.dailyscrape.plist
```

### Start Automatic Scraping
```bash
launchctl load ~/Library/LaunchAgents/com.oikotie.dailyscrape.plist
```

### Test the Script Manually
```bash
/Users/morteza.kavakebi/PycharmProjects/oikotie/run_daily_scrape.sh
```

### Trigger the Scheduled Job Immediately (for testing)
```bash
launchctl start com.oikotie.dailyscrape
```

## Monitoring

### Check Logs

The scraper creates three log files in the `data/` directory:

1. **`scrape.log`** - Completion timestamps
   ```bash
   tail -f data/scrape.log
   ```

2. **`scrape_stdout.log`** - Standard output from the scraper
   ```bash
   tail -f data/scrape_stdout.log
   ```

3. **`scrape_stderr.log`** - Error messages (if any)
   ```bash
   tail -f data/scrape_stderr.log
   ```

### Check if Job Ran Recently
```bash
launchctl list com.oikotie.dailyscrape
```

Look for the "LastExitStatus" (0 = success) and timestamps.

## Important Notes

### Computer Must Be On
- **Your Mac must be powered on and awake** for the job to run
- If your Mac is asleep or off at the scheduled time, the job will NOT run
- Consider adjusting your Mac's Energy Saver settings if needed

### Browser Requirements
- The scraper uses Selenium with Chrome in headless mode
- Chrome must be installed on your system
- ChromeDriver is managed automatically by Selenium 4.x

## Risks and Considerations

### Low Risk ✅
- **Data corruption**: Very low - the scraper appends/updates data safely
- **System resources**: Minimal - runs once daily for a few minutes
- **Privacy**: All data stays on your computer

### Medium Risk ⚠️
- **Website changes**: Oikotie.fi might change their HTML structure, breaking the scraper
  - *Mitigation*: Check logs periodically; you'll still have your existing data
- **Rate limiting**: Running too frequently might get your IP temporarily blocked
  - *Mitigation*: Once daily is safe; avoid manual runs right before/after scheduled runs
- **Disk space**: Over time, historical data grows
  - *Mitigation*: Monitor `data/` directory size; old data can be archived

### Computer Sleep Issues ⚠️
- If your Mac sleeps, the job won't run
  - *Mitigation*: Adjust System Preferences > Energy Saver, or use `caffeinate` command

### Failure Scenarios
- **Chrome updates**: Automatic Chrome updates might temporarily break ChromeDriver
  - *Mitigation*: Check error logs; Selenium usually auto-updates drivers
- **Network issues**: If internet is down, scraper will fail
  - *Mitigation*: Job will retry next day automatically

## Alternative: Run on Server/Cloud

For more reliability, consider:
- **Raspberry Pi**: Run 24/7 at home
- **Cloud VM**: AWS/DigitalOcean/Heroku with scheduled tasks
- **GitHub Actions**: Free scheduled workflows (requires code modifications)

## Troubleshooting

### Job Doesn't Run
1. Check if loaded: `launchctl list | grep oikotie`
2. Check permissions: `ls -la ~/Library/LaunchAgents/com.oikotie.dailyscrape.plist`
3. Check error log: `cat data/scrape_stderr.log`

### Scraper Fails
1. Test manually: `./run_daily_scrape.sh`
2. Check Chrome is installed: `which google-chrome-stable` or `which chromium`
3. Check virtual environment: `source venv/bin/activate && python3 --version`

### Permission Denied
```bash
chmod +x run_daily_scrape.sh
```

## Uninstall

To completely remove automatic scraping:

```bash
# Unload the job
launchctl unload ~/Library/LaunchAgents/com.oikotie.dailyscrape.plist

# Remove the plist file
rm ~/Library/LaunchAgents/com.oikotie.dailyscrape.plist

# Optionally remove the script
rm /Users/morteza.kavakebi/PycharmProjects/oikotie/scripts/run_daily_scrape.sh
```
