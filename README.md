# CryptoLoveBot — Web
Official WebSite: https://cryptolovebot.com/


**A web interface for automated trading on Hyperliquid, with revocable agent authorization and transparent account reporting.**

[Website](https://cryptolovebot.com) · [Server repository](https://github.com/uni100h-ops/cryptolovebot-server) · [Hyperliquid agent management](https://app.hyperliquid.xyz/API)

CryptoLoveBot is an early-stage trading product. Its interface brings account access, wallet authorization, historical trade replay, and real account reporting into one place. The minimum trading capital is **100 USDC**.

This public repository contains the frontend. The private trading engine runs separately on **Hetzner** and is not distributed here. The companion server repository is also public; it contains the API and integration layer, not the full strategy engine.

## What is included

- A responsive HTML, CSS, and JavaScript interface with English, Spanish, French, and German translations.
- Email registration, verification, password recovery, and optional Google sign-in interfaces.
- MetaMask connection and signing flows for wallet ownership, Hyperliquid agent approval, and fee payment.
- A private account area for trade records, account information, outstanding fees, and pausing or resuming new entries.
- A public master-account performance view, configured to start on 10 October 2026.
- A real-account log interface with date filters, timezone selection, CSV export, and a Hypurrscan link. This requires a compatible backend endpoint; see the integration notes below.
- Interactive replay of imported historical trades, including playback controls and linear or logarithmic charts.
- A Python utility for converting the simulator's Excel output into the frontend's historical dataset.

These are the interfaces present in the repository. Account and trading functions depend on a correctly configured, compatible server and the separately installed private engine.

## Architecture

| Component | Responsibility | Location |
| --- | --- | --- |
| `cryptolovebot-web` | Public website, dashboards, wallet signing, historical replay | Public repository; static deployment configuration for Render |
| `cryptolovebot-server` | Authentication, authorization, reporting, billing, worker supervision | Public repository; backend hosted on Hetzner |
| Private strategy engine | Signal evaluation and trading execution through the server integration | Hetzner; outside both public repositories |
| Hyperliquid | Trading accounts, orders, fills, and portfolio data | Exchange infrastructure |

The browser signs wallet actions with MetaMask. It does not receive the trading agent's private key. The server generates and encrypts that agent key and supplies it to the private engine for the authorized account.

## Run a local frontend preview

The frontend has no npm dependency installation or JavaScript build step.

```bash
git clone https://github.com/uni100h-ops/cryptolovebot-web.git
cd cryptolovebot-web
python3 -m http.server 8080 --bind 127.0.0.1
```

Open `http://127.0.0.1:8080` for the static interface and historical replay. Do not open `index.html` directly as a local file: the page loads `history.json` with `fetch`.

Authenticated features require a compatible API, matching allowed frontend origin, and an HTTPS setup that supports the backend's secure session cookie. A static HTTP preview does not establish a complete authenticated development environment.

## API configuration

The public API base URL is configured in `config.js`:

```javascript
window.CRYPTOLOVE = {
  apiUrl: "https://api.cryptolovebot.com"
};
```

Set this to your own compatible API when running a separate deployment. The backend's `FRONTEND_URL` must match the frontend origin exactly. Only public configuration belongs in this file; credentials and wallet keys belong on the server.

## Static deployment

`render.yaml` defines a Render static service with the following settings:

| Setting | Value |
| --- | --- |
| Service name | `cryptolovebot-web` |
| Publish directory | `dist` |
| Build command | `mkdir -p dist && cp index.html style.css app.js backtest.js config.js logo.svg history.json account-log.html account-log.js account-log.css dist/` |

The configuration also supplies browser security headers and disables caching for `config.js`. Configure the website domain and API URL for the environment being deployed.

## Historical replay methodology

The section labelled **Create Backtesting** replays records already stored in `history.json`. It does not download new candles or execute the private strategy.

For the selected period, it takes completed trades whose opening and closing timestamps fall within the selection, sorts them by closing time, and compounds each trade's `priceReturnPct`:

```text
next_balance = previous_balance × (1 + priceReturnPct / 100)
```

This illustrative balance does not reproduce simultaneous capital allocation, leverage, exchange costs, funding, or CryptoLoveBot fees. It must not be interpreted as an executable portfolio backtest, live profit, or a forecast.

The current replay accepts dates between **1 January 2021 and 7 October 2026** and uses only the records actually available in the dataset. Selecting a wider interval does not create additional history. Capital input uses European formatting, for example `1.000,00`.

To regenerate the dataset from a compatible simulator workbook:

```bash
python3 import_history.py /path/to/simulator-output.xlsx \
  --sheet Operaciones \
  --timezone Europe/Madrid \
  --output history.json
```

The importer requires the simulator's existing column names and explicit UTC opening labels. It validates timezone conversion, excludes incomplete or unexecuted records, and records source metadata including a SHA-256 hash. Review the regenerated dataset before publishing it.

## Live reporting and user controls

The headline percentage comes from the backend's public master-account report, independently of `history.json`. The companion implementation uses an estimated Modified Dietz return based on sampled Hyperliquid perpetual-account equity and PnL, including unrealized PnL. A link to an external explorer allows independent inspection; it is not a certified audit.

The account-log view describes execution-level totals. Its displayed PnL minus execution fees is not a complete account return and excludes funding and deposits or withdrawals.

Pausing new entries is different from deleting a profile. While the engine remains running, a paused account can continue to have existing positions managed. Profile deletion stops that management; positions and exchange-native orders remain on Hyperliquid, and the user must manage them and revoke the agent there.

## Fee model

With the default `FEE_BASIS=profit`, a completed trade is charged **1% of its net profit only if its net return exceeds 1% of entry margin**. At or below that threshold, no CryptoLoveBot fee is accrued. Payment requires a separate MetaMask signature. This is a per-trade calculation, not a portfolio high-water-mark calculation.

The server also supports an alternative margin-based configuration, which changes the fee base. The interface reads the configured model from `/public/config`.

The implemented payment policy uses a 48-hour deadline from the oldest outstanding fee, with reminders every 8 hours. An overdue unpaid fee can trigger profile deletion and stop automation. Open positions remain on Hyperliquid. The server suspends this deletion flow when a payment is awaiting reconciliation.

## Public repository integration status

Source review date: **12 October 2026**. The two public repositories are not yet fully synchronized:

| Frontend expectation | Current public server behavior | Effect |
| --- | --- | --- |
| Email and password submitted by the signup form | `Signup` also requires `username` | Signup is rejected unless the client or server contract is aligned |
| A truthy `verified` field in login and `/me` responses | `safe_user()` omits `verified` | The private area and wallet connection remain hidden |
| `GET /public/account-log` | No matching route in the published `app.py` | The account-log interface cannot load from that backend snapshot |
| `supportEmail` from `/public/config` | The field is not returned | The contact action shows an unavailable message |

These observations describe the published source, not an inspection of the running Hetzner deployment. Use matched frontend and backend versions when evaluating the complete workflow. The private engine is also required for trading; cloning the two public repositories is not enough to reproduce the full system.

## Main files

| File | Purpose |
| --- | --- |
| `index.html`, `style.css`, `logo.svg` | Website layout, styling, and branding |
| `app.js` | Account flows, wallet interaction, translations, dashboards |
| `backtest.js` | Historical replay calculations and input validation |
| `history.json` | Imported historical simulation data and provenance |
| `import_history.py` | Simulator workbook importer |
| `account-log.html`, `account-log.js`, `account-log.css` | Public execution-log interface |
| `config.js` | Public API configuration |
| `render.yaml` | Static hosting configuration |

## Project status and license

CryptoLoveBot is under active development. Simulation and live execution are not guaranteed to produce identical trades or returns. Automated trading involves risk of loss.

The repository is public. No license file was present in the reviewed source; public availability should not be interpreted as a grant of open-source reuse rights. The private strategy engine is excluded from this repository.
