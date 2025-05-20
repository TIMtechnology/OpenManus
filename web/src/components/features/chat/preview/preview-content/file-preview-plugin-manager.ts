export interface FilePreviewPluginManifest {
  name: string;
  version: string;
  description: string;
  author: string;
  fileTypes: string[]; // supported file types
  entryPoint: string; // entry point
  styles?: string[]; // styles
  permissions?: string[]; // permissions
}

export interface FilePreviewPluginContext {
  fileContent: string;
  fileType: string;
  fileName: string;
  container: HTMLElement;
  api: FilePreviewPluginAPI;
}

export interface FilePreviewPluginAPI {
  // API for plugins
  getFileContent(): Promise<string>;
  updateContent(content: string): void;
  showError(message: string): void;
  showLoading(): void;
  hideLoading(): void;
}

export const PLUGIN_PATH = '/file-preview-plugins';

export class FilePreviewPluginManager {
  private plugins: Map<string, FilePreviewPluginManifest> = new Map();

  async loadPlugin(pluginPath: string): Promise<void> {
    try {
      console.log(`正在加载插件: ${pluginPath}`);
      const manifest = await this.loadManifest(pluginPath);
      this.plugins.set(manifest.name, manifest);
      console.log(`插件信息加载成功: ${manifest.name}, 支持的文件类型: ${manifest.fileTypes.join(', ')}`);

      // load plugin resources
      await this.loadPluginResources(manifest);
      console.log(`插件资源加载完成: ${manifest.name}`);
    } catch (error) {
      console.error(`插件加载失败: ${pluginPath}`, error);
      throw error;
    }
  }

  async loadAllPlugins(pluginPaths: string[]): Promise<void> {
    for (const pluginPath of pluginPaths) {
      await this.loadPlugin(pluginPath);
    }
  }

  private async loadManifest(pluginPath: string): Promise<FilePreviewPluginManifest> {
    const response = await fetch(`${PLUGIN_PATH}/${pluginPath}/manifest.json`);
    if (!response.ok) {
      throw new Error('Failed to load plugin manifest');
    }
    return response.json();
  }

  private async loadPluginResources(manifest: FilePreviewPluginManifest): Promise<void> {
    // load styles
    if (manifest.styles) {
      for (const style of manifest.styles) {
        await this.loadStyle(`${PLUGIN_PATH}/${manifest.name}/${style}`);
      }
    }

    // load script
    await this.loadScript(`${PLUGIN_PATH}/${manifest.name}/${manifest.entryPoint}`);
  }

  private loadStyle(href: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      link.onload = () => resolve();
      link.onerror = reject;
      document.head.appendChild(link);
    });
  }

  private loadScript(src: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.onload = () => resolve();
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  getPluginForFileType(fileType: string): FilePreviewPluginManifest | undefined {
    // 规范化文件类型
    const normalizedType = fileType.toLowerCase();

    // 特别处理HTML文件类型
    if (normalizedType === 'html' || normalizedType === 'htm') {
      const htmlPlugin = Array.from(this.plugins.values()).find(
        plugin => plugin.fileTypes.includes('html') || plugin.fileTypes.includes('htm')
      );
      if (htmlPlugin) return htmlPlugin;
    }

    // 常规查找
    return Array.from(this.plugins.values()).find(plugin => plugin.fileTypes.includes(normalizedType));
  }
}
