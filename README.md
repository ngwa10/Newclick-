# Pocket Option Telegram Signal Trading Bot

Automates Pocket Option trades using signals from a Telegram channel. Features martingale logic, hotkey automation, fast win/loss detection, and full browser control.

## Features

- Listens to signals via Telegram
- Parses asset, direction, timeframe, and martingale levels
- Automatically executes trades via hotkeys
- Uses Selenium to select asset and timeframe
- Martingale logic: auto-increases amount after loss, customizable levels
- Fast win/loss detection via OCR
- Highly modular, production-ready code

## Architecture.

```
core.py                  # Main. orchestrator, trade manager, hotkey controller
telegram_integration.py  # Telegram listener and signal parser
selenium_integration.py  # Selenium setup, asset/timeframe selection
bot.py                   # Entry point, runs core.py
.env                     # Environment variables/config
requirements.txt         # Dependencies
```

## Setup

1. **Clone repo & install dependencies**
   ```
   pip install -r requirements.txt
   ```

2. **Update `.env` with your credentials**
   - Telegram API ID/hash/bot token
   - Channel name or ID
   - BASE_TRADE_AMOUNT, MAX_MARTINGALE

3. **Ensure Chrome & ChromeDriver are installed**
   - (See Dockerfile for automated setup)

## Usage

- Run with:
  ```
  python bot.py
  ```
- Use `/start` and `/stop` commands in your Telegram channel to control trading.

## Customizing Martingale Levels

- Anna signals (without explicit martingale levels) default to 2 levels.
- Edit `telegram_integration.py` to change number or timing of levels.

## Troubleshooting

- **OCR not detecting results?** Adjust region in core.py.
- **Currency pair/timeframe selection not working?** Update Selenium selectors in selenium_integration.py.
- **Bot not trading?** Check logs, Telegram credentials, and ensure `.env` values are correct.

## License

MIT.
