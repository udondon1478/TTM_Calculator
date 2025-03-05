import React, { useState, useEffect } from 'react';
import { Dropzone } from './components/Dropzone';
import { ResultsTable } from './components/ResultsTable';
import { MonthlyChart } from './components/MonthlyChart';
import { Tabs } from './components/Tabs';
import { Loader } from './components/Loader';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { Toaster } from 'react-hot-toast';
import { toast } from 'react-hot-toast';
import axios from 'axios';
import { Download, RefreshCw } from 'lucide-react';

function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [activeTab, setActiveTab] = useState('table');
  const [ttmStatus, setTtmStatus] = useState({ lastUpdated: null, status: 'unknown' });

  useEffect(() => {
    // Check TTM data status on load
    checkTtmStatus();
  }, []);

  const checkTtmStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/ttm/status');
      setTtmStatus(response.data);
    } catch (error) {
      // Safely log error
      console.log('Failed to check TTM status:', error?.response?.data?.detail || 'Unknown error');
      toast.error('TTMデータの状態確認に失敗しました');
    }
  };

  const refreshTtmData = async () => {
    try {
      setIsLoading(true);
      const response = await axios.post('http://localhost:8000/api/ttm/refresh');
      setTtmStatus(response.data);
      toast.success('TTMデータが更新されました');
    } catch (error) {
      // Safely log error
      console.log('Failed to refresh TTM data:', error?.response?.data?.detail || 'Unknown error');
      toast.error('TTMデータの更新に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (files) => {
    if (files.length === 0) return;
    
    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      setIsLoading(true);
      const response = await axios.post('http://localhost:8000/api/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setResults(response.data);
      toast.success('データ処理が完了しました');
    } catch (error) {
      // Safely log error
      console.log('Upload failed:', error?.response?.data?.detail || 'Unknown error');
      const errorMessage = error.response?.data?.detail || 'ファイルのアップロードに失敗しました';
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const exportCsv = () => {
    if (!results) return;
    
    try {
      axios({
        url: 'http://localhost:8000/api/export/csv',
        method: 'POST',
        data: { results },
        responseType: 'blob'
      }).then((response) => {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `ttm_conversion_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      });
    } catch (error) {
      // Safely log error
      console.log('Export failed:', error?.response?.data?.detail || 'Unknown error');
      toast.error('CSVエクスポートに失敗しました');
    }
  };

  const exportPdf = () => {
    if (!results) return;
    
    try {
      axios({
        url: 'http://localhost:8000/api/export/pdf',
        method: 'POST',
        data: { results },
        responseType: 'blob'
      }).then((response) => {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `ttm_conversion_${new Date().toISOString().split('T')[0]}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      });
    } catch (error) {
      // Safely log error
      console.log('Export failed:', error?.response?.data?.detail || 'Unknown error');
      toast.error('PDFエクスポートに失敗しました');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      <Toaster position="top-right" />
      <Header />
      
      <main className="flex-grow container mx-auto px-4 py-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6">
            <div>
              <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-2">TTMレートデータ</h2>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                最終更新: {ttmStatus.lastUpdated ? new Date(ttmStatus.lastUpdated).toLocaleString('ja-JP') : '未取得'}
              </p>
            </div>
            <button
              onClick={refreshTtmData}
              disabled={isLoading}
              className="mt-4 md:mt-0 flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:bg-blue-400"
            >
              <RefreshCw size={18} className="mr-2" />
              TTMデータを更新
            </button>
          </div>
          
          <Dropzone onDrop={handleFileUpload} disabled={isLoading} />
        </div>

        {isLoading && (
          <div className="flex justify-center my-12">
            <Loader />
          </div>
        )}

        {results && !isLoading && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-gray-800 dark:text-white">処理結果</h2>
              <div className="flex space-x-2">
                <button
                  onClick={exportCsv}
                  className="flex items-center px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                >
                  <Download size={16} className="mr-2" />
                  CSV
                </button>
                <button
                  onClick={exportPdf}
                  className="flex items-center px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                >
                  <Download size={16} className="mr-2" />
                  PDF
                </button>
              </div>
            </div>

            <Tabs activeTab={activeTab} setActiveTab={setActiveTab} />

            <div className="mt-6">
              {activeTab === 'table' && <ResultsTable data={results} />}
              {activeTab === 'chart' && <MonthlyChart data={results} />}
            </div>

            <div className="mt-8 p-4 bg-gray-100 dark:bg-gray-700 rounded-md">
              <h3 className="text-lg font-medium text-gray-800 dark:text-white mb-4">年間集計</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div className="bg-white dark:bg-gray-800 p-4 rounded-md shadow">
                  <h4 className="text-md font-medium text-gray-700 dark:text-gray-300 mb-3">取引数</h4>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">総取引数</p>
                      <p className="text-xl font-bold">{results?.summary?.totalTransactions || 0}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">入金</p>
                      <p className="text-xl font-bold text-green-600">{results?.summary?.creditTransactions || 0}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">出金</p>
                      <p className="text-xl font-bold text-red-600">{results?.summary?.debitTransactions || 0}</p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-white dark:bg-gray-800 p-4 rounded-md shadow">
                  <h4 className="text-md font-medium text-gray-700 dark:text-gray-300 mb-3">為替レート</h4>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">平均TTMレート</p>
                    <p className="text-xl font-bold">{results?.summary?.averageTtmRate?.toFixed(2) || 0}</p>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white dark:bg-gray-800 p-4 rounded-md shadow">
                  <h4 className="text-md font-medium text-gray-700 dark:text-gray-300 mb-3">入金額</h4>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">USD合計</p>
                      <p className="text-xl font-bold text-green-600">${results?.summary?.totalCreditUsd?.toFixed(2) || 0}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">JPY合計</p>
                      <p className="text-xl font-bold text-green-600">¥{results?.summary?.totalCreditJpy?.toLocaleString() || 0}</p>
                    </div>
                  </div>
                </div>
                
                <div className="bg-white dark:bg-gray-800 p-4 rounded-md shadow">
                  <h4 className="text-md font-medium text-gray-700 dark:text-gray-300 mb-3">出金額</h4>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">USD合計</p>
                      <p className="text-xl font-bold text-red-600">${results?.summary?.totalDebitUsd?.toFixed(2) || 0}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">JPY合計</p>
                      <p className="text-xl font-bold text-red-600">¥{results?.summary?.totalDebitJpy?.toLocaleString() || 0}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-4">
                <div className="bg-white dark:bg-gray-800 p-4 rounded-md shadow">
                  <h4 className="text-md font-medium text-gray-700 dark:text-gray-300 mb-3">為替差損益</h4>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">年間合計</p>
                    <p className={`text-xl font-bold ${
                      (results?.summary?.totalExchangeProfit || 0) >= 0
                        ? 'text-green-600'
                        : 'text-red-600'
                    }`}>
                      ¥{(results?.summary?.totalExchangeProfit || 0).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
      
      <Footer />
    </div>
  );
}

export default App;