from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import pandas as pd
import requests
import sqlite3
import os
import csv
import json
from datetime import datetime, timedelta
import io
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(title="TTM Rate Conversion API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify the actual origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_PATH = "ttm_data.db"

def init_db():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create TTM rates table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ttm_rates (
        date TEXT PRIMARY KEY,
        rate REAL NOT NULL
    )
    ''')
    
    # Create status table to track last update
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS status (
        id INTEGER PRIMARY KEY,
        last_updated TEXT,
        status TEXT
    )
    ''')
    
    # Insert initial status if not exists
    cursor.execute('''
    INSERT OR IGNORE INTO status (id, last_updated, status)
    VALUES (1, NULL, 'initial')
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

# Initialize database on startup
init_db()

# TTM data fetching
MIZUHO_URL = "https://www.mizuhobank.co.jp/market/quote.csv"

def fetch_ttm_data():
    """Fetch TTM rate data from Mizuho Bank."""
    try:
        logger.info("Fetching TTM data from Mizuho Bank")
        response = requests.get(MIZUHO_URL)
        response.raise_for_status()
        
        # Handle encoding issues with shift-jis
        content = response.content.decode('shift_jis', errors='ignore')
        logger.info("Successfully decoded content with shift-jis encoding")
        
        # Parse CSV data
        csv_data = list(csv.reader(io.StringIO(content)))
        logger.info(f"CSV data rows: {len(csv_data)}")
        
        # Extract USD/JPY TTM rate
        ttm_data = []
        
        # Find USD row index and column index
        usd_row_index = None
        ttm_column_index = None
        
        # CSVの構造を確認するためにデータをログ出力
        for i, row in enumerate(csv_data):
            logger.info(f"Row {i}: {row}")
            if len(row) > 1 and '米ドル' in row:
                usd_row_index = i
                # '米ドル'が見つかった列のインデックスを保存
                for j, cell in enumerate(row):
                    if '米ドル' in cell:
                        # TTMレートは'米ドル'と同じ列にある
                        ttm_column_index = j
                        logger.info(f"Found '米ドル' at row {i}, column {j}")
                        break
                break
        
        if usd_row_index is None or ttm_column_index is None:
            logger.error("Could not find USD data in CSV")
            return {"status": "error", "message": "USD data not found in CSV"}
        
        # Process USD data (assuming it's in the next rows)
        for i in range(usd_row_index + 1, len(csv_data)):
            row = csv_data[i]
            if not row or len(row) <= ttm_column_index:  # 必要な列が存在することを確認
                continue
                
            try:
                # 日付はカラム{0}から取得
                date_str = row[0]
                if not date_str:  # 日付が空の場合はスキップ
                    continue
                
                logger.info(f"Processing date string: {date_str}")
                
                # みずほ銀行の日付形式（YYYY/M/D）を解析
                try:
                    date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                    date_iso = date_obj.strftime('%Y-%m-%d')
                    logger.info(f"Converted date from {date_str} to {date_iso}")
                except ValueError as e:
                    logger.error(f"Error parsing date {date_str}: {e}")
                    continue
                
                # TTMレートの処理（'米ドル'と同じ列から取得）
                try:
                    ttm_str = row[ttm_column_index]
                    if ttm_str and ttm_str.strip():  # TTMレートが存在し、空でないことを確認
                        ttm_rate = float(ttm_str.replace(',', ''))
                        logger.info(f"Found rate: {ttm_rate} for date {date_iso} in column {ttm_column_index}")
                        ttm_data.append((date_iso, ttm_rate))
                    else:
                        logger.warning(f"No TTM rate found in row: {row}")
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing TTM rate in row {row}: {e}")
                    continue
                
            except Exception as e:
                logger.error(f"Error processing row {row}: {e}")
                continue
        
        if not ttm_data:
            logger.error("No valid TTM data found")
            return {"status": "error", "message": "No valid TTM data found"}
        
        # Update database with new data
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for date_iso, rate in ttm_data:
            cursor.execute(
                "INSERT OR REPLACE INTO ttm_rates (date, rate) VALUES (?, ?)",
                (date_iso, rate)
            )
        
        # Update status
        cursor.execute(
            "UPDATE status SET last_updated = ?, status = ? WHERE id = 1",
            (datetime.now().isoformat(), "success")
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"TTM data updated successfully with {len(ttm_data)} entries")
        return {"status": "success", "count": len(ttm_data)}
        
    except Exception as e:
        logger.error(f"Error fetching TTM data: {e}")
        
        # Update status to error
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE status SET last_updated = ?, status = ? WHERE id = 1",
            (datetime.now().isoformat(), f"error: {str(e)}")
        )
        conn.commit()
        conn.close()
        
        return {"status": "error", "message": str(e)}

# Set up scheduler for daily TTM data updates
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_ttm_data, 'cron', hour=9, minute=0)  # Run daily at 9:00 AM
scheduler.start()

# API endpoints
@app.get("/api/ttm/status")
async def get_ttm_status():
    """Get the status of TTM data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT last_updated, status FROM status WHERE id = 1")
    result = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) FROM ttm_rates")
    count = cursor.fetchone()[0]
    
    conn.close()
    
    if result:
        last_updated, status = result
        return {
            "lastUpdated": last_updated,
            "status": status,
            "count": count
        }
    else:
        return {
            "lastUpdated": None,
            "status": "unknown",
            "count": 0
        }

@app.post("/api/ttm/refresh")
async def refresh_ttm_data(background_tasks: BackgroundTasks):
    """Manually refresh TTM data."""
    result = fetch_ttm_data()
    
    # Get updated status
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT last_updated, status FROM status WHERE id = 1")
    status_result = cursor.fetchone()
    conn.close()
    
    if status_result:
        last_updated, status = status_result
        return {
            "lastUpdated": last_updated,
            "status": status,
            "message": "TTM data refresh completed"
        }
    else:
        return {
            "lastUpdated": None,
            "status": "unknown",
            "message": "TTM data refresh attempted but status unknown"
        }

def get_ttm_rate(date_str):
    """Get TTM rate for a specific date, with fallback to nearest available date."""
    try:
        # 日付が既にYYYY-MM-DD形式の場合はそのまま使用
        if '-' in date_str and len(date_str.split('-')) == 3:
            iso_date = date_str
            logger.info(f"Date is already in ISO format: {iso_date}")
        else:
            # MM-DD-YYYY形式からの変換が必要な場合
            date_obj = datetime.strptime(date_str, '%m-%d-%Y')
            iso_date = date_obj.strftime('%Y-%m-%d')
            logger.info(f"Converting input date from {date_str} to {iso_date}")
    except ValueError as e:
        logger.error(f"Error converting date format: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD or MM-DD-YYYY"
        )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Try to get exact date match
    cursor.execute("SELECT rate FROM ttm_rates WHERE date = ?", (iso_date,))
    result = cursor.fetchone()
    
    if result:
        logger.info(f"Found exact match for date {iso_date}")
        conn.close()
        return result[0]
    
    # If no exact match, find the closest previous date
    cursor.execute(
        "SELECT date, rate FROM ttm_rates WHERE date <= ? ORDER BY date DESC LIMIT 1",
        (iso_date,)
    )
    result = cursor.fetchone()
    
    if result:
        found_date, rate = result
        logger.info(f"Using fallback TTM rate {rate} from {found_date} for {iso_date}")
        conn.close()
        return rate
    
    # If no previous date, find the closest future date
    cursor.execute(
        "SELECT date, rate FROM ttm_rates WHERE date >= ? ORDER BY date ASC LIMIT 1",
        (iso_date,)
    )
    result = cursor.fetchone()
    
    if result:
        found_date, rate = result
        logger.info(f"Using fallback TTM rate {rate} from {found_date} for {iso_date}")
        conn.close()
        return rate
    
    # If no data at all, raise an exception
    conn.close()
    raise HTTPException(
        status_code=404,
        detail=f"No TTM rate available for date {iso_date} or nearby dates"
    )

class ProcessResult(BaseModel):
    transactions: List[Dict[str, Any]]
    monthly: List[Dict[str, Any]]
    summary: Dict[str, Any]

@app.post("/api/process")
async def process_csv(file: UploadFile):
    """Process a CSV file with transaction data."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    try:
        # Read CSV content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Parse CSV using pandas
        df = pd.read_csv(io.StringIO(csv_content))
        
        # Log the DataFrame columns for debugging
        logger.info(f"CSV columns: {df.columns.tolist()}")
        
        # Validate required columns
        required_columns = ['Transaction date', 'Credit amount', 'Debit amount', 'Description']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            error_msg = f"Missing required columns: {', '.join(missing_columns)}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Log sample data for debugging
        logger.info(f"Sample data:\n{df.head()}")
        
        # Convert date format and sort by date
        try:
            df['Transaction date'] = pd.to_datetime(df['Transaction date'])
            df = df.sort_values('Transaction date')
        except Exception as e:
            error_msg = f"Error converting dates: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Initialize lists for processed data
        transactions = []
        monthly_data = {}
        last_debit_date = None
        accumulated_credit = 0
        accumulated_credit_jpy = 0
        
        # Process each transaction
        for index, row in df.iterrows():
            try:
                date = row['Transaction date'].strftime('%Y-%m-%d')
                ttm_rate = get_ttm_rate(date)
                
                # Determine if this is a credit or debit transaction
                credit_amount = row['Credit amount'] if pd.notna(row['Credit amount']) else 0
                debit_amount = row['Debit amount'] if pd.notna(row['Debit amount']) else 0
                
                # Log transaction details for debugging
                logger.info(f"Processing row {index}: Date={date}, Credit={credit_amount}, Debit={debit_amount}")
                
                # Calculate JPY amounts (rounded to nearest integer)
                credit_amount_jpy = round(credit_amount * ttm_rate)
                debit_amount_jpy = round(debit_amount * ttm_rate)
                
                # Determine transaction type
                transaction_type = 'credit' if credit_amount > 0 else 'debit'
                amount_usd = credit_amount if transaction_type == 'credit' else debit_amount
                amount_jpy = credit_amount_jpy if transaction_type == 'credit' else debit_amount_jpy
                
                # Calculate profit since last debit (for debit transactions)
                profit_since_last_debit = None
                if transaction_type == 'debit':
                    profit_since_last_debit = {
                        'from_date': last_debit_date,
                        'to_date': date,
                        'profit_usd': accumulated_credit - debit_amount,
                        'profit_jpy': accumulated_credit_jpy - debit_amount_jpy
                    }
                    last_debit_date = date
                    accumulated_credit = 0
                    accumulated_credit_jpy = 0
                else:
                    accumulated_credit += credit_amount
                    accumulated_credit_jpy += credit_amount_jpy
                
                # Create transaction record
                transaction = {
                    'date': date,
                    'vendor': row['Description'],
                    'type': transaction_type,
                    'amount_usd': amount_usd,
                    'ttm_rate': ttm_rate,
                    'amount_jpy': amount_jpy,
                    'profit_since_last_debit': profit_since_last_debit
                }
                transactions.append(transaction)
                
                # Update monthly data
                month = row['Transaction date'].strftime('%Y-%m')
                if month not in monthly_data:
                    monthly_data[month] = {
                        'month': month,
                        'total_usd': 0,
                        'total_jpy': 0,
                        'transaction_count': 0,
                        'vendor_transactions': {}
                    }
                
                monthly_data[month]['total_usd'] += amount_usd
                monthly_data[month]['total_jpy'] += amount_jpy
                monthly_data[month]['transaction_count'] += 1
                
                # Update vendor transactions in monthly data
                vendor = row['Description']
                if vendor not in monthly_data[month]['vendor_transactions']:
                    monthly_data[month]['vendor_transactions'][vendor] = {
                        'usd': 0,
                        'jpy': 0,
                        'count': 0
                    }
                monthly_data[month]['vendor_transactions'][vendor]['usd'] += amount_usd
                monthly_data[month]['vendor_transactions'][vendor]['jpy'] += amount_jpy
                monthly_data[month]['vendor_transactions'][vendor]['count'] += 1
                
            except Exception as e:
                error_msg = f"Error processing row {index}: {str(e)}"
                logger.error(error_msg)
                raise HTTPException(status_code=400, detail=error_msg)
        
        # Calculate summary
        try:
            credit_transactions = [t for t in transactions if t['type'] == 'credit']
            debit_transactions = [t for t in transactions if t['type'] == 'debit']
            
            total_credit_usd = sum(t['amount_usd'] for t in credit_transactions)
            total_credit_jpy = sum(t['amount_jpy'] for t in credit_transactions)
            total_debit_usd = sum(t['amount_usd'] for t in debit_transactions)
            total_debit_jpy = sum(t['amount_jpy'] for t in debit_transactions)
            
            summary = {
                'totalTransactions': len(transactions),
                'creditTransactions': len(credit_transactions),
                'debitTransactions': len(debit_transactions),
                'totalCreditUsd': total_credit_usd,
                'totalCreditJpy': total_credit_jpy,
                'totalDebitUsd': total_debit_usd,
                'totalDebitJpy': total_debit_jpy,
                'netUsd': total_credit_usd - total_debit_usd,
                'netJpy': total_credit_jpy - total_debit_jpy,
                'averageTtmRate': sum(t['ttm_rate'] for t in transactions) / len(transactions)
            }
            
            return {
                'transactions': transactions,
                'monthly': list(monthly_data.values()),
                'summary': summary
            }
            
        except Exception as e:
            error_msg = f"Error calculating summary: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
    except Exception as e:
        error_msg = f"Error processing CSV: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)