'use client';

import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

interface FileWithPreview extends File {
  preview?: string;
}

const DocumentUploader = () => {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const { token, isAuthenticated } = useAuth();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Filter accepted file types
    const validFiles = acceptedFiles.filter(file => {
      const ext = file.name.split('.').pop()?.toLowerCase();
      return ['pdf', 'txt', 'md', 'markdown', 'docx'].includes(ext || '');
    });

    if (validFiles.length !== acceptedFiles.length) {
      toast.warning(`${acceptedFiles.length - validFiles.length} unsupported file(s) were rejected`);
    }

    setFiles(prev => [...prev, ...validFiles.map(file => Object.assign(file, {
      preview: URL.createObjectURL(file)
    }))]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md', '.markdown'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  const removeFile = (index: number) => {
    setFiles(prev => {
      const newFiles = [...prev];
      newFiles.splice(index, 1);
      return newFiles;
    });
  };

  const uploadFiles = async () => {
    if (files.length === 0) return;

    setIsUploading(true);
    setUploadStatus('uploading');
    setUploadProgress(0);

    try {
      // Simulate upload progress
      for (let i = 0; i <= 100; i += 10) {
        await new Promise(resolve => setTimeout(resolve, 100));
        setUploadProgress(i);
      }

      // Here you would actually upload the files to your backend
      // For now, we'll simulate the API call
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });

      const response = await fetch('/api/rag/upload-and-index', {
        method: 'POST',
        body: formData,
        // Don't include Content-Type — the browser sets the FormData boundary
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      setUploadStatus('success');
      toast.success(`Successfully processed ${result.indexed_count} documents`);

      // Clear files after successful upload
      setFiles([]);

      // Reset progress after a delay
      setTimeout(() => {
        setUploadProgress(null);
        setUploadStatus('idle');
        setIsUploading(false);
      }, 2000);

    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus('error');
      toast.error('Failed to upload documents. Please try again.');
      setIsUploading(false);
      setUploadProgress(null);
    }
  };

  const supportedFormats = [
    { ext: '.pdf', desc: 'PDF Documents' },
    { ext: '.txt', desc: 'Plain Text Files' },
    { ext: '.md', desc: 'Markdown Files' },
    { ext: '.docx', desc: 'Word Documents' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Document Upload</CardTitle>
        <CardDescription>
          Upload documents to enable AI-powered search and analysis
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-primary bg-primary/5'
              : 'border-gray-300 hover:border-primary'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-3" />
          <p className="text-lg font-medium mb-1">
            {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
          </p>
          <p className="text-sm text-muted-foreground mb-4">
            or click to browse
          </p>
          <p className="text-xs text-muted-foreground">
            Supported formats: PDF, TXT, MD, DOCX (Max 10MB per file)
          </p>
        </div>

        {/* Selected files list */}
        {files.length > 0 && (
          <div className="mt-6 space-y-3">
            <h3 className="font-medium">Selected Files ({files.length})</h3>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {files.map((file, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-secondary rounded-md">
                  <div className="flex items-center gap-2">
                    <File className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm truncate max-w-xs">{file.name}</span>
                    <Badge variant="secondary" className="text-xs">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </Badge>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(index)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upload progress */}
        {uploadProgress !== null && (
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span>
                {uploadStatus === 'uploading' && 'Uploading...'}
                {uploadStatus === 'success' && 'Success!'}
                {uploadStatus === 'error' && 'Error occurred'}
              </span>
              <span>{uploadProgress}%</span>
            </div>
            <Progress value={uploadProgress} className="w-full" />

            {uploadStatus === 'success' && (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-4 w-4" />
                <span>Documents processed successfully!</span>
              </div>
            )}

            {uploadStatus === 'error' && (
              <div className="flex items-center gap-2 text-red-600">
                <AlertCircle className="h-4 w-4" />
                <span>Upload failed. Please try again.</span>
              </div>
            )}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex flex-wrap gap-3 mt-6">
          <Button
            onClick={uploadFiles}
            disabled={files.length === 0 || isUploading || !isAuthenticated}
            className="flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            {isUploading ? 'Processing...' : 'Upload & Process'}
          </Button>

          <Button
            variant="outline"
            onClick={() => setFiles([])}
            disabled={files.length === 0 || isUploading}
          >
            Clear All
          </Button>
        </div>

        {/* Supported formats */}
        <div className="mt-6 pt-4 border-t">
          <h4 className="font-medium mb-2">Supported Formats</h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
            {supportedFormats.map((format, index) => (
              <Badge key={index} variant="secondary" className="justify-center">
                {format.ext}
              </Badge>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default DocumentUploader;