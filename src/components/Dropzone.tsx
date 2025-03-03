import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload } from 'lucide-react';

interface DropzoneProps {
  onDrop: (acceptedFiles: File[]) => void;
  disabled?: boolean;
}

export const Dropzone: React.FC<DropzoneProps> = ({ onDrop, disabled = false }) => {
  const handleDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (disabled) return;
      onDrop(acceptedFiles);
    },
    [onDrop, disabled]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleDrop,
    accept: {
      'text/csv': ['.csv'],
    },
    maxFiles: 1,
    disabled,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        isDragActive
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center">
        <Upload
          size={48}
          className="text-gray-400 dark:text-gray-500 mb-4"
        />
        <p className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
          CSVファイルをドラッグ&ドロップ
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          または、クリックしてファイルを選択
        </p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
          取引履歴のCSVファイルをアップロードしてください
        </p>
      </div>
    </div>
  );
};