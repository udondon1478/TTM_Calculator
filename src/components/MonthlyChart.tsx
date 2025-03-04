import React, { useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  PointElement,
  LineElement,
} from 'chart.js';
import { Chart } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface MonthlyData {
  month: string;          // 月（例：'2024-01'）
  total_usd: number;      // USD合計
  total_jpy: number;      // JPY合計
  total_debit_usd: number; // 出金額USD合計
  total_debit_jpy: number; // 出金額JPY合計
  transaction_count: number; // 取引数
  vendor_transactions: {
    [vendor: string]: {
      usd: number;
      jpy: number;
      debit_usd: number;
      debit_jpy: number;
      count: number;
    };
  };
}

interface MonthlyChartProps {
  data: {
    monthly: MonthlyData[];  // MonthlyDataの配列
  };
}

export const MonthlyChart: React.FC<MonthlyChartProps> = ({ data }) => {
  const [chartType, setChartType] = useState<'summary' | 'vendors' | 'profit'>('summary');

  // Sort months chronologically
  const sortedMonthly = [...data.monthly].sort((a, b) => {
    const [aYear, aMonth] = a.month.split('-').map(Number);
    const [bYear, bMonth] = b.month.split('-').map(Number);
    
    if (aYear !== bYear) return aYear - bYear;
    return aMonth - bMonth;
  });

  const months = sortedMonthly.map((item) => item.month);
  const jpyValues = sortedMonthly.map((item) => item.total_jpy);
  const usdValues = sortedMonthly.map((item) => item.total_usd);
  const debitJpyValues = sortedMonthly.map((item) => item.total_debit_jpy);
  const debitUsdValues = sortedMonthly.map((item) => item.total_debit_usd);
  const transactionCounts = sortedMonthly.map((item) => item.transaction_count);

  // Calculate monthly profits
  const profitUsdValues = sortedMonthly.map((item) => item.total_usd - item.total_debit_usd);
  const profitJpyValues = sortedMonthly.map((item) => item.total_jpy - item.total_debit_jpy);

  // Get unique vendors and generate colors for them
  const vendors = Array.from(new Set(
    sortedMonthly.flatMap(month => 
      Object.keys(month.vendor_transactions || {})
    )
  ));

  const vendorColors = vendors.reduce((acc, vendor, index) => {
    const hue = (index * 137.5) % 360;  // Golden ratio to distribute colors
    acc[vendor] = {
      line: `hsla(${hue}, 70%, 50%, 1)`,
      fill: `hsla(${hue}, 70%, 50%, 0.1)`
    };
    return acc;
  }, {} as { [key: string]: { line: string; fill: string } });

  const summaryChartData = {
    labels: months,
    datasets: [
      {
        type: 'bar' as const,
        label: '入金額(JPY)',
        data: jpyValues,
        backgroundColor: 'rgba(54, 162, 235, 0.5)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
        yAxisID: 'y',
      },
      {
        type: 'bar' as const,
        label: '出金額(JPY)',
        data: debitJpyValues,
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
        borderColor: 'rgba(255, 99, 132, 1)',
        borderWidth: 1,
        yAxisID: 'y',
      },
      {
        type: 'bar' as const,
        label: '入金額(USD)',
        data: usdValues,
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
        yAxisID: 'y1',
      },
      {
        type: 'bar' as const,
        label: '出金額(USD)',
        data: debitUsdValues,
        backgroundColor: 'rgba(255, 159, 64, 0.5)',
        borderColor: 'rgba(255, 159, 64, 1)',
        borderWidth: 1,
        yAxisID: 'y1',
      },
      {
        type: 'line' as const,
        label: '取引数',
        data: transactionCounts,
        backgroundColor: 'rgba(153, 102, 255, 0.5)',
        borderColor: 'rgba(153, 102, 255, 1)',
        borderWidth: 1,
        yAxisID: 'y2',
      },
    ],
  };

  const profitChartData = {
    labels: months,
    datasets: [
      {
        type: 'bar' as const,
        label: '利益(JPY)',
        data: profitJpyValues,
        backgroundColor: profitJpyValues.map(value => 
          value >= 0 ? 'rgba(75, 192, 192, 0.5)' : 'rgba(255, 99, 132, 0.5)'
        ),
        borderColor: profitJpyValues.map(value => 
          value >= 0 ? 'rgba(75, 192, 192, 1)' : 'rgba(255, 99, 132, 1)'
        ),
        borderWidth: 1,
        yAxisID: 'y',
      },
      {
        type: 'bar' as const,
        label: '利益(USD)',
        data: profitUsdValues,
        backgroundColor: profitUsdValues.map(value => 
          value >= 0 ? 'rgba(54, 162, 235, 0.5)' : 'rgba(255, 159, 64, 0.5)'
        ),
        borderColor: profitUsdValues.map(value => 
          value >= 0 ? 'rgba(54, 162, 235, 1)' : 'rgba(255, 159, 64, 1)'
        ),
        borderWidth: 1,
        yAxisID: 'y1',
      },
    ],
  };

  const vendorChartData = {
    labels: months,
    datasets: vendors.map(vendor => ({
      label: vendor,
      data: sortedMonthly.map(month => 
        month.vendor_transactions?.[vendor]?.usd || 0
      ),
      borderColor: vendorColors[vendor].line,
      backgroundColor: vendorColors[vendor].fill,
      borderWidth: 2,
      tension: 0.3,
      fill: false,
      pointRadius: 4,
      pointHoverRadius: 6,
    })),
  };

  const summaryOptions = {
    responsive: true,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    scales: {
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: 'JPY (円)',
        },
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: 'USD ($)',
        },
      },
      y2: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: '取引数',
        },
      },
    },
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: '月別収支集計',
      },
    },
  };

  const profitOptions = {
    responsive: true,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    scales: {
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: 'JPY (円)',
        },
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: 'USD ($)',
        },
      },
    },
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: '月別利益集計',
      },
    },
  };

  const vendorOptions = {
    responsive: true,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    scales: {
      x: {
        title: {
          display: true,
          text: '月',
        },
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: 'USD ($)',
        },
        stacked: false,
        min: 0,
        ticks: {
          callback: function(tickValue: number | string) {
            if (typeof tickValue === 'number') {
              return `$${tickValue}`;
            }
            return tickValue;
          }
        }
      },
    },
    plugins: {
      legend: {
        position: 'top' as const,
        onClick: function(e: any, legendItem: any, legend: any) {
          const index = legendItem.datasetIndex;
          const ci = legend.chart;
          const meta = ci.getDatasetMeta(index);

          meta.hidden = meta.hidden === null ? !ci.data.datasets[index].hidden : null;
          ci.update();
        },
      },
      title: {
        display: true,
        text: '取引先別月次推移 (USD)',
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            const value = context.parsed.y;
            return `${context.dataset.label}: $${value.toFixed(2)}`;
          }
        }
      }
    },
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-center space-x-4">
        <button
          onClick={() => setChartType('summary')}
          className={`px-4 py-2 rounded ${
            chartType === 'summary'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-200 dark:bg-gray-700'
          }`}
        >
          収支概要
        </button>
        <button
          onClick={() => setChartType('profit')}
          className={`px-4 py-2 rounded ${
            chartType === 'profit'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-200 dark:bg-gray-700'
          }`}
        >
          利益推移
        </button>
        <button
          onClick={() => setChartType('vendors')}
          className={`px-4 py-2 rounded ${
            chartType === 'vendors'
              ? 'bg-blue-500 text-white'
              : 'bg-gray-200 dark:bg-gray-700'
          }`}
        >
          取引先別
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
        {chartType === 'summary' && (
          <Chart type="bar" data={summaryChartData} options={summaryOptions} />
        )}
        {chartType === 'profit' && (
          <Chart type="bar" data={profitChartData} options={profitOptions} />
        )}
        {chartType === 'vendors' && (
          <Chart type="line" data={vendorChartData} options={vendorOptions} />
        )}
      </div>
    </div>
  );
};