(() => {
  // HTML预览器插件
  class HTMLViewer {
    constructor() {
      this.name = 'html-viewer';
    }

    /**
     * 渲染HTML内容
     * @param {FilePreviewPluginContext} context 插件上下文
     */
    async render(context) {
      const { fileContent, fileName, container, api } = context;

      // 显示加载状态
      api.showLoading();

      try {
        // 创建预览控制区
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'html-viewer-controls';

        // 创建预览按钮
        const previewBtn = document.createElement('button');
        previewBtn.className = 'html-viewer-button preview-button';
        previewBtn.innerText = '预览模式';
        previewBtn.title = '在内置框架中预览HTML';

        // 创建源码按钮
        const sourceBtn = document.createElement('button');
        sourceBtn.className = 'html-viewer-button source-button';
        sourceBtn.innerText = '源代码模式';
        sourceBtn.title = '查看HTML源代码';

        // 创建在新窗口打开按钮
        const newWindowBtn = document.createElement('button');
        newWindowBtn.className = 'html-viewer-button new-window-button';
        newWindowBtn.innerText = '在新窗口打开';
        newWindowBtn.title = '在新窗口中打开HTML文件';

        // 将按钮添加到控制区
        controlsDiv.appendChild(previewBtn);
        controlsDiv.appendChild(sourceBtn);
        controlsDiv.appendChild(newWindowBtn);

        // 创建内容区域
        const contentDiv = document.createElement('div');
        contentDiv.className = 'html-viewer-content';

        // 创建预览iframe
        const previewFrame = document.createElement('iframe');
        previewFrame.className = 'html-viewer-iframe';
        previewFrame.sandbox = 'allow-same-origin allow-scripts';
        previewFrame.title = `HTML预览: ${fileName}`;

        // 创建源码区域
        const sourceDiv = document.createElement('pre');
        sourceDiv.className = 'html-viewer-source';
        sourceDiv.textContent = fileContent;

        // 添加到内容区域
        contentDiv.appendChild(previewFrame);
        contentDiv.appendChild(sourceDiv);

        // 先清空容器，然后添加控制区和内容区
        container.innerHTML = '';
        container.appendChild(controlsDiv);
        container.appendChild(contentDiv);

        // 将HTML内容加载到iframe
        const blob = new Blob([fileContent], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        previewFrame.src = url;

        // 默认显示预览模式
        this.showPreviewMode(container);

        // 添加事件监听
        previewBtn.addEventListener('click', () => this.showPreviewMode(container));
        sourceBtn.addEventListener('click', () => this.showSourceMode(container));
        newWindowBtn.addEventListener('click', () => {
          // 在新窗口打开HTML
          const newWindow = window.open('', '_blank');
          if (newWindow) {
            newWindow.document.write(fileContent);
            newWindow.document.close();
          }
        });

        // 释放加载状态
        api.hideLoading();
      } catch (error) {
        console.error('HTML预览失败:', error);
        api.showError(`无法预览HTML文件: ${error.message}`);
      }
    }

    /**
     * 显示预览模式
     */
    showPreviewMode(container) {
      const sourceEl = container.querySelector('.html-viewer-source');
      const previewEl = container.querySelector('.html-viewer-iframe');
      const previewBtn = container.querySelector('.preview-button');
      const sourceBtn = container.querySelector('.source-button');

      if (sourceEl && previewEl && previewBtn && sourceBtn) {
        sourceEl.style.display = 'none';
        previewEl.style.display = 'block';
        previewBtn.classList.add('active');
        sourceBtn.classList.remove('active');
      }
    }

    /**
     * 显示源码模式
     */
    showSourceMode(container) {
      const sourceEl = container.querySelector('.html-viewer-source');
      const previewEl = container.querySelector('.html-viewer-iframe');
      const previewBtn = container.querySelector('.preview-button');
      const sourceBtn = container.querySelector('.source-button');

      if (sourceEl && previewEl && previewBtn && sourceBtn) {
        sourceEl.style.display = 'block';
        previewEl.style.display = 'none';
        previewBtn.classList.remove('active');
        sourceBtn.classList.add('active');
      }
    }
  }

  // 注册插件到全局
  window.HTMLViewer = new HTMLViewer();
})();
