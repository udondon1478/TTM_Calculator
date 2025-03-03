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
        try:
            csv_content = content.decode('utf-8')
        except UnicodeDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error decoding CSV file: {str(e)}. Please ensure the file is UTF-8 encoded."
            )
        
        # Parse CSV
        try:
            df = pd.read_csv(io.StringIO(csv_content))
            logger.info(f"CSV columns found: {', '.join(df.columns)}")  # カラム名をログに出力
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error parsing CSV file: {str(e)}"
            )
        
        # Validate required columns
        required_columns = ['Transaction date', 'Credit amount']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # データの中身を確認
        logger.info(f"First row of data: {df.iloc[0].to_dict()}")
        
        # Process transactions
        transactions = []
        errors = []
        for index, row in df.iterrows():
            try:
                # Parse date with explicit format
                date_str = row['Transaction date']
                logger.info(f"Processing date: {date_str}")
                
                # MM-DD-YYYY形式からYYYY-MM-DD形式に変換
                date_obj = pd.to_datetime(date_str, format='%m-%d-%Y')
                iso_date = date_obj.strftime('%Y-%m-%d')
                logger.info(f"Converted date: {iso_date}")  # 変換後の日付をログ出力
                
                # Get amount in USD
                amount_str = str(row['Credit amount'])
                logger.info(f"Processing amount: {amount_str}")
                
                # 数値に変換する前に不要な文字を削除
                amount_str = amount_str.replace(',', '').replace('$', '').strip()
                amount_usd = float(amount_str)

                # Extract vendor from Description
                description = str(row.get('Description', ''))
                vendor = 'Unknown'
                if 'Payment from ' in description:
                    vendor = description.replace('Payment from ', '').strip()
                
                try:
                    # TTMレート取得を個別にtry-exceptで囲む
                    ttm_rate = get_ttm_rate(iso_date)
                    logger.info(f"TTM rate found for {iso_date}: {ttm_rate}")
                except HTTPException as he:
                    logger.error(f"TTM rate error for {iso_date}: {str(he.detail)}")
                    errors.append(f"Error in row {index + 1}: No TTM rate available for date {iso_date}")
                    continue
                
                # Calculate JPY amount
                amount_jpy = amount_usd * ttm_rate
                
                # Extract month
                month = date_obj.strftime('%Y-%m')
                
                transactions.append({
                    'date': iso_date,
                    'amount_usd': amount_usd,
                    'ttm_rate': ttm_rate,
                    'amount_jpy': amount_jpy,
                    'month': month,
                    'vendor': vendor
                })
            except Exception as e:
                error_msg = f"Error in row {index + 1}: {type(e).__name__} - {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        if errors:
            # エラーが発生した場合は詳細なメッセージを返す
            error_message = f"Error processing CSV: {'; '.join(errors)}"
            logger.error(error_message)
            raise HTTPException(
                status_code=500,
                detail=error_message
            )
        
        # Calculate monthly summaries with vendor transactions
        monthly_data = {}
        
        for transaction in transactions:
            month = transaction['month']
            vendor = transaction['vendor']
            
            if month not in monthly_data:
                monthly_data[month] = {
                    'month': month,
                    'total_usd': 0,
                    'total_jpy': 0,
                    'transaction_count': 0,
                    'vendor_transactions': {}
                }
            
            monthly_data[month]['total_usd'] += transaction['amount_usd']
            monthly_data[month]['total_jpy'] += transaction['amount_jpy']
            monthly_data[month]['transaction_count'] += 1
            
            # Add vendor-specific data
            if vendor not in monthly_data[month]['vendor_transactions']:
                monthly_data[month]['vendor_transactions'][vendor] = {
                    'usd': 0,
                    'jpy': 0,
                    'count': 0
                }
            
            monthly_data[month]['vendor_transactions'][vendor]['usd'] += transaction['amount_usd']
            monthly_data[month]['vendor_transactions'][vendor]['jpy'] += transaction['amount_jpy']
            monthly_data[month]['vendor_transactions'][vendor]['count'] += 1
        
        monthly = list(monthly_data.values())
        
        # Calculate overall summary
        total_usd = sum(transaction['amount_usd'] for transaction in transactions)
        total_jpy = sum(transaction['amount_jpy'] for transaction in transactions)
        
        summary = {
            'totalTransactions': len(transactions),
            'totalUsd': total_usd,
            'totalJpy': total_jpy,
            'averageTtmRate': total_jpy / total_usd if total_usd else 0
        }
        
        return {
            'transactions': transactions,
            'monthly': monthly,
            'summary': summary
        }
    
    except Exception as e:
        # エラーの詳細情報を取得
        error_detail = f"{type(e).__name__}: {str(e)}"
        error_message = f"Error processing CSV: {error_detail}"
        logger.error(error_message)
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

class ExportData(BaseModel):
    results: ProcessResult

@app.post("/api/export/csv")
async def export_csv(data: ExportData):
    """Export processed data as CSV."""
    try:
        # Create CSV for transactions
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Date', 'Month', 'USD Amount', 'TTM Rate', 'JPY Amount'])
        
        # Write transaction data
        for transaction in data.results.transactions:
            writer.writerow([
                transaction['date'],
                transaction['month'],
                transaction['amount_usd'],
                transaction['ttm_rate'],
                transaction['amount_jpy']
            ])
        
        # Write monthly summary
        writer.writerow([])
        writer.writerow(['Monthly Summary'])
        writer.writerow(['Month', 'Total USD', 'Total JPY', 'Transaction Count'])
        
        for month in data.results.monthly:
            writer.writerow([
                month['month'],
                month['total_usd'],
                month['total_jpy'],
                month['transaction_count']
            ])
        
        # Write overall summary
        writer.writerow([])
        writer.writerow(['Overall Summary'])
        writer.writerow([
            'Total Transactions',
            'Total USD',
            'Total JPY',
            'Average TTM Rate'
        ])
        writer.writerow([
            data.results.summary['totalTransactions'],
            data.results.summary['totalUsd'],
            data.results.summary['totalJpy'],
            data.results.summary['averageTtmRate']
        ])
        
        # Prepare response
        output.seek(0)
        
        # Create a temporary file
        temp_file = "temp_export.csv"
        with open(temp_file, "w", newline="") as f:
            f.write(output.getvalue())
        
        return FileResponse(
            temp_file,
            media_type="text/csv",
            filename=f"ttm_conversion_{datetime.now().strftime('%Y%m%d')}.csv"
        )
    
    except Exception as e:
        error_message = f"Error exporting CSV: {str(e)}"
        logger.error(error_message)
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

@app.post("/api/export/pdf")
async def export_pdf(data: ExportData):
    """Export processed data as PDF."""
    try:
        # Create a simple HTML file that will be converted to PDF
        html_content = f"""
        <html>
        <head>
            <title>TTM Conversion Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>TTM Conversion Report</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>Transaction Details</h2>
            <table>
                <tr>
                    <th>Date</th>
                    <th>Month</th>
                    <th>USD Amount</th>
                    <th>TTM Rate</th>
                    <th>JPY Amount</th>
                </tr>
        """
        
        # Add transaction rows
        for transaction in data.results.transactions:
            html_content += f"""
                <tr>
                    <td>{transaction['date']}</td>
                    <td>{transaction['month']}</td>
                    <td>${transaction['amount_usd']:.2f}</td>
                    <td>{transaction['ttm_rate']:.2f}</td>
                    <td>¥{transaction['amount_jpy']:.0f}</td>
                </tr>
            """
        
        html_content += """
            </table>
            
            <h2>Monthly Summary</h2>
            <table>
                <tr>
                    <th>Month</th>
                    <th>Total USD</th>
                    <th>Total JPY</th>
                    <th>Transaction Count</th>
                </tr>
        """
        
        # Add monthly summary rows
        for month in data.results.monthly:
            html_content += f"""
                <tr>
                    <td>{month['month']}</td>
                    <td>${month['total_usd']:.2f}</td>
                    <td>¥{month['total_jpy']:.0f}</td>
                    <td>{month['transaction_count']}</td>
                </tr>
            """
        
        html_content += f"""
            </table>
            
            <h2>Overall Summary</h2>
            <div class="summary">
                <p><strong>Total Transactions:</strong> {data.results.summary['totalTransactions']}</p>
                <p><strong>Total USD:</strong> ${data.results.summary['totalUsd']:.2f}</p>
                <p><strong>Total JPY:</strong> ¥{data.results.summary['totalJpy']:.0f}</p>
                <p><strong>Average TTM Rate:</strong> {data.results.summary['averageTtmRate']:.2f}</p>
            </div>
            
            <p><em>This report was generated by the TTM Rate Conversion Application.</em></p>
        </body>
        </html>
        """
        
        # Save HTML to a temporary file
        temp_html = "temp_export.html"
        with open(temp_html, "w") as f:
            f.write(html_content)
        
        # For simplicity, we'll return the HTML file instead of converting to PDF
        # In a real application, you would use a library like WeasyPrint or wkhtmltopdf
        # to convert HTML to PDF
        
        return FileResponse(
            temp_html,
            media_type="text/html",
            filename=f"ttm_conversion_{datetime.now().strftime('%Y%m%d')}.html"
        )
    
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error exporting PDF: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Run tasks on application startup."""
    # Initialize database
    init_db()
    
    # Check if we need to fetch TTM data
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ttm_rates")
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        logger.info("No TTM data found, fetching initial data")
        fetch_ttm_data()

@app.on_event("shutdown")
async def shutdown_event():
    """Run tasks on application shutdown."""
    # Shut down the scheduler
    scheduler.shutdown()
    logger.info("Application shutting down")

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)