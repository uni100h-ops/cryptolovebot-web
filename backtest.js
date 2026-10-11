'use strict';
// A replay of supplied trades, not a strategy run against newly fetched candles.
(function (root) {
  const MIN_DATE = Date.UTC(2020, 0, 1);
  const DAY = 86400000;
  function parseDate(value) {
    const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(String(value).trim());
    if (!m) return NaN;
    const [, day, month, year] = m.map(Number);
    const time = Date.UTC(year, month - 1, day);
    const d = new Date(time);
    return d.getUTCFullYear() === year && d.getUTCMonth() === month - 1 && d.getUTCDate() === day ? time : NaN;
  }
  function date(value) {
    const d = new Date(value);
    if (!Number.isFinite(d.getTime())) return '—';
    return [d.getUTCDate(), d.getUTCMonth() + 1].map(n => String(n).padStart(2, '0')).join('/') + '/' + d.getUTCFullYear();
  }
  function stamp(value) {
    const d = new Date(value);
    if (!Number.isFinite(d.getTime())) return '—';
    return date(value) + ' ' + [d.getUTCHours(), d.getUTCMinutes()].map(n => String(n).padStart(2, '0')).join(':');
  }
  function pair(coin) {
    const symbol = String(coin).replace(/[\s\/-]/g, '');
    return /USDC$/i.test(symbol) ? symbol : symbol + 'USDC';
  }
  function parseCapital(value) {
    if (typeof value === 'number') return value;
    const s = String(value).trim();
    // European display/input: 1.000,50. Reject ambiguous US separators.
    if (!/^(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d{1,2})?$/.test(s)) return NaN;
    return Number(s.replace(/\./g, '').replace(',', '.'));
  }
  function replay(history, { start, end, capital }) {
    const from = parseDate(start), through = parseDate(end), initial = parseCapital(capital);
    if (!Number.isFinite(from) || !Number.isFinite(through)) throw Error('invalidDates');
    if (from < MIN_DATE || through < MIN_DATE) throw Error('minDate');
    if (from > through) throw Error('dateOrder');
    if (!Number.isFinite(initial) || initial < 100) throw Error('minCapital');
    const to = through + DAY;
    const selected = history.trades.filter(r => {
      const open = Date.parse(r.open), close = Date.parse(r.close);
      return open >= from && close >= open && close < to;
    }).sort((a, b) => Date.parse(a.close) - Date.parse(b.close) || Date.parse(a.open) - Date.parse(b.open) || Number(a.id) - Number(b.id));
    const balances = [initial];
    const trades = selected.map(r => {
      const pct = Number(r.priceReturnPct);
      if (!Number.isFinite(pct) || pct < -100) throw Error('invalidHistory');
      const balance = balances.at(-1) * (1 + pct / 100);
      const cumulativePct = (balance / initial - 1) * 100;
      if (!Number.isFinite(balance) || !Number.isFinite(cumulativePct)) throw Error('amountTooLarge');
      balances.push(balance);
      return { ...r, simulatedBalance: balance, cumulativePct };
    });
    const availableFrom = Date.parse(history.period.from), availableTo = Date.parse(history.period.to);
    if (!Number.isFinite(availableFrom) || !Number.isFinite(availableTo)) throw Error('invalidHistory');
    return { trades, balances, initial, from, to,
      partial: from < Math.floor(availableFrom / DAY) * DAY || through > Math.floor(availableTo / DAY) * DAY,
      availableFrom, availableTo };
  }
  const api = { replay, parseCapital, parseDate, date, stamp, pair };
  root.CryptoLoveBacktest = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(globalThis);
