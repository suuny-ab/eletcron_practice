const { app, BrowserWindow } = require('electron/main')
const path = require('path')

const createWindow = () => {
  const win = new BrowserWindow({
    width: 900,
    height: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false
    }
  })

  // 开发环境加载 Vite 开发服务器，生产环境加载构建后的文件
  // 直接加载 Vite 开发服务器，不依赖 NODE_ENV
  win.loadURL('http://localhost:5173')

  // 监听加载完成事件
  win.webContents.on('did-finish-load', () => {
    console.log('页面加载完成')
  })

  // 监听加载失败事件
  win.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('页面加载失败:', errorCode, errorDescription)
  })

  // 监听渲染进程中的错误
  win.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[渲染进程] ${message}`)
  })
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})