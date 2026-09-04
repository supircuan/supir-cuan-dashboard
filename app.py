from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import requests
import random
from datetime import datetime, timedelta
import time
import hashlib
import math

app = Flask(__name__, static_folder='.')
CORS(app)

price_cache = {}

def get_current_price_yahoo(symbol):
    """Ambil harga current dari Yahoo Finance"""
    try:
        ticker = f"{symbol.upper()}.JK"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {'range': '1d', 'interval': '1d'}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'chart' in data and 'result' in data['chart']:
                result = data['chart']['result'][0]
                if 'indicators' in result:
                    quotes = result['indicators']['quote'][0]
                    closes = quotes.get('close', [])
                    if closes and closes[-1]:
                        return round(closes[-1])
                if 'meta' in result and 'regularMarketPrice' in result['meta']:
                    return round(result['meta']['regularMarketPrice'])
    except Exception as e:
        print(f"Yahoo Finance error: {e}")
    return None

def get_current_price_manual(symbol):
    """Fallback harga manual jika Yahoo gagal"""
    manual_prices = {
        "BBCA": 9800, "BBRI": 5400, "BMRI": 7200, "BBNI": 5800,
        "TLKM": 3900, "ASII": 5200, "UNVR": 4300, "GOTO": 78,
        "EPAC": 60, "DEWA": 210, "ANTM": 1900, "INCO": 4800,
        "ICBP": 10800, "INDF": 7000, "ACES": 780, "KLBF": 1250,
        "MYOR": 2100, "SIDO": 650, "BUKA": 120, "BUMI": 206
    }
    return manual_prices.get(symbol.upper(), 5000)

def get_current_price(symbol):
    """Ambil harga dengan prioritas: Yahoo Finance -> Manual"""
    if symbol in price_cache:
        cache_time, cached_price = price_cache[symbol]
        if (time.time() - cache_time) < 300:
            return cached_price
    
    print(f"🔄 Fetching current price for {symbol} from Yahoo Finance...")
    price = get_current_price_yahoo(symbol)
    
    if price and price > 0:
        print(f"✓ Got real price from Yahoo: Rp {price:,}")
        price_cache[symbol] = (time.time(), price)
        return price
    
    print(f"⚠️ Yahoo failed, using manual price for {symbol}")
    price = get_current_price_manual(symbol)
    price_cache[symbol] = (time.time(), price)
    return price

def get_consistent_seed(symbol, timeframe):
    """Generate seed yang KONSISTEN berdasarkan simbol + time frame."""
    seed_string = f"{symbol.upper()}_{timeframe}_v1"
    hash_object = hashlib.md5(seed_string.encode())
    seed_int = int(hash_object.hexdigest(), 16) % (2**32)
    return seed_int

def generate_daily_data(current_price, total_days=500, seed=None):
    """Generate data harian mentah dengan seed yang konsisten"""
    if seed is not None:
        random.seed(seed)
    
    data = []
    start_price = current_price * random.uniform(0.6, 0.8)
    current = start_price
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=total_days)
    current_time = start_time
    
    day_count = 0
    while current_time <= end_time and day_count < total_days:
        timestamp = int(current_time.timestamp())
        
        volatility = 0.025
        change_percent = (random.random() - 0.48) * volatility
        
        days_remaining = total_days - day_count
        if days_remaining < 50:
            target_price = current_price
            trend_factor = (target_price - current) / current / days_remaining
            change_percent += trend_factor
        
        new_price = current * (1 + change_percent)
        min_price = current_price * 0.4
        max_price = current_price * 1.5
        new_price = max(min_price, min(max_price, new_price))
        
        open_price = current
        close_price = new_price
        high_price = max(open_price, close_price) * (1 + random.random() * 0.015)
        low_price = min(open_price, close_price) * (1 - random.random() * 0.015)
        volume = random.randint(5000000, 80000000)
        
        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
        
        current = close_price
        current_time += timedelta(days=1)
        day_count += 1
    
    if data:
        data[-1]['close'] = current_price
        data[-1]['open'] = round(current_price * (1 + (random.random() - 0.5) * 0.01))
        data[-1]['high'] = round(current_price * (1 + random.random() * 0.01))
        data[-1]['low'] = round(current_price * (1 - random.random() * 0.01))
    
    return data

def aggregate_to_timeframe(daily_data, timeframe):
    """Agregasi data harian ke time frame yang diminta"""
    if timeframe == 'daily':
        result = []
        volume_result = []
        for d in daily_data:
            result.append({
                'time': d['timestamp'],
                'open': round(d['open']),
                'high': round(d['high']),
                'low': round(d['low']),
                'close': round(d['close'])
            })
            volume_result.append({
                'time': d['timestamp'],
                'value': d['volume'],
                'color': 'rgba(8, 153, 129, 0.5)' if d['close'] >= d['open'] else 'rgba(242, 54, 69, 0.5)'
            })
        return result, volume_result
    
    interval_days = {
        'weekly': 7,
        'monthly': 30,
        'yearly': 365
    }.get(timeframe, 7)
    
    result = []
    volume_result = []
    
    for i in range(0, len(daily_data), interval_days):
        chunk = daily_data[i:i + interval_days]
        if not chunk:
            continue
        
        open_price = chunk[0]['open']
        close_price = chunk[-1]['close']
        high_price = max(d['high'] for d in chunk)
        low_price = min(d['low'] for d in chunk)
        total_volume = sum(d['volume'] for d in chunk)
        
        timestamp = chunk[-1]['timestamp']
        
        result.append({
            'time': timestamp,
            'open': round(open_price),
            'high': round(high_price),
            'low': round(low_price),
            'close': round(close_price)
        })
        
        volume_result.append({
            'time': timestamp,
            'value': total_volume,
            'color': 'rgba(8, 153, 129, 0.5)' if close_price >= open_price else 'rgba(242, 54, 69, 0.5)'
        })
    
    return result, volume_result

def calculate_square_of_9(current_price):
    """
    Hitung level Square of 9 Gann
    Rumus: (√price ± n/8)² untuk n = 1, 2, 3, 4
    """
    sqrt_price = math.sqrt(current_price)
    
    levels = {
        'resistance_4': round((sqrt_price + 4/8) ** 2),
        'resistance_3': round((sqrt_price + 3/8) ** 2),
        'resistance_2': round((sqrt_price + 2/8) ** 2),
        'resistance_1': round((sqrt_price + 1/8) ** 2),
        'current': round(current_price),
        'support_1': round((sqrt_price - 1/8) ** 2),
        'support_2': round((sqrt_price - 2/8) ** 2),
        'support_3': round((sqrt_price - 3/8) ** 2),
        'support_4': round((sqrt_price - 4/8) ** 2),
    }
    
    return levels

def calculate_time_cycles(data, timeframe):
    """
    Hitung Time Cycle Lines Gann dari swing low terakhir
    Siklus: 30, 60, 90, 120, 180, 270, 360 hari
    """
    if not data:
        return []
    
    # Cari swing low terakhir (100 candle terakhir)
    recent_data = data[-100:] if len(data) > 100 else data
    swing_low_idx_local = min(range(len(recent_data)), key=lambda i: recent_data[i]['low'])
    swing_low_idx = len(data) - len(recent_data) + swing_low_idx_local
    swing_low_time = data[swing_low_idx]['time']
    
    # Siklus penting Gann (dalam hari)
    cycles = [30, 60, 90, 120, 180, 270, 360, 450, 540]
    
    cycle_lines = []
    for cycle_days in cycles:
        cycle_timestamp = swing_low_time + (cycle_days * 86400)  # 86400 detik per hari
        if cycle_timestamp <= data[-1]['time']:  # Hanya tampilkan jika dalam range data
            cycle_lines.append({
                'time': cycle_timestamp,
                'days': cycle_days,
                'label': f'{cycle_days}d'
            })
    
    return cycle_lines

@app.route('/')
def serve_dashboard():
    return send_from_directory('.', 'dashboard_saham.html')

@app.route('/api/stock/<symbol>')
def get_stock_data(symbol):
    try:
        ticker = symbol.upper()
        timeframe = request.args.get('timeframe', 'daily').lower()
        
        print(f"\n{'='*60}")
        print(f"📊 GETTING DATA FOR {ticker}")
        print(f" Timeframe: {timeframe.upper()}")
        print(f"{'='*60}")
        
        current_price = get_current_price(ticker)
        print(f"💰 Current Price: Rp {current_price:,}")
        
        seed = get_consistent_seed(ticker, timeframe)
        print(f"🎲 Using seed: {seed}")
        
        base_days = {
            'daily': 500,
            'weekly': 1000,
            'monthly': 2000,
            'yearly': 5000
        }.get(timeframe, 500)
        
        print(f"📈 Generating {base_days} days of data...")
        daily_data = generate_daily_data(current_price, base_days, seed=seed)
        
        print(f"🔄 Aggregating to {timeframe} timeframe...")
        data, volume_data = aggregate_to_timeframe(daily_data, timeframe)
        
        # Hitung Square of 9
        print(f" Calculating Gann Square of 9...")
        square_of_9 = calculate_square_of_9(current_price)
        
        # Hitung Time Cycles
        print(f" Calculating Gann Time Cycles...")
        time_cycles = calculate_time_cycles(data, timeframe)
        
        last_price = data[-1]['close'] if data else current_price
        print(f"✓ Generated {len(data)} candles")
        print(f"✓ Last Price: Rp {last_price:,}")
        print(f"✓ Square of 9 Levels: {len(square_of_9)} levels")
        print(f"✓ Time Cycles: {len(time_cycles)} lines")
        print(f"{'='*60}\n")
        
        timeframe_labels = {
            'daily': 'Harian (Daily)',
            'weekly': 'Mingguan (Weekly)',
            'monthly': 'Bulanan (Monthly)',
            'yearly': 'Tahunan (Yearly)'
        }
        
        return jsonify({
            'symbol': ticker,
            'data': data,
            'volume': volume_data,
            'last_price': last_price,
            'current_price': current_price,
            'timeframe': timeframe,
            'timeframe_label': timeframe_labels.get(timeframe, timeframe.upper()),
            'square_of_9': square_of_9,
            'time_cycles': time_cycles,
            'source': 'auto-yahoo-finance',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/price/<symbol>')
def get_only_price(symbol):
    ticker = symbol.upper()
    price = get_current_price(ticker)
    return jsonify({
        'symbol': ticker,
        'price': price,
        'currency': 'IDR',
        'timestamp': datetime.now().isoformat()
    })
@app.route('/api/ticker/indices')
def get_indices():
    """Ambil data indeks global termasuk IHSG"""
    try:
        indices_data = {
            'KOSPI': get_yahoo_data('^KS11'),
            'HANGSENG': get_yahoo_data('^HSI'),
            'DOW30': get_yahoo_data('^DJI'),
            'NIKKEI': get_yahoo_data('^N225'),
            'SHANGHAI': get_yahoo_data('000001.SS'),
            'FTSE': get_yahoo_data('^FTSE'),
            'IHSG': get_yahoo_data('^JKSE')  # Tambahkan IHSG
        }
        return jsonify(indices_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ticker/commodities')
def get_commodities():
    """Ambil data komoditas global dengan simbol yang lebih akurat"""
    try:
        # Simbol yang lebih reliable untuk Yahoo Finance
        commodities_data = {
            'OIL': get_yahoo_data('CL=F'),           # Crude Oil WTI
            'BRENT': get_yahoo_data('BZ=F'),         # Brent Crude
            'CPO': get_yahoo_data('FCPO=F'),         # Crude Palm Oil (lebih reliable)
            'COAL': get_yahoo_data('MTF=F'),         # Newcastle Coal
            'GOLD': get_yahoo_data('GC=F'),          # Gold
            'SILVER': get_yahoo_data('SI=F'),        # Silver
            'NICKEL': get_yahoo_data('NI=F'),        # Nickel
            'ALUMINIUM': get_yahoo_data('ALI=F')     # Aluminium
        }
        
        # Fallback: Jika harga 0, gunakan data manual terakhir
        fallback_prices = {
            'OIL': {'price': 78.50, 'change': 0.5, 'changePercent': 0.64},
            'BRENT': {'price': 82.30, 'change': 0.3, 'changePercent': 0.37},
            'CPO': {'price': 3850.0, 'change': -25.0, 'changePercent': -0.64},
            'COAL': {'price': 125.50, 'change': 1.2, 'changePercent': 0.96},
            'GOLD': {'price': 2650.0, 'change': 15.0, 'changePercent': 0.57},
            'SILVER': {'price': 31.50, 'change': 0.25, 'changePercent': 0.80},
            'NICKEL': {'price': 16500.0, 'change': -150.0, 'changePercent': -0.90},
            'ALUMINIUM': {'price': 2450.0, 'change': 12.0, 'changePercent': 0.49}
        }
        
        # Cek jika ada yang 0, gunakan fallback
        for key, data in commodities_data.items():
            if data['price'] == 0 or data['price'] is None:
                print(f"⚠️ {key} price is 0, using fallback data")
                commodities_data[key] = fallback_prices[key]
        
        return jsonify(commodities_data)
    except Exception as e:
        print(f"❌ Error fetching commodities: {e}")
        # Return fallback data jika error
        return jsonify({
            'OIL': {'price': 78.50, 'change': 0.5, 'changePercent': 0.64},
            'BRENT': {'price': 82.30, 'change': 0.3, 'changePercent': 0.37},
            'CPO': {'price': 3850.0, 'change': -25.0, 'changePercent': -0.64},
            'COAL': {'price': 125.50, 'change': 1.2, 'changePercent': 0.96},
            'GOLD': {'price': 2650.0, 'change': 15.0, 'changePercent': 0.57},
            'SILVER': {'price': 31.50, 'change': 0.25, 'changePercent': 0.80},
            'NICKEL': {'price': 16500.0, 'change': -150.0, 'changePercent': -0.90},
            'ALUMINIUM': {'price': 2450.0, 'change': 12.0, 'changePercent': 0.49}
        }), 200

def get_yahoo_data(symbol):
    """Helper function untuk ambil data dari Yahoo Finance dengan perhitungan yang lebih akurat"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            'range': '1d', 
            'interval': '1d',
            'includePrePost': 'false'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                result = data['chart']['result'][0]
                meta = result.get('meta', {})
                quotes = result.get('indicators', {}).get('quote', [{}])[0]
                
                current_price = quotes.get('close', [None])[-1]
                previous_close = meta.get('previousClose')
                chart_previous_close = meta.get('chartPreviousClose')
                
                # Gunakan previousClose jika ada, jika tidak gunakan chartPreviousClose
                if previous_close is None or previous_close == 0:
                    previous_close = chart_previous_close
                
                if current_price and current_price > 0:
                    if previous_close and previous_close > 0:
                        change = current_price - previous_close
                        change_percent = (change / previous_close) * 100
                    else:
                        # Fallback: jika tidak ada previous close, set change = 0
                        change = 0
                        change_percent = 0
                    
                    return {
                        'price': round(current_price, 2),
                        'change': round(change, 2),
                        'changePercent': round(change_percent, 2)
                    }
        
        print(f"⚠️ No data for {symbol}")
        return {'price': 0, 'change': 0, 'changePercent': 0}
        
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return {'price': 0, 'change': 0, 'changePercent': 0}

# Tambahkan kode ini untuk mengizinkan server menampilkan gambar background
@app.route('/background.jpg')
def serve_background():
    return send_from_directory('.', 'background.jpg')
if __name__ == '__main__':
    print("=" * 70)
    print(" BANG SUPIR DASHBOARD - FULL GANN ANALYSIS")
    print("=" * 70)
    print("✓ Dashboard: http://localhost:5000")
    print("✓ API: http://localhost:5000/api/stock/BBCA")
    print("=" * 70)
    print("✨ NEW GANN FEATURES:")
    print("  • Gann Fan Lengkap (9 angles)")
    print("  • Gann Square of 9 (Support/Resistance)")
    print("  • Gann Time Cycles (30-540 days)")
    print("=" * 70)
    app.run(debug=False, port=5000, host='0.0.0.0')
