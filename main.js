const { app, BrowserWindow, Menu, dialog } = require('electron/main')
const path = require('path')
const fs = require('fs')
const { spawn } = require('child_process')


let backendProcess = null

const getBackendPaths = () => {
  const isDev = !app.isPackaged
  const resourcesRoot = isDev ? __dirname : path.join(process.resourcesPath, 'app.asar.unpacked')
  const backendRoot = path.join(resourcesRoot, 'backend')
  const pythonRoot = isDev ? path.join(__dirname, 'python') : path.join(process.resourcesPath, 'python')
  const pyDepsRoot = path.join(backendRoot, '.pydeps')
  return { isDev, resourcesRoot, backendRoot, pythonRoot, pyDepsRoot }
}

const resolvePythonCmd = (pythonRoot, isPackaged) => {
  const embeddedPython = path.join(pythonRoot, 'python.exe')
  if (fs.existsSync(embeddedPython)) {
    return embeddedPython
  }
  if (isPackaged) {
    return null
  }
  return process.env.PYTHON_PATH || 'python'
}


const ensurePythonPathConfig = (pythonRoot, backendRoot, pyDepsRoot) => {
  if (!fs.existsSync(pythonRoot)) return

  const pthFile = fs.readdirSync(pythonRoot).find(name => name.endsWith('._pth'))
  if (!pthFile) return

  const pthPath = path.join(pythonRoot, pthFile)
  try {
    const raw = fs.readFileSync(pthPath, 'utf-8')
    const lines = raw.split(/\r?\n/)
    const normalized = new Set(
      lines
        .map(line => line.trim())
        .filter(line => line && !line.startsWith('#'))
    )
    const desired = [backendRoot, pyDepsRoot].filter(p => p && fs.existsSync(p))
    let changed = false

    for (const entry of desired) {
      if (!normalized.has(entry)) {
        lines.push(entry)
        normalized.add(entry)
        changed = true
      }
    }

    if (!lines.some(line => line.trim() === 'import site')) {
      lines.push('import site')
      changed = true
    }

    if (changed) {
      fs.writeFileSync(pthPath, lines.join('\n'), 'utf-8')
    }
  } catch (error) {
    console.error('更新 Python ._pth 失败:', error)
  }
}

const startBackend = () => {


  if (backendProcess) return

  const { resourcesRoot, backendRoot, pythonRoot, pyDepsRoot } = getBackendPaths()
  if (!fs.existsSync(backendRoot)) {
    console.error('未找到后端目录:', backendRoot)
    return
  }

  const pythonCmd = resolvePythonCmd(pythonRoot, app.isPackaged)
  if (!pythonCmd) {
    dialog.showErrorBox('后端启动失败', '未找到内置 Python 运行时，请重新安装完整包。')
    return
  }

  if (app.isPackaged && !fs.existsSync(pyDepsRoot)) {
    dialog.showErrorBox('后端启动失败', '未找到后端依赖目录，请重新安装完整包。')
    return
  }

  ensurePythonPathConfig(pythonRoot, backendRoot, pyDepsRoot)
  const port = process.env.BACKEND_PORT || '8000'


  const pythonPathEntries = [pyDepsRoot, backendRoot].filter(p => p && fs.existsSync(p))
  const pythonPath = [...pythonPathEntries, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter)
  const env = {
    ...process.env,
    BACKEND_PORT: port
  }

  if (pythonPath) {
    env.PYTHONPATH = pythonPath
  }

  if (fs.existsSync(pythonRoot)) {
    env.PYTHONHOME = pythonRoot
  }

  console.log(`使用 Python: ${pythonCmd}`)


  backendProcess = spawn(
    pythonCmd,
    ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', port],
    {
      cwd: resourcesRoot,
      env,
      stdio: 'pipe',
      windowsHide: true
    }
  )

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data.toString().trim()}`)
  })

  backendProcess.stderr.on('data', (data) => {
    console.error(`[backend] ${data.toString().trim()}`)
  })

  backendProcess.on('exit', (code) => {
    console.log(`backend exited with code ${code}`)
    backendProcess = null
  })

  backendProcess.on('error', (error) => {
    console.error('backend start failed:', error)
  })
}

const createWindow = () => {

  const win = new BrowserWindow({
    width: 900,
    height: 700,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false
    }
  })

  win.setMenuBarVisibility(false)


  // 开发环境加载 Vite 开发服务器，生产环境加载构建后的文件
  const devServerUrl = process.env.VITE_DEV_SERVER_URL || 'http://localhost:5173'

  if (app.isPackaged) {
    win.loadFile(path.join(__dirname, 'frontend', 'dist', 'index.html'))
  } else {
    win.loadURL(devServerUrl)
  }


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
  Menu.setApplicationMenu(null)
  startBackend()
  createWindow()


  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
