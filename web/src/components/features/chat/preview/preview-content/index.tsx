import { Badge } from '@/components/ui/badge';
import { Message } from '@/lib/chat-messages/types';
import { usePreviewData } from '../store';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { githubGist } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  WrenchIcon,
  ArrowRightIcon,
  PackageIcon,
  HashIcon,
  LoaderIcon,
  FileIcon,
  FolderIcon,
  DownloadIcon,
  ChevronLeftIcon,
  HomeIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getImageUrl } from '@/lib/image';
import Image from 'next/image';
import { useAsync } from '@/hooks/use-async';
import { Button } from '@/components/ui/button';
import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { FilePreviewContainer } from '@/components/features/chat/preview/preview-content/file-preview-container';
import { FilePreviewPluginManager } from '@/components/features/chat/preview/preview-content/file-preview-plugin-manager';

const pluginManager = new FilePreviewPluginManager();

export const PreviewContent = ({ messages }: { messages: Message[] }) => {
  const { data } = usePreviewData();
  const [pluginsLoaded, setPluginsLoaded] = useState(false);

  useEffect(() => {
    // 加载插件
    const loadPlugins = async () => {
      try {
        console.log('开始加载文件预览插件...');
        const pluginPaths = ['markdown-viewer', 'csv-viewer'];
        await pluginManager.loadAllPlugins(pluginPaths);
        console.log('所有文件预览插件加载完成');
        setPluginsLoaded(true);
      } catch (error) {
        console.error('加载文件预览插件失败:', error);
        // 即使插件加载失败，我们也设置为加载完成，以便继续执行
        setPluginsLoaded(true);
      }
    };

    loadPlugins();
  }, []);

  if (data?.type === 'tool') {
    const executionStart = messages.find(m => m.type === 'agent:lifecycle:step:act:tool:execute:start' && m.content.id === data.toolId);
    const executionComplete = messages.find(m => m.type === 'agent:lifecycle:step:act:tool:execute:complete' && m.content.id === data.toolId);

    const name = executionStart?.content.name;
    const args = executionStart?.content.args;
    const result = executionComplete?.content.result;
    const toolId = data.toolId;
    const isExecuting = executionStart && !executionComplete;

    return (
      <div className="space-y-4 p-4">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <WrenchIcon className="text-primary h-5 w-5" />
                <CardTitle className="text-base">Tool Execution</CardTitle>
              </div>
              {isExecuting && (
                <div className="flex items-center gap-1 text-amber-500">
                  <LoaderIcon className="h-4 w-4 animate-spin" />
                  <span className="text-xs font-medium">Running...</span>
                </div>
              )}
            </div>
            <CardDescription className="flex items-center gap-2">
              <HashIcon className="h-3.5 w-3.5" />
              <span>ID: {toolId}</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="text-muted-foreground text-sm font-medium">Tool Name</div>
              <Badge variant="outline" className="font-mono text-sm">
                <PackageIcon className="mr-1 h-3.5 w-3.5" />
                {name}
              </Badge>
            </div>

            {args && Object.keys(args).length > 0 && (
              <div className="space-y-2">
                <div className="text-muted-foreground text-sm font-medium">Parameters</div>
                <div className="bg-muted/40 space-y-2 rounded-md border p-3">
                  {Object.entries(args).map(([key, value]) => (
                    <div key={key} className="flex flex-col gap-1">
                      <div className="text-muted-foreground text-xs font-medium">{key}</div>
                      <Badge variant="outline" className="font-mono break-all whitespace-normal">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result ? (
              <div className="space-y-2">
                <div className="text-muted-foreground flex items-center gap-2 text-sm font-medium">
                  <ArrowRightIcon className="h-3.5 w-3.5" />
                  <span>Result</span>
                </div>
                <div
                  className={cn(
                    'bg-muted/40 text-foreground overflow-hidden rounded-md border',
                    typeof result === 'string' && result.length > 1000 ? 'max-h-96' : '',
                  )}
                >
                  <SyntaxHighlighter
                    language="json"
                    showLineNumbers
                    style={githubGist}
                    customStyle={{
                      color: 'inherit',
                      backgroundColor: 'inherit',
                      fontSize: '0.875rem',
                      lineHeight: '1.5',
                      margin: 0,
                      borderRadius: 0,
                    }}
                  >
                    {result}
                  </SyntaxHighlighter>
                </div>
              </div>
            ) : (
              isExecuting && (
                <div className="space-y-2">
                  <div className="text-muted-foreground flex items-center gap-2 text-sm font-medium">
                    <ArrowRightIcon className="h-3.5 w-3.5" />
                    <span>Result</span>
                  </div>
                  <div className="bg-muted/20 flex items-center justify-center rounded-md border p-6">
                    <div className="text-muted-foreground flex flex-col items-center gap-2">
                      <LoaderIcon className="h-5 w-5 animate-spin" />
                      <span className="text-sm">Processing...</span>
                    </div>
                  </div>
                </div>
              )
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  if (data?.type === 'browser') {
    return (
      <div className="relative w-full">
        <Image
          src={getImageUrl(data.screenshot)}
          alt="Manus's Computer Screen"
          width={1920}
          height={1080}
          className="h-auto w-full"
          sizes="(max-width: 1920px) 100vw, 1920px"
          priority
        />
      </div>
    );
  }

  if (data?.type === 'workspace') {
    return <WorkspacePreview />;
  }

  return <NotPreview />;
};

const isHtmlFile = (fileName: string): boolean => {
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  return ext === 'html' || ext === 'htm';
};

const WorkspacePreview = () => {
  const pathname = usePathname();
  const { data, setData } = usePreviewData();
  const [isDownloading, setIsDownloading] = useState(false);

  const workspacePath = data?.type === 'workspace' ? data.path || '' : '';

  const isShare = pathname.startsWith('/share');

  // Helper to check if we're in root directory
  const isRootDirectory = !workspacePath || workspacePath.split('/').length <= 1;

  // Handle back button click - navigate to parent directory
  const handleBackClick = () => {
    if (isRootDirectory) return;

    const pathParts = workspacePath.split('/');
    pathParts.pop(); // Remove the last path segment
    const parentPath = pathParts.join('/');

    setData({
      type: 'workspace',
      path: parentPath,
    });
  };

  const handleItemClick = (item: { name: string; type: 'file' | 'directory' }) => {
    setData({
      type: 'workspace',
      path: `${workspacePath}/${item.name}`,
    });
  };

  const handleDownload = async () => {
    if (data?.type !== 'workspace') return;
    setIsDownloading(true);
    try {
      const downloadUrl = isShare ? `/api/share/download/${workspacePath}` : `/api/workspace/download/${workspacePath}`;
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = workspacePath.split('/').pop() || 'workspace';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
    } finally {
      // Add a small delay to show loading state
      setTimeout(() => {
        setIsDownloading(false);
      }, 1000);
    }
  };

  const { data: workspace, isLoading } = useAsync(
    async () => {
      if (data?.type !== 'workspace') return;
      const workspaceRes = await fetch(isShare ? `/api/share/workspace/${workspacePath}` : `/api/workspace/${workspacePath}`);
      if (!workspaceRes.ok) return;
      if (workspaceRes.headers.get('content-type')?.includes('application/json')) {
        return (await workspaceRes.json()) as {
          name: string;
          type: 'file' | 'directory';
          size: number;
          modifiedTime: string;
        }[];
      }
      return workspaceRes.blob();
    },
    [],
    {
      deps: [workspacePath, data?.type],
    },
  );

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="flex flex-col items-center gap-2">
          <LoaderIcon className="text-primary h-5 w-5 animate-spin" />
          <span className="text-muted-foreground text-sm">Loading workspace...</span>
        </div>
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-muted-foreground">Could not load workspace content</div>
      </div>
    );
  }

  if (Array.isArray(workspace)) {
    return (
      <div className="p-4">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isRootDirectory ? (
                  <HomeIcon className="text-muted-foreground h-4 w-4" />
                ) : (
                  <Button variant="ghost" size="icon" onClick={handleBackClick} className="h-6 w-6" title="Return to parent directory">
                    <ChevronLeftIcon className="h-4 w-4" />
                  </Button>
                )}
                <CardTitle className="text-base">Workspace: {data?.type === 'workspace' && data.path ? data.path : 'Root Directory'}</CardTitle>
              </div>
              <Button onClick={handleDownload} variant="outline" size="sm" disabled={isDownloading} title="Download current directory">
                {isDownloading ? (
                  <>
                    <LoaderIcon className="mr-2 h-4 w-4 animate-spin" />
                    Downloading...
                  </>
                ) : (
                  <>
                    <DownloadIcon className="mr-2 h-4 w-4" />
                    Download
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {workspace.length === 0 ? (
                <div className="text-muted-foreground py-4 text-center">This directory is empty</div>
              ) : (
                workspace.map(item => (
                  <div
                    key={item.name}
                    className="hover:bg-muted/40 flex cursor-pointer items-center justify-between rounded-md border p-2"
                    onClick={() => handleItemClick(item)}
                  >
                    <div className="flex items-center gap-2">
                      {item.type === 'directory' ? <FolderIcon className="h-4 w-4 text-blue-500" /> : <FileIcon className="h-4 w-4 text-gray-500" />}
                      <span className="text-sm font-medium">{item.name}</span>
                      {item.type === 'file' && item.name.toLowerCase().endsWith('.html') && (
                        <Badge className="ml-1 px-1.5 py-0 text-xs" variant="outline">
                          可预览
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-muted-foreground text-xs">{formatFileSize(item.size)}</span>
                      <span className="text-muted-foreground text-xs">{new Date(item.modifiedTime).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isRootDirectory ? (
                <HomeIcon className="text-muted-foreground h-5 w-5" />
              ) : (
                <Button variant="ghost" size="icon" onClick={handleBackClick} className="h-6 w-6" title="Return to parent directory">
                  <ChevronLeftIcon className="h-4 w-4" />
                </Button>
              )}
              <CardTitle className="text-base">
                File: {data?.type === 'workspace' ? (
                  <>
                    {data.path}
                    {data.path?.toLowerCase().endsWith('.html') && (
                      <Badge className="ml-2 px-1.5 py-0 text-xs" variant="outline">
                        HTML预览
                      </Badge>
                    )}
                  </>
                ) : ''}
              </CardTitle>
            </div>
            <Button onClick={handleDownload} variant="outline" size="sm" disabled={isDownloading} title="Download file">
              {isDownloading ? (
                <>
                  <LoaderIcon className="mr-2 h-4 w-4 animate-spin" />
                  Downloading...
                </>
              ) : (
                <>
                  <DownloadIcon className="mr-2 h-4 w-4" />
                  Download
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-md border">
            {workspace instanceof Blob &&
              (workspace.type.includes('image') || (data?.type === 'workspace' && data.path?.match(/\.(jpg|jpeg|png|gif|bmp|svg|webp)$/i))) ? (
              <Image
                src={URL.createObjectURL(workspace)}
                alt={data?.type === 'workspace' ? data.path || 'File preview' : 'File preview'}
                width={800}
                height={600}
                className="h-auto w-full object-contain"
              />
            ) : workspace instanceof Blob ? (
              <FileContent blob={workspace} path={data?.type === 'workspace' ? data.path : ''} />
            ) : (
              <div className="text-muted-foreground p-4 text-center">This file type cannot be previewed</div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const FileContent = ({ blob, path }: { blob: Blob; path: string }) => {
  console.log('FileContent 组件加载', { path, blobType: blob.type });
  const [isDownloading, setIsDownloading] = useState(false);
  const [viewMode, setViewMode] = useState<'preview' | 'source'>('preview');
  const [blobUrl, setBlobUrl] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      // 创建Blob URL用于预览
      console.log('创建Blob URL用于预览', { blob });
      const url = URL.createObjectURL(blob);
      console.log('Blob URL创建成功', { url });
      setBlobUrl(url);

      // 组件卸载时清理
      return () => {
        console.log('清理Blob URL', { url });
        if (url) URL.revokeObjectURL(url);
      };
    } catch (err) {
      console.error('创建Blob URL失败', err);
      setError('创建预览链接失败');
    }
  }, [blob]);

  const { data: content, isLoading } = useAsync(
    async () => {
      return await blob.text();
    },
    [],
    { deps: [blob] },
  );

  // File download function
  const handleDownload = () => {
    setIsDownloading(true);
    try {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = path.split('/').pop() || 'download';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
    } finally {
      // Add a small delay to show loading state
      setTimeout(() => {
        setIsDownloading(false);
      }, 1000);
    }
  };

  // 在新窗口中打开HTML
  const openInNewWindow = () => {
    if (!content) return;

    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>${path.split('/').pop() || 'HTML预览'}</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }
          </style>
        </head>
        <body>
          ${content}
        </body>
      </html>
    `;

    const newWindow = window.open('', '_blank');
    if (newWindow) {
      newWindow.document.write(htmlContent);
      newWindow.document.close();
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <LoaderIcon className="text-primary h-5 w-5 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-red-500">
        <p className="font-medium">预览错误</p>
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  if (!content) {
    return <div className="text-muted-foreground p-4 text-center">Could not load file content</div>;
  }

  const fileType = path.split('.').pop()?.toLowerCase() || '';
  console.log('文件类型检测', { fileType, path });

  // 显式设置blob类型为HTML，确保iframe能正确渲染
  if (fileType === 'html' || fileType === 'htm') {
    console.log('处理HTML文件', { contentLength: content.length });

    // 创建包装好的HTML内容，确保正确的编码和样式
    const htmlContent = `
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${path.split('/').pop() || 'HTML预览'}</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        padding: 10px;
        margin: 0;
      }
    </style>
  </head>
  <body>
    ${content}
  </body>
</html>`;

    // 使用UTF-8编码创建Blob
    const htmlBlob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
    const htmlUrl = URL.createObjectURL(htmlBlob);

    // 记录创建的URL，但使用新创建的URL而不使用组件状态中的blobUrl
    console.log('创建HTML专用Blob URL', { htmlUrl });

    return (
      <div className="flex flex-col h-full">
        <div className="flex justify-between items-center p-2 bg-muted/40 border-b">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant={viewMode === 'preview' ? 'default' : 'outline'}
              onClick={() => setViewMode('preview')}
            >
              预览模式
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'source' ? 'default' : 'outline'}
              onClick={() => setViewMode('source')}
            >
              源代码模式
            </Button>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={openInNewWindow}
          >
            在新窗口打开
          </Button>
        </div>

        {viewMode === 'preview' ? (
          <div className="flex-1 min-h-[400px] w-full">
            <iframe
              src={htmlUrl}
              className="w-full h-full border-0"
              sandbox="allow-scripts"
              title={`HTML预览: ${path}`}
              style={{ minHeight: '400px', width: '100%' }}
            />
          </div>
        ) : (
          <SyntaxHighlighter
            language="html"
            showLineNumbers
            style={githubGist}
            customStyle={{
              fontSize: '0.875rem',
              lineHeight: '1.5',
              margin: 0,
              borderRadius: 0,
              maxHeight: '500px',
              minHeight: '400px',
            }}
          >
            {content}
          </SyntaxHighlighter>
        )}
      </div>
    );
  }

  // 尝试使用插件系统
  const plugin = pluginManager.getPluginForFileType(fileType);
  if (plugin) {
    return <FilePreviewContainer fileContent={content} fileType={fileType} fileName={path} pluginManager={pluginManager} />;
  }

  // For binary files or very large files, show a simplified view
  if (content.length > 100000 || /[\x00-\x08\x0E-\x1F]/.test(content.substring(0, 1000))) {
    return (
      <div className="p-4 text-center">
        <p className="text-muted-foreground mb-2">File is too large or contains binary content</p>
        <Button onClick={handleDownload} disabled={isDownloading}>
          {isDownloading ? (
            <>
              <LoaderIcon className="mr-2 h-4 w-4 animate-spin" />
              Downloading...
            </>
          ) : (
            'Download'
          )}
        </Button>
      </div>
    );
  }

  const language = getFileLanguage(path);
  return (
    <SyntaxHighlighter
      language={language}
      showLineNumbers
      style={githubGist}
      customStyle={{
        fontSize: '0.875rem',
        lineHeight: '1.5',
        margin: 0,
        borderRadius: 0,
        maxHeight: '500px',
      }}
    >
      {content}
    </SyntaxHighlighter>
  );
};

// Format file size helper function
const formatFileSize = (size: number): string => {
  if (size < 1024) return `${size} B`;
  const kbSize = size / 1024;
  if (kbSize < 1024) return `${Math.round(kbSize)} KB`;
  const mbSize = kbSize / 1024;
  return `${mbSize.toFixed(1)} MB`;
};

const NotPreview = () => {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="animate-pulse text-gray-500">Manus is not using the computer right now...</div>
    </div>
  );
};

const getFileLanguage = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase();
  const languageMap: Record<string, string> = {
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    py: 'python',
    java: 'java',
    c: 'c',
    cpp: 'cpp',
    cs: 'csharp',
    go: 'go',
    rb: 'ruby',
    php: 'php',
    swift: 'swift',
    kt: 'kotlin',
    rs: 'rust',
    sh: 'bash',
    bash: 'bash',
    zsh: 'bash',
    html: 'html',
    htm: 'html',
    css: 'css',
    scss: 'scss',
    less: 'less',
    json: 'json',
    yaml: 'yaml',
    yml: 'yaml',
    xml: 'xml',
    sql: 'sql',
    md: 'markdown',
    txt: 'text',
    log: 'text',
    ini: 'ini',
    toml: 'toml',
    conf: 'conf',
    env: 'env',
    dockerfile: 'dockerfile',
    'docker-compose': 'yaml',
    csv: 'csv',
  };
  return languageMap[ext || ''] || 'text';
};
