import React from 'react';

export const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();
  
  return (
    <footer className="bg-white dark:bg-gray-800 shadow-inner mt-auto">
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            &copy; {currentYear} TTMレート換算アプリ - 確定申告用
          </p>
          <div className="mt-4 md:mt-0">
            <p className="text-xs text-gray-500 dark:text-gray-500">
              みずほ銀行のTTMレートを使用して換算しています。
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};