import React, { useEffect, useRef, useState } from 'react';
import {
  FilePreviewPluginManager,
  FilePreviewPluginContext,
  FilePreviewPluginAPI,
} from '@/components/features/chat/preview/preview-content/file-preview-plugin-manager';
import { LoaderIcon } from 'lucide-react';

interface FilePreviewContainerProps {
  fileContent: string;
  fileType: string;
  fileName: string;
  pluginManager: FilePreviewPluginManager;
}

export const FilePreviewContainer: React.FC<FilePreviewContainerProps> = ({ fileContent, fileType, fileName, pluginManager }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadPlugin = async () => {
      if (!containerRef.current) return;

      setIsLoading(true);
      setError(null);

      try {
        const plugin = pluginManager.getPluginForFileType(fileType);
        if (!plugin) {
          setError(`没有找到支持${fileType}文件类型的插件`);
          return;
        }

        const context: FilePreviewPluginContext = {
          fileContent,
          fileType,
          fileName,
          container: containerRef.current,
          api: createPluginAPI(containerRef.current),
        };

        // 获取插件全局变量名称
        const pluginName = plugin.name;

        // 特别处理HTML插件，因为它使用了不同的名称约定
        const pluginInstance = (pluginName === 'html-viewer')
          ? (window as any)['HTMLViewer']
          : (window as any)[pluginName];

        if (typeof pluginInstance?.render !== 'function') {
          setError(`插件${pluginName}不包含render方法`);
          return;
        }

        // 调用插件的render函数
        await pluginInstance.render(context);
      } catch (error) {
        console.error('插件渲染失败:', error);
        setError('文件预览加载失败: ' + (error instanceof Error ? error.message : String(error)));
      } finally {
        setIsLoading(false);
      }
    };

    loadPlugin();
  }, [fileContent, fileType, fileName, pluginManager]);

  if (isLoading) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <LoaderIcon className="h-5 w-5 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">正在加载{fileType}文件预览...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center p-4">
        <div className="text-center text-red-500">
          <p className="font-medium">预览错误</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return <div ref={containerRef} className="plugin-container min-h-[200px]" />;
};

function createPluginAPI(container: HTMLElement): FilePreviewPluginAPI {
  return {
    getFileContent: async () => {
      // 此功能未实现，返回空字符串
      return '';
    },
    updateContent: (content: string) => {
      container.innerHTML = content;
    },
    showError: (message: string) => {
      container.innerHTML = `<div class="p-4 text-center text-red-500"><p class="font-medium">错误</p><p>${message}</p></div>`;
    },
    showLoading: () => {
      container.innerHTML = `
        <div class="flex h-full items-center justify-center p-4">
          <div class="flex flex-col items-center gap-2">
            <div class="h-5 w-5 animate-spin text-primary">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="2" x2="12" y2="6"></line>
                <line x1="12" y1="18" x2="12" y2="22"></line>
                <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                <line x1="2" y1="12" x2="6" y2="12"></line>
                <line x1="18" y1="12" x2="22" y2="12"></line>
                <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
              </svg>
            </div>
            <span class="text-sm text-muted-foreground">加载中...</span>
          </div>
        </div>
      `;
    },
    hideLoading: () => {
      const loading = container.querySelector('.loading');
      if (loading) {
        loading.remove();
      }
    },
  };
}
