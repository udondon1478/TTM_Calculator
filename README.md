# TTM Rate Conversion Application for Tax Filing

[日本語のREADME](README.ja.md)

This application helps with tax filing by automatically converting USD transactions to JPY using Mizuho Bank's TTM (Telegraphic Transfer Middle) rates.

## Features

- **TTM Data Auto-Fetching**: Automatically retrieves and stores Mizuho Bank's exchange rates
- **CSV Upload & Processing**: Upload transaction history CSV files for automatic conversion
- **Analysis & Reporting**: View monthly and annual income summaries
- **Export Options**: Export results as CSV or HTML/PDF
- **Dark Mode Support**: Toggle between light and dark themes

## CSV Format Requirements

This web application is designed to import CSV files exported from Payoneer.

The application expects CSV files with at least the following columns:
- `Transaction Date`: Transaction date (in a format parseable by pandas)
- `Credit amount`: Transaction amount in USD

## Tech Stack

### Frontend
- React
- TypeScript
- Tailwind CSS
- Chart.js for data visualization
- Lucide React for icons

### Backend
- Python with FastAPI
- Pandas for data processing
- SQLite for data storage
- APScheduler for background tasks

## Getting Started

### Prerequisites
- Node.js
- Python 3.8+
- npm or yarn

### Installation

1. Clone the repository
2. Install frontend dependencies:
   ```
   npm install
   ```
3. Install backend dependencies:
   ```
   cd api
   pip install -r requirements.txt
   ```

### Running the Application

1. Start the backend server:
   ```
   cd api
   python main.py
   ```

2. Start the frontend development server:
   ```
   npm run dev
   ```

3. Open your browser and navigate to `http://localhost:5173`

## License

This project is for personal use.